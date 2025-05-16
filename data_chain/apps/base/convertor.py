# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from typing import Any, Dict
import base64
import hashlib
import json
import uuid
from data_chain.entities.request_data import (
    CreateTeamRequest,
    UpdateKnowledgeBaseRequest,
    DocumentType as DocumentTypeRequest,
    CreateKnowledgeBaseRequest,
    UpdateDocumentRequest,
    UpdateChunkRequest,
    CreateDatasetRequest,
    CreateTestingRequest,
    UpdateTestingRequest
)
from data_chain.entities.response_data import (
    User,
    Team,
    Knowledgebase,
    DocumentType as DocumentTypeResponse,
    Document,
    Chunk,
    LLM,
    Dataset,
    Data,
    Testing,
    TestCase,
    Task
)

from data_chain.entities.enum import (
    UserStatus,
    TeamStatus,
    TaskType,
    TaskStatus,
    KnowledgeBaseStatus,
    DocumentStatus,
    ChunkType,
    SearchMethod,
    TestingStatus,
    TestCaseStatus
)
from data_chain.entities.common import default_roles
from data_chain.stores.database.database import (
    UserEntity,
    TeamEntity,
    KnowledgeBaseEntity,
    DocumentTypeEntity,
    DocumentEntity,
    ChunkEntity,
    DataSetEntity,
    DataSetDocEntity,
    QAEntity,
    TestingEntity,
    TestCaseEntity,
    TaskEntity,
    TaskReportEntity,
    TeamUserEntity,
    UserRoleEntity,
    RoleEntity,
    RoleActionEntity
)
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging


