# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
import os
import shutil
import yaml
import json
import random
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.llm.llm import LLM
from data_chain.entities.enum import TaskType, TaskStatus, KnowledgeBaseStatus, DocumentStatus, DataSetStatus, QAStatus, ChunkType
from data_chain.entities.common import DEFAULt_DOC_TYPE_ID, IMPORT_DATASET_PATH_IN_OS, IMPORT_DATASET_PATH_IN_MINIO
from data_chain.parser.parse_result import ParseResult, ParseNode
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.parser.handler.json_parser import JsonParser
from data_chain.parser.handler.yaml_parser import YamlParser
from data_chain.parser.handler.xlsx_parser import XlsxParser
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.manager.dataset_manager import DatasetManager
from data_chain.manager.qa_manager import QAManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.stores.database.database import TaskEntity, DocumentEntity, DocumentTypeEntity, QAEntity, DataSetEntity, DataSetDocEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.mongodb.mongodb import Task


class ImportDataSetWorker(BaseWorker):
    """
    ImportDataSetWorker
    """
    name = TaskType.DATASET_IMPORT.value

    @staticmethod
    async def init(dataset_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        dataset_entity = await DatasetManager.get_dataset_by_dataset_id(dataset_id)
        if dataset_entity is None:
            err = f"[ImportDataSetWorker] 数据集不存在，数据集ID: {dataset_id}"
            logging.exception(err)
            return None
        dataset_entity = await DatasetManager.update_dataset_by_dataset_id(dataset_id, {"status": DataSetStatus.PENDING.value})
        task_entity = TaskEntity(
            team_id=dataset_entity.team_id,
            user_id=dataset_entity.author_id,
            op_id=dataset_entity.id,
            op_name=dataset_entity.name,
            type=TaskType.DATASET_IMPORT.value,
            retry=0,
            status=TaskStatus.PENDING.value)
        task_entity = await TaskManager.add_task(task_entity)
        return task_entity.id

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return False
        await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"score": 0})
        await QAManager.update_qa_by_dataset_id(task_entity.op_id, {"status": QAStatus.DELETED.value})
        tmp_path = os.path.join(IMPORT_DATASET_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        if task_entity.retry < config['TASK_RETRY_TIME_LIMIT']:
            await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.PENDING.value})
            return True
        else:
            await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.DELETED.value})
            await MinIO.delete_object(
                IMPORT_DATASET_PATH_IN_MINIO,
                str(task_entity.op_id)
            )
            return False

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        tmp_path = os.path.join(IMPORT_DATASET_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.IDLE.value})
        return task_id

    @staticmethod
    async def init_path(task_id: uuid.UUID) -> str:
        '''初始化路径'''
        tmp_path = os.path.join(IMPORT_DATASET_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.makedirs(tmp_path)
        return tmp_path

    @staticmethod
    async def download_file_from_minio(dataset_id: uuid.UUID, tmp_path: str) -> str:
        '''从MinIO下载文件'''
        file_path = os.path.join(tmp_path, str(dataset_id))
        if not os.path.exists(file_path):
            await MinIO.download_object(
                IMPORT_DATASET_PATH_IN_MINIO,
                str(dataset_id),
                file_path
            )
        return file_path

    @staticmethod
    async def load_qa_entity_from_file(dataset_id: uuid.UUID, file_path: str) -> list[QAEntity]:
        '''从文件中加载QA实体'''
        parser_result = None
        parsers = {
            'json': JsonParser,
            'yaml': YamlParser,
            'xlsx': XlsxParser
        }
        extension = None
        for parser_name, parser in parsers.items():
            try:
                parser_result = await parser.parser(file_path)
                extension = parser_name
                break
            except Exception as e:
                err = f"[GenerateDataSetWorker] 解析文件失败，文件路径: {file_path}，错误信息: {e}"
                logging.error(err)
        if parser_result is None:
            err = f"[GenerateDataSetWorker] 解析文件失败，文件路径: {file_path}，不支持的文件格式"
            logging.exception(err)
            raise Exception(err)
        qa_entities = []
        if extension == 'xlsx':
            nodes = parser_result.nodes
            ignore = True
            for node in nodes:
                if ignore:
                    ignore = False
                    continue
                tmp_list = node.content
                if len(tmp_list) < 3:
                    err = f"[GenerateDataSetWorker] qa对提取失败，文件路径: {file_path}，qa对长度不足3"
                    logging.exception(err)
                    continue
                question = tmp_list[0]
                answer = tmp_list[1]
                chunk = tmp_list[2]
                qa_entity = QAEntity(
                    dataset_id=dataset_id,
                    doc_id=None,
                    doc_name='',
                    question=question,
                    answer=answer,
                    chunk=chunk,
                    chunk_type=ChunkType.UNKOWN.value
                )
                qa_entities.append(qa_entity)
        elif extension == 'json' or extension == 'yaml':
            for tmp_dict in parser_result.nodes[0].content:
                if 'question' not in tmp_dict or 'answer' not in tmp_dict or 'chunk' not in tmp_dict:
                    err = f"[GenerateDataSetWorker] qa对提取失败，文件路径: {file_path}，qa对格式不正确"
                    logging.exception(err)
                    continue
                question = tmp_dict['question']
                answer = tmp_dict['answer']
                chunk = tmp_dict['chunk']
                qa_entity = QAEntity(
                    dataset_id=dataset_id,
                    doc_id=None,
                    doc_name='',
                    question=question,
                    answer=answer,
                    chunk=chunk,
                    chunk_type=ChunkType.UNKOWN.value
                )
                qa_entities.append(qa_entity)
        qa_entities = qa_entities[:512]
        await QAManager.add_qas(qa_entities)
        await DatasetManager.update_dataset_by_dataset_id(dataset_id, {"data_cnt": len(qa_entities)})
        return qa_entities

    @staticmethod
    async def update_dataset_score(dataset_id: uuid.UUID, qa_entities: list[QAEntity], llm: LLM) -> None:
        '''更新数据集分数'''
        if not qa_entities:
            return
        databse_score = 0
        with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
            prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
        cal_qa_score_prompt_template = prompt_dict.get('CAL_QA_SCORE_PROMPT', '')
        for qa_entity in qa_entities:
            chunk = qa_entity.chunk
            question = qa_entity.question
            answer = qa_entity.answer
            sys_call = cal_qa_score_prompt_template.format(
                fragment=TokenTool.get_k_tokens_words_from_content(chunk, llm.max_tokens//9*4),
                question=TokenTool.get_k_tokens_words_from_content(question, llm.max_tokens//9),
                answer=TokenTool.get_k_tokens_words_from_content(answer, llm.max_tokens//9*4)
            )
            usr_call = '请输出分数'
            score = await llm.nostream([], sys_call, usr_call)
            score = eval(score)
            score = min(max(score, 0), 100)
            databse_score += score
        if len(qa_entities) > 0:
            databse_score /= len(qa_entities)
        await DatasetManager.update_dataset_by_dataset_id(dataset_id, {"score": databse_score})

    @staticmethod
    async def run(task_id: uuid.UUID) -> None:
        '''运行任务'''
        try:
            task_entity = await TaskManager.get_task_by_task_id(task_id)
            if task_entity is None:
                err = f"[ImportDataSetWorker] 任务不存在，task_id: {task_id}"
                logging.exception(err)
                raise Exception(err)
            llm = LLM(
                openai_api_key=config['OPENAI_API_KEY'],
                openai_api_base=config['OPENAI_API_BASE'],
                model_name=config['MODEL_NAME'],
                max_tokens=config['MAX_TOKENS'],
            )
            dataset_entity = await DatasetManager.get_dataset_by_dataset_id(task_entity.op_id)
            if dataset_entity is None:
                err = f"[ImportDataSetWorker] 数据集不存在，数据集ID: {task_entity.op_id}"
                logging.exception(err)
                raise Exception(err)
            await DatasetManager.update_dataset_by_dataset_id(dataset_entity.id, {"status": DataSetStatus.IMPORTING.value})
            current_stage = 0
            stage_cnt = 4
            tmp_path = await ImportDataSetWorker.init_path(task_id)
            current_stage += 1
            await ImportDataSetWorker.report(task_id, "初始化路径", current_stage, stage_cnt)
            file_path = await ImportDataSetWorker.download_file_from_minio(dataset_entity.id, tmp_path)
            current_stage += 1
            await ImportDataSetWorker.report(task_id, "下载文件", current_stage, stage_cnt)
            qa_entities = await ImportDataSetWorker.load_qa_entity_from_file(dataset_entity.id, file_path)
            current_stage += 1
            await ImportDataSetWorker.report(task_id, "加载qa实体", current_stage, stage_cnt)
            await ImportDataSetWorker.update_dataset_score(dataset_entity.id, qa_entities, llm)
            current_stage += 1
            await ImportDataSetWorker.report(task_id, "更新数据集分数", current_stage, stage_cnt)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.SUCCESS.value))
        except Exception as e:
            err = f"[ImportDataSetWorker] 任务失败，task_id: {task_id}，错误信息: {e}"
            logging.exception(err)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.FAILED.value))
            await ImportDataSetWorker.report(task_id, "任务失败", 0, 1)

    @staticmethod
    async def stop(task_id: uuid.UUID) -> uuid.UUID:
        '''停止任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.IDLE.value})
        tmp_path = os.path.join(IMPORT_DATASET_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        return task_id

    @staticmethod
    async def delete(task_id: uuid.UUID) -> uuid.UUID:
        '''删除任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        if task_entity.status == TaskStatus.CANCLED or TaskStatus.FAILED.value:
            await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.DELETED.value})
            await MinIO.delete_object(
                IMPORT_DATASET_PATH_IN_MINIO,
                str(task_entity.op_id)
            )
        return task_id
