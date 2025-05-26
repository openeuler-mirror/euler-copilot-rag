# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from typing import Any
import uuid
import os
import shutil
import yaml
import random
import io
import numpy as np
from PIL import Image
from data_chain.parser.tools.ocr_tool import OcrTool
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.parser.tools.image_tool import ImageTool
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.llm.llm import LLM
from data_chain.embedding.embedding import Embedding
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.entities.enum import TaskType, TaskStatus, KnowledgeBaseStatus, ParseMethod, DocumentStatus, ChunkStatus, ImageStatus, DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.entities.common import DEFAULt_DOC_TYPE_ID, REPORT_PATH_IN_MINIO, DOC_PATH_IN_MINIO, DOC_PATH_IN_OS, IMAGE_PATH_IN_MINIO
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.manager.image_manager import ImageManager
from data_chain.manager.task_report_manager import TaskReportManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.stores.database.database import TaskEntity, DocumentEntity, DocumentTypeEntity, ChunkEntity, ImageEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.mongodb.mongodb import Task


class ParseDocumentWorker(BaseWorker):
    name = TaskType.DOC_PARSE.value

    @staticmethod
    async def init(doc_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        doc_entity = await DocumentManager.get_document_by_doc_id(doc_id)
        if doc_entity is None:
            err = f"[ParseDocumentWorker] 文档不存在，doc_id: {doc_id}"
            logging.exception(err)
            raise None
        await DocumentManager.update_document_by_doc_id(doc_id, {"status": DocumentStatus.PENDING.value, "abstract": "", "abstract_vector": None})
        await ImageManager.update_images_by_doc_id(doc_id, {"status": ImageStatus.DELETED.value})
        await ChunkManager.update_chunk_by_doc_id(doc_id, {"status": ChunkStatus.DELETED.value})
        task_entity = TaskEntity(
            team_id=doc_entity.team_id,
            user_id=doc_entity.author_id,
            op_id=doc_entity.id,
            op_name=doc_entity.name,
            type=TaskType.DOC_PARSE.value,
            retry=0,
            status=TaskStatus.PENDING.value)
        task_entity = await TaskManager.add_task(task_entity)
        return task_entity.id

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return False
        doc_id = task_entity.op_id
        await DocumentManager.update_document_by_doc_id(doc_id, {"abstract": "", "abstract_vector": None})
        await ImageManager.update_images_by_doc_id(doc_id, {"status": ImageStatus.DELETED.value})
        await ChunkManager.update_chunk_by_doc_id(doc_id, {"status": ChunkStatus.DELETED.value})
        tmp_path = os.path.join(DOC_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        if task_entity.retry < config['TASK_RETRY_TIME_LIMIT']:
            await DocumentManager.update_document_by_doc_id(task_entity.op_id, {"status": DocumentStatus.PENDING.value})
            return True
        else:
            await DocumentManager.update_document_by_doc_id(task_entity.op_id, {"status": DocumentStatus.IDLE.value})
            return False

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ParseDocumentWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await DocumentManager.update_document_by_doc_id(task_entity.op_id, {"status": DocumentStatus.IDLE.value})
        tmp_path = os.path.join(DOC_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        return task_id

    @staticmethod
    async def init_path(task_id: uuid.UUID) -> tuple:
        '''初始化存放配置文件和文档的路径'''
        tmp_path = os.path.join(DOC_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.makedirs(tmp_path)
        image_path = os.path.join(tmp_path, "images")
        os.makedirs(image_path)
        return tmp_path, image_path

    @staticmethod
    async def download_doc_from_minio(doc_id: uuid.UUID, tmp_path: str) -> str:
        '''下载文档'''
        doc_entity = await DocumentManager.get_document_by_doc_id(doc_id)
        if doc_entity is None:
            err = f"[ParseDocumentWorker] 文档不存在，doc_id: {doc_id}"
            logging.exception(err)
            raise Exception(err)
        file_path = os.path.join(tmp_path, str(doc_id)+'.'+doc_entity.extension)
        await MinIO.download_object(
            DOC_PATH_IN_MINIO,
            str(doc_entity.id),
            file_path,
        )
        return file_path

    @staticmethod
    async def parse_doc(doc_entity: DocumentEntity, file_path: str) -> ParseResult:
        '''解析文档'''
        parse_result = await BaseParser.parser(doc_entity.extension, file_path)
        return parse_result

    @staticmethod
    async def get_content_from_json(js: Any) -> str:
        '''获取json内容'''
        if isinstance(js, dict):
            content = ''
            for key, value in js.items():
                content += str(key) + ': '
                if isinstance(value, (dict, list)):
                    content += await ParseDocumentWorker.get_content_from_json(value)
                else:
                    content += str(value) + '\n'
            return content
        elif isinstance(js, list):
            for item in js:
                content += await ParseDocumentWorker.get_content_from_json(item)
                content += ' '
            content += '\n'
            return content
        else:
            return str(js)

    @staticmethod
    async def handle_parse_result(parse_result: ParseResult, doc_entity: DocumentEntity, llm: LLM = None) -> None:
        '''处理解析结果'''
        if doc_entity.parse_method != ParseMethod.OCR.value and doc_entity.parse_method != ParseMethod.EHANCED:
            nodes = []
            for node in parse_result.nodes:
                if node.type != ChunkType.IMAGE:
                    nodes.append(node)
            parse_result.nodes = nodes
        if doc_entity.parse_method == ParseMethod.QA:
            if doc_entity.extension == 'xlsx' or doc_entity.extension == 'csv':
                for node in parse_result.nodes:
                    node.type = ChunkType.QA
                    try:
                        question = ''
                        if len(node.content) > 0:
                            question = str(node.content[0])
                        answer = ''
                        if len(node.content) > 1:
                            answer = str(node.content[1])
                    except Exception as e:
                        question = ''
                        answer = ''
                        warning = f"[ParseDocumentWorker] 解析问题和答案失败，doc_id: {doc_entity.id}, error: {e}"
                        logging.warning(warning)
                    node.text_feature = question
                    node.content = 'question: ' + question + '\n' + 'answer: ' + answer
            elif doc_entity.extension == 'json' or doc_entity.extension == 'yaml':
                qa_list = parse_result.nodes[0].content
                parse_result.nodes = []
                for qa in qa_list:
                    question = qa.get('question')
                    answer = qa.get('answer')
                    if question is None or answer is None:
                        warning = f"[ParseDocumentWorker] 解析问题和答案失败，doc_id: {doc_entity.id}, error: {e}"
                        logging.warning(warning)
                        continue
                    node = ParseNode(
                        id=uuid.uuid4(),
                        lv=0,
                        parse_topology_type=ChunkParseTopology.GERNERAL,
                        text_feature=question,
                        content='question: ' + question + '\n' + 'answer: ' + answer,
                        type=ChunkType.QA,
                        link_nodes=[]
                    )
                    parse_result.nodes.append(node)
        else:
            if doc_entity.extension == 'xlsx' or doc_entity.extension == 'xls' or doc_entity.extension == 'csv':
                for node in parse_result.nodes:
                    node.content = '|'.join(node.content)
                    node.text_feature = node.content
            elif doc_entity.extension == 'json' or doc_entity.extension == 'yaml':
                parse_result.nodes[0].content = await ParseDocumentWorker.get_content_from_json(parse_result.nodes[0].content)
                parse_result.nodes[0].text_feature = parse_result.nodes[0].content
            else:
                for node in parse_result.nodes:
                    if node.type == ChunkType.TEXT or node.type == ChunkType.LINK:
                        node.text_feature = node.content
                    elif node.type == ChunkType.CODE:
                        if llm is not None:
                            node.text_feature = await TokenTool.get_abstract_by_llm(node.content, llm)
                        if node.text_feature is None:
                            node.text_feature = TokenTool.get_top_k_keywords(node.content)
                    elif node.type == ChunkType.TABLE:
                        node.content = '|'.join(node.content)
                        node.text_feature = node.content

    @staticmethod
    async def upload_parse_image_to_minio_and_postgres(
            parse_result: ParseResult, doc_entity: DocumentEntity, image_path: str) -> None:
        '''上传解析图片到minio'''
        image_entities = []
        for node in parse_result.nodes:
            if node.type == ChunkType.IMAGE:
                try:
                    extension = ImageTool.get_image_type(node.content)
                    image_entity = ImageEntity(
                        id=uuid.uuid4(),
                        team_id=doc_entity.team_id,
                        doc_id=doc_entity.id,
                        chunk_id=node.id,
                        extension=extension,
                    )
                    image_entities.append(image_entity)
                    image_blob = node.content
                    image_file_path = os.path.join(image_path, str(node.id) + '.' + extension)
                    with open(image_file_path, 'wb') as f:
                        f.write(image_blob)
                    await MinIO.put_object(
                        IMAGE_PATH_IN_MINIO,
                        str(node.id),
                        image_file_path
                    )
                except Exception as e:
                    err = f"[ParseDocumentWorker] 上传解析图片到minio失败，doc_id: {doc_entity.id}, image_path: {image_path}, error: {e}"
                    logging.exception(err)
                    continue
                image_entities.append(image_entity)
        index = 0
        while index < len(image_entities):
            try:
                await ImageManager.add_images(image_entities[index:index+1024])
            except Exception as e:
                err = f"[ParseDocumentWorker] 上传解析图片到postgres失败，doc_id: {doc_entity.id}, image_path: {image_path}, error: {e}"
                logging.exception(err)
            index += 1024

    @staticmethod
    async def ocr_from_parse_image(parse_result: ParseResult, llm: LLM = None) -> list:
        '''从解析图片中获取ocr'''
        for node in parse_result.nodes:
            if node.type == ChunkType.IMAGE:
                try:
                    image_blob = node.content
                    image = Image.open(io.BytesIO(image_blob))
                    img_np = np.array(image)
                    image_related_text = ''
                    for related_node in node.link_nodes:
                        if related_node.type != ChunkType.IMAGE:
                            image_related_text += related_node.content
                    node.content = await OcrTool.image_to_text(img_np, image_related_text, llm)
                    node.text_feature = node.content
                except Exception as e:
                    err = f"[ParseDocumentWorker] OCR失败，doc_id: {node.doc_id}, error: {e}"
                    logging.exception(err)
                    continue

    @staticmethod
    async def merge_and_split_text(parse_result: ParseResult, doc_entity: DocumentEntity) -> None:
        '''合并和拆分内容'''
        if doc_entity.parse_method == ParseMethod.QA or doc_entity.parse_relut_topology == DocParseRelutTopology.TREE:
            return
        nodes = []
        for node in parse_result.nodes:
            if node.type == ChunkType.TEXT:
                tokens = TokenTool.get_tokens(node.content)
                if len(nodes) == 0 or (len(nodes) and (nodes[-1].type != ChunkType.TEXT or TokenTool.get_tokens(nodes[-1].content) + tokens > doc_entity.chunk_size)):
                    nodes.append(node)
                else:
                    nodes[-1].content += node.content
            else:
                nodes.append(node)
        parse_result.nodes = nodes
        nodes = []
        tmp = ''
        for node in parse_result.nodes:
            if node.type == ChunkType.TEXT:
                sentences = TokenTool.content_to_sentences(node.content)
                new_sentences = []
                for sentence in sentences:
                    if TokenTool.get_tokens(sentence) > doc_entity.chunk_size:
                        tmp = sentence[:]
                        while len(tmp) > 0:
                            sub_sentence = TokenTool.get_k_tokens_words_from_content(tmp, doc_entity.chunk_size)
                            new_sentences.append(sub_sentence)
                            tmp = tmp[len(sub_sentence):]
                    else:
                        new_sentences.append(sentence)
                sentences = new_sentences
                for sentence in sentences:
                    if TokenTool.get_tokens(tmp) + TokenTool.get_tokens(sentence) > doc_entity.chunk_size:
                        tmp_node = ParseNode(
                            id=uuid.uuid4(),
                            lv=node.lv,
                            parse_topology_type=ChunkParseTopology.GERNERAL,
                            text_feature=tmp,
                            content=tmp,
                            type=ChunkType.TEXT,
                            link_nodes=[]
                        )
                        nodes.append(tmp_node)
                        tmp = sentence
                    else:
                        tmp += sentence
            else:
                if len(tmp) > 0:
                    tmp_node = ParseNode(
                        id=uuid.uuid4(),
                        lv=node.lv,
                        parse_topology_type=ChunkParseTopology.GERNERAL,
                        text_feature=tmp,
                        content=tmp,
                        type=ChunkType.TEXT,
                        link_nodes=[]
                    )
                    nodes.append(tmp_node)
                tmp = ''
                nodes.append(node)
        if len(tmp) > 0:
            tmp_node = ParseNode(
                id=uuid.uuid4(),
                lv=node.lv,
                parse_topology_type=ChunkParseTopology.GERNERAL,
                text_feature=tmp,
                content=tmp,
                type=ChunkType.TEXT,
                link_nodes=[]
            )
            nodes.append(tmp_node)

    @staticmethod
    async def push_up_words_feature(parse_result: ParseResult, llm: LLM = None) -> None:
        '''推送上层词特征'''
        async def dfs(node: ParseNode, parent_node: ParseNode, llm: LLM = None) -> None:
            if parent_node is not None:
                node.pre_id = parent_node.id
            for child_node in node.link_nodes:
                await dfs(child_node, node, llm)
            if node.title is not None:
                if len(node.title) == 0:
                    if llm is not None:
                        content = '父标题\n'
                        if parent_node and parent_node.title:
                            if len(parent_node.title) > 0:
                                content += parent_node.title + '\n'
                            else:
                                sentences = TokenTool.get_top_k_keysentence(parent_node.content, 1)
                                if sentences:
                                    content += sentences[0] + '\n'
                        index = 0
                        for node in node.link_nodes:
                            content += '子标题'+str(index) + '\n'
                            if node.title:
                                content += node.title + '\n'
                            else:
                                sentences = TokenTool.get_top_k_keysentence(node.content, 1)
                                if sentences:
                                    content += sentences[0] + '\n'
                            index += 1
                        title = await TokenTool.get_title_by_llm(content, llm)
                        if not title:
                            sentences = TokenTool.get_top_k_keysentence(content, 1)
                            if sentences:
                                title = sentences[0]
                        node.text_feature = title
                        node.content = node.text_feature
                    else:
                        node.text_feature = ''
                        node.content = ''
                else:
                    node.text_feature = node.title
                    node.content = node.text_feature
        if parse_result.parse_topology_type == DocParseRelutTopology.TREE:
            await dfs(parse_result.nodes[0], None, llm)

    @staticmethod
    async def update_doc_abstract(doc_id: uuid.UUID, parse_result: ParseResult, llm: LLM = None) -> str:
        '''获取文档摘要'''
        abstract = ""
        for node in parse_result.nodes:
            abstract += node.content
        if llm is not None:
            abstract = await TokenTool.get_abstract_by_llm(abstract, llm)
        else:
            sentences = TokenTool.get_top_k_keysentence(abstract, 1)
            if sentences:
                abstract = sentences[0]
            else:
                abstract = ''
        abstract_vector = await Embedding.vectorize_embedding(abstract)
        await DocumentManager.update_document_by_doc_id(
            doc_id,
            {
                "abstract": abstract,
                "abstract_vector": abstract_vector
            }
        )
        return abstract

    @staticmethod
    async def embedding_chunk(parse_result: ParseResult) -> None:
        '''嵌入chunk'''
        for node in parse_result.nodes:
            node.vector = await Embedding.vectorize_embedding(node.text_feature)

    @staticmethod
    async def add_parse_result_to_db(parse_result: ParseResult, doc_entity: DocumentEntity) -> None:
        '''添加解析结果到数据库'''
        chunk_entities = []
        global_offset = 0
        local_offset = 0
        for node in parse_result.nodes:
            if not node.content:
                continue
            chunk_entity = ChunkEntity(
                id=node.id,
                team_id=doc_entity.team_id,
                kb_id=doc_entity.kb_id,
                doc_id=doc_entity.id,
                doc_name=doc_entity.name,
                text=node.content,
                text_vector=node.vector,
                tokens=TokenTool.get_tokens(node.content),
                type=node.type,
                pre_id_in_parse_topology=node.pre_id,
                parse_topology_type=node.parse_topology_type,
                global_offset=global_offset,
                local_offset=local_offset,
                enabled=True,
                status=ChunkStatus.EXISTED.value
            )
            chunk_entities.append(chunk_entity)
            if global_offset and parse_result.nodes[global_offset].type != parse_result.nodes[global_offset-1].type:
                local_offset = 0
            local_offset += 1
            global_offset += 1
        index = 0
        while index < len(chunk_entities):
            try:
                await ChunkManager.add_chunks(chunk_entities[index:index+1024])
            except Exception as e:
                err = f"[ParseDocumentWorker] 添加解析结果到数据库失败，doc_id: {doc_entity.id}, error: {e}"
                logging.exception(err)
            index += 1024

    @staticmethod
    async def run(task_id: uuid.UUID) -> None:
        '''运行任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ParseDocumentWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            raise Exception(err)
        doc_entity = await DocumentManager.get_document_by_doc_id(task_entity.op_id)
        if doc_entity is None:
            err = f"[ParseDocumentWorker] 文档不存在，doc_id: {task_entity.op_id}"
            logging.exception(err)
            raise Exception(err)
        await DocumentManager.update_document_by_doc_id(task_entity.op_id, {"status": DocumentStatus.RUNNING.value})
        try:
            if doc_entity.parse_method == ParseMethod.EHANCED:
                llm = LLM(
                    openai_api_key=config['OPENAI_API_KEY'],
                    openai_api_base=config['OPENAI_API_BASE'],
                    model_name=config['MODEL_NAME'],
                    max_tokens=config['MAX_TOKENS'],
                )
            else:
                llm = None
            tmp_path, image_path = await ParseDocumentWorker.init_path(task_id)
            current_stage = 0
            stage_cnt = 10
            await ParseDocumentWorker.download_doc_from_minio(task_entity.op_id, tmp_path)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '下载文档', current_stage, stage_cnt)
            file_path = os.path.join(tmp_path, str(task_entity.op_id)+'.'+doc_entity.extension)
            parse_result = await ParseDocumentWorker.parse_doc(doc_entity, file_path)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '解析文档', current_stage, stage_cnt)
            await ParseDocumentWorker.handle_parse_result(parse_result, doc_entity, llm)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '处理解析结果', current_stage, stage_cnt)
            await ParseDocumentWorker.upload_parse_image_to_minio_and_postgres(parse_result, doc_entity, image_path)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '上传解析图片', current_stage, stage_cnt)
            await ParseDocumentWorker.ocr_from_parse_image(parse_result, llm)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, 'OCR图片', current_stage, stage_cnt)
            await ParseDocumentWorker.merge_and_split_text(parse_result, doc_entity)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '合并和拆分文本', current_stage, stage_cnt)
            await ParseDocumentWorker.push_up_words_feature(parse_result, llm)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '推送上层词特征', current_stage, stage_cnt)
            await ParseDocumentWorker.embedding_chunk(parse_result)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '嵌入chunk', current_stage, stage_cnt)
            await ParseDocumentWorker.update_doc_abstract(doc_entity.id, parse_result, llm)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '更新文档摘要', current_stage, stage_cnt)
            await ParseDocumentWorker.add_parse_result_to_db(parse_result, doc_entity)
            current_stage += 1
            await ParseDocumentWorker.report(task_id, '添加解析结果到数据库', current_stage, stage_cnt)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.SUCCESS.value))
            task_report = await ParseDocumentWorker.assemble_task_report(task_id)
            report_path = os.path.join(tmp_path, 'task_report.txt')
            with open(report_path, 'w') as f:
                f.write(task_report)
            await MinIO.put_object(
                REPORT_PATH_IN_MINIO,
                str(task_entity.op_id),
                report_path
            )
        except Exception as e:
            err = f"[DocParseWorker] 任务失败，task_id: {task_id}，错误信息: {e}"
            logging.exception(err)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.FAILED.value))
            await ParseDocumentWorker.report(task_id, err, 0, 1)
            task_report = await ParseDocumentWorker.assemble_task_report(task_id)
            report_path = os.path.join(tmp_path, 'task_report.txt')
            with open(report_path, 'w') as f:
                f.write(task_report)
            await MinIO.put_object(
                REPORT_PATH_IN_MINIO,
                str(task_entity.op_id),
                report_path
            )
            return None

    @staticmethod
    async def stop(task_id: uuid.UUID) -> uuid.UUID:
        '''停止任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ParseDocumentWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await DocumentManager.update_document_by_doc_id(task_entity.op_id, {"status": DocumentStatus.IDLE.value})
        if task_entity.status == TaskStatus.PENDING.value or task_entity.status == TaskStatus.RUNNING.value or task_entity.status == TaskStatus.FAILED.value:
            if task_entity.status == TaskStatus.RUNNING.value or task_entity.status == TaskStatus.FAILED.value:
                await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.CANCLED.value})
            await DocumentManager.update_document_by_doc_id(task_entity.op_id, {"abstract": "", "abstract_vector": None})
            await ImageManager.update_images_by_doc_id(task_entity.op_id, {"status": ImageStatus.DELETED.value})
            await ChunkManager.update_chunk_by_doc_id(task_entity.op_id, {"status": ChunkStatus.DELETED.value})
        tmp_path = os.path.join(DOC_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        return task_id
