# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
import os
import shutil
import yaml
import json
import random
import pandas as pd
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.llm.llm import LLM
from data_chain.rag.base_searcher import BaseSearcher
from data_chain.entities.enum import TaskType, TaskStatus, KnowledgeBaseStatus, DocumentStatus, DataSetStatus, QAStatus, TestingStatus, TestCaseStatus
from data_chain.entities.common import DEFAULT_DOC_TYPE_ID, TESTING_REPORT_PATH_IN_OS, TESTING_REPORT_PATH_IN_MINIO
from data_chain.parser.parse_result import ParseResult, ParseNode
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.parser.handler.json_parser import JsonParser
from data_chain.parser.handler.yaml_parser import YamlParser
from data_chain.parser.handler.xlsx_parser import XlsxParser
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.manager.dataset_manager import DatasetManager
from data_chain.manager.testing_manager import TestingManager
from data_chain.manager.testcase_manager import TestCaseManager
from data_chain.manager.qa_manager import QAManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.stores.database.database import TaskEntity, QAEntity, DataSetEntity, DataSetDocEntity, TestingEntity, TestCaseEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.mongodb.mongodb import Task
from data_chain.config.config import config


class TestingWorker(BaseWorker):
    """
    TestingWorker
    """
    name = TaskType.TESTING_RUN.value

    @staticmethod
    async def init(testing_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        testing_entity = await TestingManager.get_testing_by_testing_id(testing_id)
        if testing_entity is None:
            err = f"[TestingWorker] 测试不存在，测试ID: {testing_id}"
            logging.exception(err)
            return None
        await TestCaseManager.update_test_case_by_testing_id(testing_id, {"status": TestCaseStatus.DELETED.value})
        testing_entity = await TestingManager.update_testing_by_testing_id(testing_id, {"status": DataSetStatus.PENDING.value})
        task_entity = TaskEntity(
            team_id=testing_entity.team_id,
            user_id=testing_entity.author_id,
            op_id=testing_entity.id,
            op_name=testing_entity.name,
            type=TaskType.TESTING_RUN.value,
            retry=0,
            status=TaskStatus.PENDING.value)
        task_entity = await TaskManager.add_task(task_entity)
        await TestingManager.update_testing_by_testing_id(testing_id, {
            "ave_score": -1,
            "ave_pre": -1,
            "ave_rec": -1,
            "ave_fai": -1,
            "ave_rel": -1,
            "ave_lcs": -1,
            "ave_leve": -1,
            "ave_jac": -1,
        })
        await MinIO.delete_object(
            TESTING_REPORT_PATH_IN_MINIO,
            str(testing_id)
        )
        return task_entity.id

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[TestingWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return False
        tmp_path = os.path.join(TESTING_REPORT_PATH_IN_OS, str(task_entity.id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        await TestCaseManager.update_test_case_by_testing_id(task_entity.op_id, {"status": TestCaseStatus.DELETED.value})
        await MinIO.delete_object(
            TESTING_REPORT_PATH_IN_MINIO,
            str(task_entity.op_id)
        )
        await TestingManager.update_testing_by_testing_id(task_entity.op_id, {
            "ave_score": -1,
            "ave_pre": -1,
            "ave_rec": -1,
            "ave_fai": -1,
            "ave_rel": -1,
            "ave_lcs": -1,
            "ave_leve": -1,
            "ave_jac": -1,
        })
        if task_entity.retry < config['TASK_RETRY_TIME_LIMIT']:
            await TestingManager.update_testing_by_testing_id(task_entity.op_id, {"status": TestingStatus.PENDING.value})
            return True
        else:
            await TestingManager.update_testing_by_testing_id(task_entity.op_id, {"status": TestingStatus.IDLE.value})
            return False

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[TestingWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        tmp_path = os.path.join(TESTING_REPORT_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        await TestingManager.update_testing_by_testing_id(task_entity.op_id, {"status": TestingStatus.IDLE.value})
        return task_id

    @staticmethod
    async def init_path(task_id: uuid.UUID) -> tuple:
        '''初始化路径'''
        tmp_path = os.path.join(TESTING_REPORT_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.makedirs(tmp_path)
        return tmp_path

    @staticmethod
    async def testing(testing_entity: TestingEntity, qa_entities: list[QAEntity], llm: LLM) -> list[TestCaseEntity]:
        '''测试数据集'''
        testcase_entities = []
        with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
            prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
        prompt_template = prompt_dict.get('LLM_PROMPT_TEMPLATE', '')
        for qa_entity in qa_entities:
            question = qa_entity.question
            answer = qa_entity.answer
            chunk = qa_entity.chunk
            chunk_entities = await BaseSearcher.search(testing_entity.search_method, testing_entity.kb_id, question, top_k=2*testing_entity.top_k, doc_ids=None, banned_ids=[])
            related_chunk_entities = []
            banned_ids = [chunk_entity.id for chunk_entity in chunk_entities]
            divide_tokens = llm.max_tokens // len(chunk_entities) if chunk_entities else llm.max_tokens
            leave_tokens = 0
            token_sum = 0
            for chunk_entity in chunk_entities:
                token_sum += chunk_entity.tokens
            for chunk_entity in chunk_entities:
                leave_tokens = leave_tokens+divide_tokens
                sub_related_chunk_entities = await BaseSearcher.related_surround_chunk(chunk_entity, leave_tokens-chunk_entity.tokens, banned_ids)
                banned_ids += [sub_chunk_entity.id for sub_chunk_entity in sub_related_chunk_entities]
                related_chunk_entities += sub_related_chunk_entities
                for related_chunk_entity in sub_related_chunk_entities:
                    token_sum += related_chunk_entity.tokens
                    leave_tokens -= related_chunk_entity.tokens
                leave_tokens = max(leave_tokens, 0)
                if token_sum >= llm.max_tokens:
                    break
            chunk_entities += related_chunk_entities
            doc_chunk_dict = {}
            for chunk_entity in chunk_entities:
                if chunk_entity.doc_id not in doc_chunk_dict:
                    doc_chunk_dict[chunk_entity.doc_id] = []
                doc_chunk_dict[chunk_entity.doc_id].append(chunk_entity)
            bac_info = ''
            for doc_id, chunk_entities in doc_chunk_dict.items():
                chunk_entities.sort(key=lambda x: x.global_offset)
                document_entity = await DocumentManager.get_document_by_doc_id(doc_id)
                sub_bac_info = f"文档名称: {document_entity.name}\n"
                for chunk_entity in chunk_entities:
                    sub_bac_info += chunk_entity.text
                bac_info += sub_bac_info+'\n'
            bac_info = TokenTool.get_k_tokens_words_from_content(bac_info, llm.max_tokens//8*7)
            prompt = prompt_template.format(
                bac_info=bac_info
            )
            llm_answer = await llm.nostream([], prompt, question)
            sub_socres = []
            pre = await TokenTool.cal_precision(question, answer, llm)
            if pre != -1:
                sub_socres.append(pre)
            rec = await TokenTool.cal_recall(answer, llm_answer, llm)
            if rec != -1:
                sub_socres.append(rec)
            fai = await TokenTool.cal_faithfulness(question, llm_answer, bac_info, llm)
            if fai != -1:
                sub_socres.append(fai)
            rel = await TokenTool.cal_relevance(question, llm_answer, llm)
            if rel != -1:
                sub_socres.append(rel)
            lcs = TokenTool.cal_lcs(answer, llm_answer)
            if lcs != -1:
                sub_socres.append(lcs)
            leve = TokenTool.cal_leve(answer, llm_answer)
            if leve != -1:
                sub_socres.append(leve)
            jac = TokenTool.cal_jac(answer, llm_answer)
            if jac != -1:
                sub_socres.append(jac)
            score = -1
            if sub_socres:
                score = sum(sub_socres) / len(sub_socres)
            test_case_entity = TestCaseEntity(
                testing_id=testing_entity.id,
                question=question,
                answer=answer,
                chunk=chunk,
                doc_name=qa_entity.doc_name,
                llm_answer=llm_answer,
                related_chunk=bac_info,
                score=score,
                pre=pre,
                rec=rec,
                fai=fai,
                rel=rel,
                lcs=lcs,
                leve=leve,
                jac=jac
            )
            testcase_entities.append(test_case_entity)
        index = 0
        while index < len(testcase_entities):
            await TestCaseManager.add_test_cases(testcase_entities[index:index+1024])
            index += 1024
        return testcase_entities

    @staticmethod
    async def update_testing_score(testing_id: uuid.UUID, testcase_entities: list[TestCaseEntity]) -> TestingEntity:
        '''更新测试分数'''
        score_list = []
        for test_case_entity in testcase_entities:
            if test_case_entity.score != -1:
                score_list.append(test_case_entity.score)
        pre_list = []
        for test_case_entity in testcase_entities:
            if test_case_entity.pre != -1:
                pre_list.append(test_case_entity.pre)
        rec_list = []
        for test_case_entity in testcase_entities:
            if test_case_entity.rec != -1:
                rec_list.append(test_case_entity.rec)
        fai_list = []
        for test_case_entity in testcase_entities:
            if test_case_entity.fai != -1:
                fai_list.append(test_case_entity.fai)
        rel_list = []
        for test_case_entity in testcase_entities:
            if test_case_entity.rel != -1:
                rel_list.append(test_case_entity.rel)
        lcs_list = []
        for test_case_entity in testcase_entities:
            if test_case_entity.lcs != -1:
                lcs_list.append(test_case_entity.lcs)
        leve_list = []
        for test_case_entity in testcase_entities:
            if test_case_entity.leve != -1:
                leve_list.append(test_case_entity.leve)
        jac_list = []
        for test_case_entity in testcase_entities:
            if test_case_entity.jac != -1:
                jac_list.append(test_case_entity.jac)
        ave_score = -1
        if score_list:
            ave_score = sum(score_list) / len(score_list)
        ave_pre = -1
        if pre_list:
            ave_pre = sum(pre_list) / len(pre_list)
        ave_rec = -1
        if rec_list:
            ave_rec = sum(rec_list) / len(rec_list)
        ave_fai = -1
        if fai_list:
            ave_fai = sum(fai_list) / len(fai_list)
        ave_rel = -1
        if rel_list:
            ave_rel = sum(rel_list) / len(rel_list)
        ave_lcs = -1
        if lcs_list:
            ave_lcs = sum(lcs_list) / len(lcs_list)
        ave_leve = -1
        if leve_list:
            ave_leve = sum(leve_list) / len(leve_list)
        ave_jac = -1
        if jac_list:
            ave_jac = sum(jac_list) / len(jac_list)
        testing_entity = await TestingManager.update_testing_by_testing_id(testing_id, {
            "ave_score": ave_score,
            "ave_pre": ave_pre,
            "ave_rec": ave_rec,
            "ave_fai": ave_fai,
            "ave_rel": ave_rel,
            "ave_lcs": ave_lcs,
            "ave_leve": ave_leve,
            "ave_jac": ave_jac
        })
        return testing_entity

    @staticmethod
    async def generate_report_and_upload_to_minio(
            dataset_entity: DataSetEntity, testing_entity: TestingEntity, testcase_entities: list[TestCaseEntity],
            tmp_path: str):
        '''生成报告并上传到minio'''
        xlsx_path = os.path.join(tmp_path, "report.xlsx")
        kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(testing_entity.kb_id)
        doc_cnt = await DocumentManager.get_doc_cnt_by_kb_id(testing_entity.kb_id)
        chunk_cnt = await ChunkManager.get_chunk_cnt_by_kb_id(testing_entity.kb_id)
        chunk_tokens = await ChunkManager.get_chunk_tokens_by_kb_id(testing_entity.kb_id)
        ave_chunk_tokens = 0
        if chunk_cnt != 0:
            ave_chunk_tokens = chunk_tokens / chunk_cnt

        def clean_value(value):
            """清洗单元格值中的非法字符"""
            import re
            if not isinstance(value, str):
                return value

            # 移除Excel不允许的字符（可根据实际报错调整）
            invalid_chars = re.compile(r'[\000-\010\013\014\016-\037]')
            cleaned_value = invalid_chars.sub('', value)

            # 额外处理常见问题字符（如替换冒号、斜杠等）
            problematic_chars = {'\\': '', '/': '', '*': '', '?': '', '"': "'", '<': '', '>': '', ':': ''}
            for char, replacement in problematic_chars.items():
                cleaned_value = cleaned_value.replace(char, replacement)

            return cleaned_value

        test_config = {
            'kb_name(知识库名称)': [clean_value(kb_entity.name)],
            'dataset_name(数据集名称)': [clean_value(dataset_entity.name)],
            'doc_cnt(文档数量)': [doc_cnt],
            'chunk_cnt(分片数量)': [chunk_cnt],
            'chunk_tokens(分片平均token数)': [ave_chunk_tokens],
            'llm(大模型)': [clean_value(config['MODEL_NAME'])],
            'embedding_model(向量检索)': [clean_value(config['EMBEDDING_MODEL_NAME'])],
        }
        model_config_df = pd.DataFrame(test_config)
        ave_result = {
            'ave_score(平均综合得分)': [testing_entity.ave_score],
            'ave_pre(平均准确率)': [testing_entity.ave_pre],
            'ave_rec(平均召回率)': [testing_entity.ave_rec],
            'ave_fai(平均可信度)': [testing_entity.ave_fai],
            'ave_rel(平均相关度)': [testing_entity.ave_rel],
            'ave_lcs(平均最长公共子序列得分)': [testing_entity.ave_lcs],
            'ave_leve(平均编辑距离得分)': [testing_entity.ave_leve],
            'ave_jac(平均杰卡德相似度)': [testing_entity.ave_jac]
        }
        ave_result_df = pd.DataFrame(ave_result)
        test_case_dict = {
            'question': [],
            'answer': [],
            'chunk': [],
            'doc_name': [],
            'llm_answer': [],
            'related_chunk': [],
            'score(综合得分)': [],
            'pre(准确率)': [],
            'rec(召回率)': [],
            'fai(可信度)': [],
            'rel(相关性)': [],
            'lcs(最长公共子序列得分)': [],
            'leve(编辑距离得分)': [],
            'jac(杰卡德相似度)': []
        }
        for test_case_entity in testcase_entities:
            test_case_dict['question'].append(clean_value(test_case_entity.question))
            test_case_dict['answer'].append(clean_value(test_case_entity.answer))
            test_case_dict['chunk'].append(clean_value(test_case_entity.chunk))
            test_case_dict['doc_name'].append(clean_value(test_case_entity.doc_name))
            test_case_dict['llm_answer'].append(test_case_entity.llm_answer)
            test_case_dict['related_chunk'].append(test_case_entity.related_chunk)
            test_case_dict['score(综合得分)'].append(test_case_entity.score)
            test_case_dict['pre(准确率)'].append(test_case_entity.pre)
            test_case_dict['rec(召回率)'].append(test_case_entity.rec)
            test_case_dict['fai(可信度)'].append(test_case_entity.fai)
            test_case_dict['rel(相关性)'].append(test_case_entity.rel)
            test_case_dict['lcs(最长公共子序列得分)'].append(test_case_entity.lcs)
            test_case_dict['leve(编辑距离得分)'].append(test_case_entity.leve)
            test_case_dict['jac(杰卡德相似度)'].append(test_case_entity.jac)
        test_case_df = pd.DataFrame(test_case_dict)
        with pd.ExcelWriter(xlsx_path, engine='xlsxwriter') as writer:
            model_config_df.to_excel(writer, sheet_name='config(配置)', index=False)
            ave_result_df.to_excel(writer, sheet_name='ave_result(平均结果)', index=False)
            test_case_df.to_excel(writer, sheet_name='test_case(测试结果)', index=False)
        await MinIO.put_object(
            TESTING_REPORT_PATH_IN_MINIO,
            str(testing_entity.id),
            xlsx_path
        )

    @staticmethod
    async def run(task_id: uuid.UUID) -> None:
        '''运行任务'''
        try:
            task_entity = await TaskManager.get_task_by_task_id(task_id)
            if task_entity is None:
                err = f"[TestingWorker] 任务不存在，task_id: {task_id}"
                logging.exception(err)
                raise Exception(err)
            testing_entity = await TestingManager.get_testing_by_testing_id(task_entity.op_id)
            if testing_entity is None:
                err = f"[TestingWorker] 测试不存在，测试ID: {task_id}"
                logging.exception(err)
                raise Exception(err)
            await TestingManager.update_testing_by_testing_id(testing_entity.id, {"status": TestingStatus.RUNNING.value})
            current_stage = 0
            stage_cnt = 4
            llm = LLM(
                openai_api_key=config['OPENAI_API_KEY'],
                openai_api_base=config['OPENAI_API_BASE'],
                model_name=config['MODEL_NAME'],
                max_tokens=config['MAX_TOKENS'],
            )
            tmp_path = await TestingWorker.init_path(task_id)
            current_stage += 1
            await TestingWorker.report(task_id, "初始化路径", current_stage, stage_cnt)
            qa_entities = await QAManager.list_all_qa_by_dataset_id(testing_entity.dataset_id)
            testcase_entities = await TestingWorker.testing(testing_entity, qa_entities, llm)
            current_stage += 1
            await TestingWorker.report(task_id, "测试完成", current_stage, stage_cnt)
            testing_entity = await TestingWorker.update_testing_score(testing_entity.id, testcase_entities)
            current_stage += 1
            await TestingWorker.report(task_id, "更新测试分数", current_stage, stage_cnt)
            dataset_entity = await DatasetManager.get_dataset_by_dataset_id(testing_entity.dataset_id)
            await TestingWorker.generate_report_and_upload_to_minio(dataset_entity, testing_entity, testcase_entities, tmp_path)
            current_stage += 1
            await TestingWorker.report(task_id, "生成报告并上传到minio", current_stage, stage_cnt)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.SUCCESS.value))
        except Exception as e:
            err = f"[TestingWorker] 任务失败，task_id: {task_id}, 错误信息: {e}"
            logging.exception(err)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.FAILED.value))
            await TestingWorker.report(task_id, "任务失败", 0, 1)

    @staticmethod
    async def stop(task_id: uuid.UUID) -> uuid.UUID:
        '''停止任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[TestingWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await TestingManager.update_testing_by_testing_id(task_entity.op_id, {"status": TestingStatus.IDLE.value})
        tmp_path = os.path.join(TESTING_REPORT_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        if task_entity.status == TaskStatus.PENDING.value or task_entity.status == TaskStatus.RUNNING.value or task_entity.status == TaskStatus.FAILED.value:
            await TestCaseManager.update_test_case_by_testing_id(task_entity.op_id, {"status": TestCaseStatus.DELETED.value})
            await MinIO.delete_object(
                TESTING_REPORT_PATH_IN_MINIO,
                str(task_entity.op_id)
            )
            await TestingManager.update_testing_by_testing_id(task_entity.op_id, {
                "ave_score": -1,
                "ave_pre": -1,
                "ave_rec": -1,
                "ave_fai": -1,
                "ave_rel": -1,
                "ave_lcs": -1,
                "ave_leve": -1,
                "ave_jac": -1,
            })
        return task_id