class Convertor:
    """数据转换器"""

    @staticmethod
    async def convert_request_to_dict(req: Any) -> dict:
        """将请求转换为字典"""
        try:
            req_dict = req.dict(exclude_none=True)
            return req_dict
        except Exception as e:
            err = "请求转换为字典失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_user_sub_to_user_entity(user_sub: str) -> UserEntity:
        """将用户ID转换为用户实体"""
        try:
            user_entity = UserEntity(id=user_sub, name=user_sub, status=UserStatus.ACTIVE)
            return user_entity
        except Exception as e:
            err = "用户ID转换为用户实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_user_entity_to_user(user_entity: UserEntity) -> User:
        """将用户实体转换为用户"""
        try:
            user = User(id=user_entity.id, name=user_entity.name)
            return user
        except Exception as e:
            err = "用户实体转换为用户失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_create_team_request_to_team_entity(
            user_sub: str, req: CreateTeamRequest) -> TeamEntity:
        """将创建团队请求转换为团队实体"""
        try:
            team_entity = TeamEntity(
                author_id=user_sub,
                author_name=user_sub,
                name=req.team_name,
                description=req.description,
                member_cnt=1,
                is_public=req.is_public,
                status=TeamStatus.EXISTED
            )
            return team_entity
        except Exception as e:
            err = "创建团队请求转换为团队实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_update_team_request_to_dict(
            req: CreateTeamRequest) -> dict:
        """将更新团队请求转换为字典"""
        try:

            req_dict = {
                'name': req.team_name,
                'description': req.description,
                'is_public': req.is_public
            }
            return req_dict
        except Exception as e:
            err = "更新团队请求转换为字典失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_team_entity_to_team(team_entity: TeamEntity) -> Team:
        """将团队实体转换为团队"""
        try:
            team = Team(
                teamId=team_entity.id,
                teamName=team_entity.name,
                description=team_entity.description,
                authorName=team_entity.author_name,
                memberCount=team_entity.member_cnt,
                isPublic=team_entity.is_public,
                createdTime=team_entity.created_time.strftime('%Y-%m-%d %H:%M')
            )
            return team
        except Exception as e:
            err = "团队实体转换为团队失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_user_sub_and_team_id_to_team_user_entity(
            user_sub: str, team_id: uuid.UUID) -> TeamUserEntity:
        """将用户ID和团队ID转换为团队用户实体"""
        try:
            team_user_entity = TeamUserEntity(
                user_id=user_sub,
                team_id=team_id
            )
            return team_user_entity
        except Exception as e:
            err = "用户ID和团队ID转换为团队用户实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_default_role_dict_to_role_entity(
            team_id: uuid.UUID, default_role_dict: Dict[str, Any]) -> RoleEntity:
        """将默认角色字典转换为角色实体"""
        try:
            role_entity = RoleEntity(
                team_id=team_id,
                name=default_role_dict["name"],
                is_unique=default_role_dict["is_unique"],
                editable=default_role_dict["editable"],
            )
            return role_entity
        except Exception as e:
            err = "默认角色字典转换为角色实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_default_role_action_dicts_to_role_action_entities(
            role_id: uuid.UUID,
            default_role_action_dicts: list[Dict[str, Any]]) -> list[RoleActionEntity]:
        """将默认角色操作字典转换为角色操作实体"""
        try:
            role_action_entities = []
            for default_role_action_dict in default_role_action_dicts:
                role_action_entity = RoleActionEntity(
                    role_id=role_id,
                    action=default_role_action_dict["action"],
                )
                role_action_entities.append(role_action_entity)
            return role_action_entities
        except Exception as e:
            err = "默认角色操作字典转换为角色操作实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_user_sub_role_id_and_team_id_to_user_role_entity(
            user_sub: str, role_id: uuid.UUID, team_id: uuid.UUID) -> UserRoleEntity:
        """将用户ID、角色ID和团队ID转换为用户角色实体"""
        try:
            user_role_entity = UserRoleEntity(
                user_id=user_sub,
                role_id=role_id,
                team_id=team_id
            )
            return user_role_entity
        except Exception as e:
            err = "用户ID、角色ID和团队ID转换为用户角色实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_update_knowledge_base_request_to_dict(
            req: UpdateKnowledgeBaseRequest) -> dict:
        """将更新知识库请求转换为字典"""
        try:
            req_dict = {
                'name': req.kb_name,
                'description': req.description,
                'tokenizer': req.tokenizer.value,
                'upload_count_limit': req.upload_count_limit,
                'upload_size_limit': req.upload_size_limit,
                'default_parse_method': req.default_parse_method.value,
                'default_chunk_size': req.default_chunk_size
            }
            return req_dict
        except Exception as e:
            err = "更新知识库请求转换为字典失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_knowledge_base_entity_to_knowledge_base(
            knowledge_base_entity: KnowledgeBaseEntity) -> Knowledgebase:
        """将知识库实体转换为知识库"""
        try:
            knowledge_base = Knowledgebase(
                kbId=knowledge_base_entity.id,
                kbName=knowledge_base_entity.name,
                authorName=knowledge_base_entity.author_name,
                tokenizer=knowledge_base_entity.tokenizer,
                embeddingModel=knowledge_base_entity.embedding_model,
                description=knowledge_base_entity.description,
                docCnt=knowledge_base_entity.doc_cnt,
                docSize=knowledge_base_entity.doc_size,
                uploadCountLimit=knowledge_base_entity.upload_count_limit,
                uploadSizeLimit=knowledge_base_entity.upload_size_limit,
                defaultParseMethod=knowledge_base_entity.default_parse_method,
                defaultChunkSize=knowledge_base_entity.default_chunk_size,
                createdTime=knowledge_base_entity.created_time.strftime('%Y-%m-%d %H:%M'),
                docTypes=[],
            )
            return knowledge_base
        except Exception as e:
            err = "知识库实体转换为知识库失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_document_type_entity_to_document_type_response(
            document_type_entity: DocumentTypeEntity) -> DocumentTypeResponse:
        """将文档类型实体转换为文档类型"""
        try:
            document_type = DocumentTypeResponse(
                docTypeId=document_type_entity.id,
                docTypeName=document_type_entity.name
            )
            return document_type
        except Exception as e:
            err = "文档类型实体转换为文档类型失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_create_knowledge_base_request_to_knowledge_base_entity(
            user_sub: str, team_id: uuid.UUID, req: CreateKnowledgeBaseRequest) -> KnowledgeBaseEntity:
        """将创建知识库请求转换为知识库实体"""
        try:
            knowledge_base_entity = KnowledgeBaseEntity(
                team_id=team_id,
                author_id=user_sub,
                author_name=user_sub,
                name=req.kb_name,
                tokenizer=req.tokenizer.value,
                description=req.description,
                embedding_model=req.embedding_model,
                upload_count_limit=req.upload_count_limit,
                upload_size_limit=req.upload_size_limit,
                default_parse_method=req.default_parse_method.value,
                default_chunk_size=req.default_chunk_size,
            )
            return knowledge_base_entity
        except Exception as e:
            err = "创建知识库请求转换为知识库实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_kb_id_and_requeset_document_type_to_document_type_entity(
            kb_id: uuid.UUID, document_type: DocumentTypeRequest) -> DocumentTypeEntity:
        """将知识库ID和文档类型转换为文档类型实体"""
        try:
            document_type_entity = DocumentTypeEntity(
                id=document_type.doc_type_id,
                kb_id=kb_id,
                name=document_type.doc_type_name
            )
            return document_type_entity
        except Exception as e:
            err = "知识库ID和文档类型转换为文档类型实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_document_entity_and_document_type_entity_to_document(
            document_entity: DocumentEntity, document_type_entity: DocumentTypeEntity) -> Document:
        """将文档实体和文档类型实体转换为文档"""
        try:
            document_type_response = await Convertor.convert_document_type_entity_to_document_type_response(
                document_type_entity
            )
            document = Document(
                docId=document_entity.id,
                docName=document_entity.name,
                docType=document_type_response,
                chunkSize=document_entity.chunk_size,
                createdTime=document_entity.created_time.strftime('%Y-%m-%d %H:%M'),
                parseMethod=document_entity.parse_method,
                enabled=document_entity.enabled,
                authorName=document_entity.author_name,
                status=DocumentStatus(document_entity.status),
            )
            return document
        except Exception as e:
            err = "文档实体和文档类型实体转换为文档失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_task_entity_to_task(
            task_entity: TaskEntity, task_report: TaskReportEntity = None) -> Task:
        """将任务实体和任务报告实体转换为任务"""
        try:
            task_completed = 0
            finished_time = None
            if task_report is not None:
                task_completed = task_report.current_stage/task_report.stage_cnt*100
                finished_time = task_report.created_time.strftime('%Y-%m-%d %H:%M')
            task = Task(
                opId=task_entity.op_id,
                opName=task_entity.op_name,
                taskId=task_entity.id,
                taskStatus=TaskStatus(task_entity.status),
                taskType=TaskType(task_entity.type),
                taskCompleted=task_completed,
                finishedTime=finished_time,
                createdTime=task_entity.created_time.strftime('%Y-%m-%d %H:%M')
            )
            return task
        except Exception as e:
            err = "任务实体和任务报告实体转换为任务失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_update_document_request_to_dict(
            req: UpdateDocumentRequest) -> dict:
        """将更新文档请求转换为字典"""
        try:
            req_dict = {
                'name': req.doc_name,
                'type_id': req.doc_type_id,
                'parse_method': req.parse_method.value,
                'chunk_size': req.chunk_size,
                'enabled': req.enabled
            }
            return req_dict
        except Exception as e:
            err = "更新文档请求转换为字典失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_update_chunk_request_to_dict(
            req: UpdateChunkRequest) -> dict:
        """将更新分片请求转换为字典"""
        try:
            req_dict = {
            }
            if req.text is not None:
                req_dict['text'] = req.text
            if req.enabled is not None:
                req_dict['enabled'] = req.enabled
            return req_dict
        except Exception as e:
            err = "更新分片请求转换为字典失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_chunk_entity_to_chunk(
            chunk_entity: ChunkEntity) -> Chunk:
        """将chunk实体转换为chunk"""
        try:
            chunk = Chunk(
                chunkId=chunk_entity.id,
                chunkType=ChunkType(chunk_entity.type),
                text=chunk_entity.text,
                enabled=chunk_entity.enabled,
            )
            return chunk
        except Exception as e:
            err = "chunk实体转换为chunk失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_dataset_entity_to_dataset(
            dataset_entity: DataSetEntity) -> Dataset:
        """将数据集实体转换为数据集"""
        try:
            dataset = Dataset(
                datasetId=dataset_entity.id,
                datasetName=dataset_entity.name,
                description=dataset_entity.description,
                dataCnt=dataset_entity.data_cnt,
                isDataCleared=dataset_entity.is_data_cleared,
                isChunkRelated=dataset_entity.is_chunk_related,
                isImported=dataset_entity.is_imported,
                score=dataset_entity.score,
                authorName=dataset_entity.author_name,
                status=dataset_entity.status,
            )
            return dataset
        except Exception as e:
            err = "数据集实体转换为数据集失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_llm_config_to_llm() -> LLM:
        try:
            with open('./data_chain/llm/icon/ollama.svg', 'r', encoding='utf-8') as file:
                svg_content = file.read()
            svg_bytes = svg_content.encode('utf-8')
            base64_bytes = base64.b64encode(svg_bytes)
            base64_string = base64_bytes.decode('utf-8')
            config_params = {
                'MODEL_NAME': config['MODEL_NAME'],
                'OPENAI_API_BASE': config['OPENAI_API_BASE'],
                'OPENAI_API_KEY': config['OPENAI_API_KEY'],
                'REQUEST_TIMEOUT': config['REQUEST_TIMEOUT'],
                'MAX_TOKENS': config['MAX_TOKENS'],
                'TEMPERATURE': config['TEMPERATURE']
            }
            config_json = json.dumps(config_params, sort_keys=True, ensure_ascii=False).encode('utf-8')
            hash_object = hashlib.sha256(config_json)
            hash_hex = hash_object.hexdigest()
            llm = LLM(
                llmId=hash_hex,
                llmName=config['MODEL_NAME'],
                llmIcon=base64_string,
            )
            return llm
        except Exception as e:
            err = "llm配置转换为llm失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_qa_entity_to_data(
            qa_entity: QAEntity) -> Data:
        """将QA实体转换为数据"""
        try:
            data = Data(
                dataId=qa_entity.id,
                docName=qa_entity.doc_name,
                question=qa_entity.question,
                answer=qa_entity.answer,
                chunk=qa_entity.chunk,
                chunkType=ChunkType(qa_entity.chunk_type),
            )
            return data
        except Exception as e:
            err = "QA实体转换为数据失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_create_dataset_request_to_dataset_entity(
            user_sub: str, team_id: str, req: CreateDatasetRequest) -> DataSetEntity:
        """将创建数据集请求转换为数据集实体"""
        try:
            dataset_entity = DataSetEntity(
                team_id=team_id,
                author_id=user_sub,
                author_name=user_sub,
                kb_id=req.kb_id,
                llm_id=req.llm_id,
                name=req.dataset_name,
                description=req.description,
                data_cnt=req.data_cnt,
                is_data_cleared=req.is_data_cleared,
                is_chunk_related=req.is_chunk_related,
            )
            return dataset_entity
        except Exception as e:
            err = "创建数据集请求转换为数据集实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_dataset_id_and_doc_id_to_dataset_doc_entity(
            dataset_id: uuid.UUID, doc_id: uuid.UUID) -> DataSetDocEntity:
        """将数据集ID和文档ID转换为数据集文档实体"""
        try:
            dataset_doc_entity = DataSetDocEntity(
                dataset_id=dataset_id,
                doc_id=doc_id
            )
            return dataset_doc_entity
        except Exception as e:
            err = "数据集ID和文档ID转换为数据集文档实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_testing_entity_to_testing(testing_entity: TestingEntity) -> Testing:
        """将测试实体转换为测试"""
        try:
            testing = Testing(
                testingId=testing_entity.id,
                testingName=testing_entity.name,
                description=testing_entity.description,
                searchMethod=SearchMethod(testing_entity.search_method),
                aveScore=round(testing_entity.ave_score, 2),
                avePre=round(testing_entity.ave_pre, 2),
                aveRec=round(testing_entity.ave_rec, 2),
                aveFai=round(testing_entity.ave_fai, 2),
                aveRel=round(testing_entity.ave_rel, 2),
                aveLcs=round(testing_entity.ave_lcs, 2),
                aveLeve=round(testing_entity.ave_leve, 2),
                aveJac=round(testing_entity.ave_jac, 2),
                authorName=testing_entity.author_name,
                topk=testing_entity.top_k,
                status=TestingStatus(testing_entity.status),
            )
            return testing
        except Exception as e:
            err = "测试实体转换为测试失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_test_case_entity_to_test_case(test_case_entity: TestCaseEntity) -> TestCase:
        """将测试用例实体转换为测试用例"""
        try:
            test_case = TestCase(
                testCaseId=test_case_entity.id,
                question=test_case_entity.question,
                answer=test_case_entity.answer,
                llmAnswer=test_case_entity.llm_answer,
                relatedChunk=test_case_entity.related_chunk,
                docName=test_case_entity.doc_name,
                score=round(test_case_entity.score, 2),
                pre=round(test_case_entity.pre, 2),
                rec=round(test_case_entity.rec, 2),
                fai=round(test_case_entity.fai, 2),
                rel=round(test_case_entity.rel, 2),
                lcs=round(test_case_entity.lcs, 2),
                leve=round(test_case_entity.leve, 2),
                jac=round(test_case_entity.jac, 2),
                status=TestCaseStatus(test_case_entity.status),
            )
            return test_case
        except Exception as e:
            err = "测试用例实体转换为测试用例失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_create_testing_request_to_testing_entity(
            user_sub: str, team_id: uuid.UUID, kb_id: uuid.UUID, req: CreateTestingRequest) -> TestingEntity:
        """将创建测试请求转换为测试实体"""
        try:
            testing_entity = TestingEntity(
                team_id=team_id,
                kb_id=kb_id,
                author_id=user_sub,
                author_name=user_sub,
                dataset_id=req.dataset_id,
                name=req.testing_name,
                description=req.description,
                llm_id=req.llm_id,
                search_method=req.search_method.value,
                top_k=req.top_k,
            )
            return testing_entity
        except Exception as e:
            err = "创建测试请求转换为测试实体失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_update_testing_request_to_dict(req: UpdateTestingRequest) -> dict:
        """将更新测试请求转换为字典"""
        try:
            req_dict = {
                'name': req.testing_name,
                'description': req.description,
                'llm_id': req.llm_id,
                'search_method': req.search_method.value,
                'top_k': req.top_k,
            }
            return req_dict
        except Exception as e:
            err = "更新测试请求转换为字典失败"
            logging.exception("[Convertor] %s", err)
            raise e
