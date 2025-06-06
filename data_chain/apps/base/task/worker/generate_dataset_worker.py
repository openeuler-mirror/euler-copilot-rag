# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
import os
import shutil
import yaml
import json
import random
from pydantic import BaseModel, Field
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.llm.llm import LLM
from data_chain.entities.enum import TaskType, TaskStatus, KnowledgeBaseStatus, DocumentStatus, DataSetStatus, QAStatus
from data_chain.entities.common import DEFAULT_DOC_TYPE_ID
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.manager.dataset_manager import DatasetManager
from data_chain.manager.qa_manager import QAManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.stores.database.database import TaskEntity, DocumentEntity, DocumentTypeEntity, QAEntity, DataSetEntity, DataSetDocEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.mongodb.mongodb import Task


class Chunk(BaseModel):
    text: str
    type: str


class DocChunk(BaseModel):
    doc_id: uuid.UUID
    doc_name: str
    chunks: list[Chunk]


class GenerateDataSetWorker(BaseWorker):
    """
    GenerateDataSetWorker
    """
    name = TaskType.DATASET_GENERATE.value

    @staticmethod
    async def init(dataset_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        dataset_entity = await DatasetManager.get_dataset_by_dataset_id(dataset_id)
        if dataset_entity is None:
            err = f"[GenerateDataSetWorker] 数据集不存在，数据集ID: {dataset_id}"
            logging.exception(err)
            return None
        await DatasetManager.update_dataset_by_dataset_id(dataset_id, {"score": -1})
        dataset_entity = await DatasetManager.update_dataset_by_dataset_id(dataset_id, {"status": DataSetStatus.PENDING.value})
        await QAManager.update_qa_by_dataset_id(dataset_id, {"status": QAStatus.DELETED.value})
        task_entity = TaskEntity(
            team_id=dataset_entity.team_id,
            user_id=dataset_entity.author_id,
            op_id=dataset_entity.id,
            op_name=dataset_entity.name,
            type=TaskType.DATASET_GENERATE.value,
            retry=0,
            status=TaskStatus.PENDING.value)
        task_entity = await TaskManager.add_task(task_entity)
        return task_entity.id

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[GenerateDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return False
        await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"score": -1})
        await QAManager.update_qa_by_dataset_id(task_entity.op_id, {"status": QAStatus.DELETED.value})
        if task_entity.retry < config['TASK_RETRY_TIME_LIMIT']:
            await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.PENDING.value})
            return True
        else:
            await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.IDLE.value})
            return False

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[GenerateDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.IDLE.value})
        return task_id

    @staticmethod
    async def get_chunks(dataset_entity: DataSetEntity) -> list[DocChunk]:
        '''获取文档的分块信息'''
        dataset_doc_entities = await DatasetManager.list_dataset_document_by_dataset_id(dataset_entity.id)
        doc_chunks = []
        for dataset_doc_entity in dataset_doc_entities:
            doc_entity = await DocumentManager.get_document_by_doc_id(dataset_doc_entity.doc_id)
            chunk_entities = await ChunkManager.list_all_chunk_by_doc_id(dataset_doc_entity.doc_id)
            chunks = []
            for chunk_entity in chunk_entities:
                chunks.append(Chunk(
                    text=chunk_entity.text,
                    type=chunk_entity.type
                ))
            doc_chunk = DocChunk(
                doc_id=doc_entity.id,
                doc_name=doc_entity.name,
                chunks=[]
            )
            doc_chunk.chunks = chunks
            doc_chunks.append(doc_chunk)
        return doc_chunks

    @staticmethod
    async def generate_qa(dataset_entity: DataSetEntity, doc_chunks: list[DocChunk], llm: LLM) -> list[QAEntity]:
        chunk_cnt = 0
        for doc_chunk in doc_chunks:
            chunk_cnt += len(doc_chunk.chunks)
        if chunk_cnt == 0:
            return []
        chunk_index_list = []
        for i in range(chunk_cnt):
            chunk_index_list.append(i)
        random.shuffle(chunk_index_list)
        qa_entities = []
        data_cnt = dataset_entity.data_cnt
        chunk_index_list = chunk_index_list[:data_cnt]
        chunk_cnt = len(chunk_index_list)
        division = data_cnt // chunk_cnt
        remainder = data_cnt % chunk_cnt
        logging.error(f"数据集总条目 {dataset_entity.data_cnt}, 分块数量: {chunk_cnt}, 每块数据量: {division}, 余数: {remainder}")
        index = 0
        d_index = 0
        random.shuffle(doc_chunks)
        with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
            prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
        q_generate_prompt_template = prompt_dict.get('GENREATE_QUESTION_FROM_CONTENT_PROMPT', '')
        answer_generate_prompt_template = prompt_dict.get('GENERATE_ANSWER_FROM_QUESTION_AND_CONTENT_PROMPT', '')
        cal_qa_score_prompt_template = prompt_dict.get('CAL_QA_SCORE_PROMPT', '')
        dataset_score = 0
        logging.error(f"{chunk_index_list}")
        for i in range(len(doc_chunks)):
            doc_chunk = doc_chunks[i]
            for j in range(len(doc_chunk.chunks)):
                if index not in chunk_index_list:
                    index += 1
                    continue
                index += 1
                d_index += 1
                chunk = doc_chunk.chunks[j].text
                if dataset_entity.is_chunk_related:
                    l = j-1
                    r = j+1
                    tokens_sub = 0
                    while TokenTool.get_tokens(chunk) < llm.max_tokens:
                        if l < 0 and r >= len(doc_chunk.chunks):
                            break
                        if tokens_sub > 0:
                            if l >= 0:
                                tokens_sub -= TokenTool.get_tokens(doc_chunk.chunks[l].text)
                                chunk = doc_chunk.chunks[l].text+chunk
                                l -= 1
                            else:
                                tokens_sub += TokenTool.get_tokens(doc_chunk.chunks[r].text)
                                chunk += doc_chunk.chunks[r].text
                                r += 1
                        else:
                            if r < len(doc_chunk.chunks):
                                tokens_sub += TokenTool.get_tokens(doc_chunk.chunks[r].text)
                                chunk += doc_chunk.chunks[r].text
                                r += 1
                            else:
                                tokens_sub -= TokenTool.get_tokens(doc_chunk.chunks[l].text)
                                chunk = doc_chunk.chunks[l].text+chunk
                                l -= 1
                qa_cnt = division+(d_index <= remainder)
                qs = []
                answers = []
                rd = 5
                while len(qs) < qa_cnt and rd > 0:
                    rd -= 1
                    try:
                        sys_call = q_generate_prompt_template.format(
                            k=qa_cnt-len(qs),
                            content=TokenTool.get_k_tokens_words_from_content(chunk, llm.max_tokens)
                        )
                        usr_call = '请输出问题的列表'
                        sub_qs = await llm.nostream([], sys_call, usr_call)
                        sub_qs = json.loads(sub_qs)
                    except Exception as e:
                        err = f"[GenerateDataSetWorker] 生成问题失败，错误信息: {e}"
                        logging.exception(err)
                        continue
                    sub_qs = sub_qs[:qa_cnt-len(qs)]
                    sub_answers = []
                    try:
                        for q in sub_qs:
                            sys_call = answer_generate_prompt_template.format(
                                content=TokenTool.get_k_tokens_words_from_content(chunk, llm.max_tokens//8*7),
                                question=TokenTool.get_k_tokens_words_from_content(q, llm.max_tokens//8)
                            )
                            usr_call = '请输出答案'
                            sub_answer = await llm.nostream([], sys_call, usr_call)
                            sub_answers.append(sub_answer)
                    except Exception as e:
                        err = f"[GenerateDataSetWorker] 生成答案失败，错误信息: {e}"
                        logging.exception(err)
                        continue
                    for q, answer in zip(sub_qs, sub_answers):
                        if len(qa_entities) + len(qs) >= dataset_entity.data_cnt:
                            break
                        try:
                            if dataset_entity.is_data_cleared:
                                sys_call = cal_qa_score_prompt_template.format(
                                    fragment=TokenTool.get_k_tokens_words_from_content(chunk, llm.max_tokens//9*4),
                                    question=TokenTool.get_k_tokens_words_from_content(q, llm.max_tokens//9),
                                    answer=TokenTool.get_k_tokens_words_from_content(answer, llm.max_tokens//9*4)
                                )
                                usr_call = '请输出分数'
                                score = await llm.nostream([], sys_call, usr_call)
                                score = eval(score)
                                score = max(0, min(100, score))
                            else:
                                score = 100
                            if score > 60:
                                qs.append(q)
                                answers.append(answer)
                            dataset_score += score
                        except Exception as e:
                            err = f"[GenerateDataSetWorker] 计算分数失败，错误信息: {e}"
                            logging.exception(err)
                            continue
                for q, ans in zip(qs, answers):
                    qa_entity = QAEntity(
                        dataset_id=dataset_entity.id,
                        doc_id=doc_chunk.doc_id,
                        doc_name=doc_chunk.doc_name,
                        question=q,
                        answer=ans,
                        chunk=chunk,
                        chunk_type=doc_chunk.chunks[j].type)
                    qa_entities.append(qa_entity)
                if len(qa_entities) >= dataset_entity.data_cnt:
                    break
            if len(qa_entities) >= dataset_entity.data_cnt:
                break
        if len(qa_entities) > 0:
            dataset_score = dataset_score / len(qa_entities)
            dataset_score = max(0, min(100, dataset_score))
        await DatasetManager.update_dataset_by_dataset_id(
            dataset_entity.id, {'score': dataset_score})
        return qa_entities

    @staticmethod
    async def add_qa_to_db(qa_entities: list[QAEntity]) -> None:
        '''添加QA到数据库'''
        index = 0
        while index < len(qa_entities):
            try:
                await QAManager.add_qas(qa_entities[index:index+1024])
            except Exception as e:
                err = f"[GenerateDataSetWorker] 添加QA到数据库失败，错误信息: {e}"
                logging.exception(err)
            index += 1024

    @staticmethod
    async def run(task_id: uuid.UUID) -> None:
        '''运行任务'''
        try:
            task_entity = await TaskManager.get_task_by_task_id(task_id)
            if task_entity is None:
                err = f"[GenerateDataSetWorker] 任务不存在，task_id: {task_id}"
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
                err = f"[GenerateDataSetWorker] 数据集不存在，数据集ID: {task_entity.op_id}"
                logging.exception(err)
                raise Exception(err)
            await DatasetManager.update_dataset_by_dataset_id(dataset_entity.id, {"status": DataSetStatus.GENERATING.value})
            current_stage = 0
            stage_cnt = 3
            doc_chunks = await GenerateDataSetWorker.get_chunks(dataset_entity)
            current_stage += 1
            await GenerateDataSetWorker.report(task_id, "获取文档分块信息", current_stage, stage_cnt)
            qa_entities = await GenerateDataSetWorker.generate_qa(
                dataset_entity, doc_chunks, llm)
            current_stage += 1
            await GenerateDataSetWorker.report(task_id, "生成QA", current_stage, stage_cnt)
            await GenerateDataSetWorker.add_qa_to_db(qa_entities)
            current_stage += 1
            await GenerateDataSetWorker.report(task_id, "添加QA到数据库", current_stage, stage_cnt)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.SUCCESS.value))
        except Exception as e:
            err = f"[GenerateDataSetWorker] 任务失败，task_id: {task_id}，错误信息: {e}"
            logging.exception(err)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.FAILED.value))
            await GenerateDataSetWorker.report(task_id, err, 0, 1)

    @staticmethod
    async def stop(task_id: uuid.UUID) -> uuid.UUID:
        '''停止任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ExportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.IDLE.value})
        if task_entity.status == TaskStatus.PENDING.value or task_entity.status == TaskStatus.RUNNING.value or task_entity.status == TaskStatus.FAILED.value:
            await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"score": -1})
            await QAManager.update_qa_by_dataset_id(task_entity.op_id, {"status": QAStatus.DELETED.value})
        return task_id
