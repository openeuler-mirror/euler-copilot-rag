# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import aiofiles
import uuid
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
import os
import shutil
import yaml
from data_chain.logger.logger import logger as logging
from data_chain.entities.request_data import (
    ListTeamRequest,
    CreateKnowledgeBaseRequest,
    DocumentType as DocumentTypeRequest,
    ListKnowledgeBaseRequest,
    UpdateKnowledgeBaseRequest
)
from data_chain.entities.response_data import (
    TeamKnowledgebase,
    ListAllKnowledgeBaseMsg,
    Team,
    DocumentType as DocumentTypeResponse,
    ListKnowledgeBaseMsg,
    ListDocumentTypesResponse)
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.apps.service.task_queue_service import TaskQueueService
from data_chain.entities.enum import Tokenizer, ParseMethod, TeamType, TeamStatus, KnowledgeBaseStatus, TaskType
from data_chain.entities.common import DEFAULt_DOC_TYPE_ID, default_roles, IMPORT_KB_PATH_IN_OS, EXPORT_KB_PATH_IN_MINIO, IMPORT_KB_PATH_IN_MINIO
from data_chain.stores.database.database import TeamEntity, KnowledgeBaseEntity, DocumentTypeEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.apps.base.convertor import Convertor
from data_chain.manager.team_manager import TeamManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.testing_manager import TestingManager
from data_chain.manager.dataset_manager import DataSetManager
from data_chain.manager.role_manager import RoleManager
from data_chain.manager.task_manager import TaskManager
from data_chain.apps.service.document_service import DocumentService
from data_chain.apps.service.dataset_service import DataSetService
from data_chain.apps.service.acc_testing_service import TestingService


class KnowledgeBaseService:
    """知识库服务"""
    @staticmethod
    async def validate_user_action_to_knowledge_base(
            user_sub: str, kb_id: uuid.UUID, action: str) -> bool:
        """验证用户在知识库中的操作权限"""
        try:
            kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
            if kb_entity is None:
                logging.exception("[KnowledgeBaseService] 知识库不存在")
                raise Exception("Knowledge base not exist")
            action_entity = await RoleManager.get_action_by_team_id_user_sub_and_action(
                user_sub, kb_entity.team_id, action)
            if action_entity is None:
                return False
            return True
        except Exception as e:
            err = "验证用户在知识库中的操作权限失败"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise e

    @staticmethod
    async def list_kb_by_user_sub(user_sub: str, kb_id: uuid.UUID, kb_name: str = None) -> ListAllKnowledgeBaseMsg:
        """列出知识库"""
        try:
            # 获取用户所在团队
            team_entities = await TeamManager.list_all_team_user_created_or_joined(user_sub)
            team_entities.sort(key=lambda x: x.created_time, reverse=True)
            team_ids = [team_entity.id for team_entity in team_entities]
            # 获取知识库
            knowledge_base_entities = await KnowledgeBaseManager.list_knowledge_base_by_team_ids(team_ids, kb_id, kb_name)
            team_knowledge_bases_dict = {}
            for knowledge_base_entity in knowledge_base_entities:
                team_id = knowledge_base_entity.team_id
                if team_id not in team_knowledge_bases_dict:
                    team_knowledge_bases_dict[team_id] = []
                team_knowledge_bases_dict[team_id].append(knowledge_base_entity)
            team_knowledge_bases = []
            for team_entity in team_entities:
                knowledge_base_entities = team_knowledge_bases_dict.get(team_entity.id, [])
                team_knowledge_base = TeamKnowledgebase(
                    teamId=team_entity.id,
                    teamName=team_entity.name,
                    kbList=[]
                )
                for knowledge_base_entity in knowledge_base_entities:
                    doc_type_entities = await KnowledgeBaseManager.list_doc_types_by_kb_id(knowledge_base_entity.id)
                    doc_types = []
                    for doc_type_entity in doc_type_entities:
                        doc_types.append(
                            (await Convertor.convert_document_type_entity_to_document_type_response(doc_type_entity))
                        )
                    knowledge_base = await Convertor.convert_knowledge_base_entity_to_knowledge_base(knowledge_base_entity)
                    knowledge_base.doc_types = doc_types
                    team_knowledge_base.kb_list.append(
                        knowledge_base
                    )
                team_knowledge_bases.append(team_knowledge_base)
            return ListAllKnowledgeBaseMsg(teamKnowledgebases=team_knowledge_bases)
        except Exception as e:
            err = "列出知识库失败"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise e

    @staticmethod
    async def list_kb_by_team_id(req: ListKnowledgeBaseRequest) -> ListKnowledgeBaseMsg:
        """列出知识库"""
        try:
            # 获取知识库
            total, knowledge_base_entities = await KnowledgeBaseManager.list_knowledge_base(req)
            knowledge_bases = []
            for knowledge_base_entity in knowledge_base_entities:
                doc_type_entities = await KnowledgeBaseManager.list_doc_types_by_kb_id(knowledge_base_entity.id)
                doc_types = []
                for doc_type_entity in doc_type_entities:
                    doc_types.append(
                        (await Convertor.convert_document_type_entity_to_document_type_response(doc_type_entity))
                    )
                knowledge_base = await Convertor.convert_knowledge_base_entity_to_knowledge_base(knowledge_base_entity)
                knowledge_base.doc_types = doc_types
                knowledge_bases.append(
                    knowledge_base
                )
            return ListKnowledgeBaseMsg(total=total, kbList=knowledge_bases)
        except Exception as e:
            err = "列出知识库失败"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise e

    @staticmethod
    async def list_doc_types_by_kb_id(kb_id: uuid.UUID) -> list[DocumentTypeResponse]:
        """列出知识库文档类型"""
        try:
            # 获取文档类型
            document_type_entities = await KnowledgeBaseManager.list_doc_types_by_kb_id(kb_id)
            document_types = []
            for document_type_entity in document_type_entities:
                document_types.append(
                    (await Convertor.convert_document_type_entity_to_document_type_response(document_type_entity))
                )
            return document_types
        except Exception as e:
            err = "列出知识库文档类型失败"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise e

    @staticmethod
    async def generate_knowledge_base_download_link(task_id: uuid.UUID) -> str:
        """生成知识库下载链接"""
        try:
            # 获取知识库
            download_link = await MinIO.generate_download_link(
                EXPORT_KB_PATH_IN_MINIO,
                str(task_id),
            )
            return download_link
        except Exception as e:
            err = "生成知识库下载链接失败"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise e

    @staticmethod
    async def create_kb(
            user_sub: str, team_id: uuid.UUID, req: CreateKnowledgeBaseRequest) -> uuid.UUID:
        """创建知识库"""
        try:
            knowledge_base_entity = await Convertor.convert_create_knowledge_base_request_to_knowledge_base_entity(
                user_sub, team_id, req)
            knowledge_base_entity = await KnowledgeBaseManager.add_knowledge_base(knowledge_base_entity)
            if knowledge_base_entity is None:
                err = "创建知识库失败"
                logging.exception("[KnowledgeBaseService] %s", err)
                raise e
            doc_types = req.doc_types
            doc_type_entities = []
            for doc_type in doc_types:
                doc_type_entity = await Convertor.convert_kb_id_and_requeset_document_type_to_document_type_entity(knowledge_base_entity.id, doc_type)
                doc_type_entities.append(doc_type_entity)
            await DocumentTypeManager.add_document_types(doc_type_entities)
            return knowledge_base_entity.id
        except Exception as e:
            err = "创建知识库失败"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise e

    @staticmethod
    async def get_kb_entity_from_yaml(user_sub: str, team_id: uuid.UUID, yaml_path: str) -> KnowledgeBaseEntity:
        """获取知识库配置并转换为数据库实体"""
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                kb_config = yaml.load(f, Loader=yaml.SafeLoader)
            kb_entity = KnowledgeBaseEntity(
                team_id=team_id,
                author_id=user_sub,
                author_name=user_sub,
                name=kb_config.get("name", ""),
                tokenizer=kb_config.get("tokenizer", Tokenizer.ZH.value),
                description=kb_config.get("description", ""),
                embedding_model=kb_config.get("embedding_model", ""),
                doc_cnt=0,
                doc_size=0,
                upload_count_limit=kb_config.get("upload_count_limit", 128),
                upload_size_limit=kb_config.get("upload_size_limit", 512),
                default_parse_method=kb_config.get("default_parse_method", ParseMethod.GENERAL.value),
                default_chunk_size=kb_config.get("default_chunk_size", 1024),
                status=kb_config.get("status", KnowledgeBaseStatus.IDLE.value),
            )
            return kb_entity
        except Exception as e:
            err = "获取知识库配置失败"
            logging.exception("[KnowledgeBaseService] %s", err)

    @staticmethod
    async def import_kbs(user_sub: str, team_id: uuid.UUID, kb_packages: list[UploadFile] = File(...)) -> str:
        """导入知识库"""
        if len(kb_packages) > 5:
            err = "导入知识库失败，知识库数量超过5个"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise Exception(err)
        kb_packages_sz = 0
        for kb_package in kb_packages:
            kb_packages_sz += kb_package.size
        if kb_packages_sz > 5 * 1024 * 1024 * 1024:
            err = "导入知识库失败，知识库大小超过5G"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise Exception(err)
        kb_import_task_ids = []
        for kb_package in kb_packages:
            tmp_path = os.path.join(IMPORT_KB_PATH_IN_OS, str(uuid.uuid4()))
            zip_file_name = kb_package.filename
            zip_file_path = os.path.join(tmp_path, zip_file_name)
            if os.path.exists(tmp_path):
                shutil.rmtree(tmp_path)
            os.makedirs(tmp_path)
            try:
                async with aiofiles.open(zip_file_path, "wb") as f:
                    content = await kb_package.read()
                    await f.write(content)
            except Exception as e:
                err = "导入知识库失败"
                logging.exception("[KnowledgeBaseService] %s", err)
                continue
            if not ZipHandler.check_zip_file(zip_file_path):
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path)
                err = "导入知识库失败，包含文件数量过多或者解压缩之后体积过大"
                logging.exception("[KnowledgeBaseService] %s", err)
                continue
            try:
                await ZipHandler.unzip_file(zip_file_path, tmp_path, ['kb_config.yaml'])
            except Exception as e:
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path)
                err = "导入知识库失败，解压缩失败"
                logging.exception("[KnowledgeBaseService] %s", err)
                continue
            kb_entity = await KnowledgeBaseService.get_kb_entity_from_yaml(
                user_sub, team_id, os.path.join(tmp_path, 'kb_config.yaml'))
            kb_entity = await KnowledgeBaseManager.add_knowledge_base(kb_entity)
            if kb_entity is None:
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path)
                err = "导入知识库失败，获取知识库配置失败"
                logging.exception("[KnowledgeBaseService] %s", err)
                continue
            await MinIO.put_object(IMPORT_KB_PATH_IN_MINIO, str(kb_entity.id), zip_file_path)
            try:
                task_id = await TaskQueueService.init_task(TaskType.KB_IMPORT.value, kb_entity.id)
                if task_id:
                    kb_import_task_ids.append(task_id)
            except Exception as e:
                err = "导入知识库失败"
                logging.exception("[KnowledgeBaseService] %s", err)
            if os.path.exists(tmp_path):
                shutil.rmtree(tmp_path)
        return kb_import_task_ids

    @staticmethod
    async def export_kb_by_kb_ids(kb_ids: list[uuid.UUID]) -> str:
        """导出知识库"""
        kb_export_task_ids = []
        for kb_id in kb_ids:
            try:
                task_id = await TaskQueueService.init_task(TaskType.KB_EXPORT.value, kb_id)
                if task_id:
                    kb_export_task_ids.append(task_id)
            except Exception as e:
                err = "导出知识库失败"
                logging.exception("[KnowledgeBaseService] %s", err)
        return kb_export_task_ids

    @staticmethod
    async def update_doc_types(kb_id: uuid.UUID, doc_types: list[DocumentTypeRequest]) -> None:
        new_doc_type_map = {doc_type.doc_type_id: doc_type.doc_type_name for doc_type in doc_types}
        new_doc_type_ids = {doc_type.doc_type_id for doc_type in doc_types}
        old_doc_type_entities = await KnowledgeBaseManager.list_doc_types_by_kb_id(kb_id)
        old_doc_type_ids = {doc_type_entity.id for doc_type_entity in old_doc_type_entities}
        delete_doc_type_ids = old_doc_type_ids - new_doc_type_ids
        add_doc_type_ids = new_doc_type_ids - old_doc_type_ids
        update_doc_type_ids = old_doc_type_ids & new_doc_type_ids
        await DocumentManager.update_doc_type_by_kb_id(kb_id, delete_doc_type_ids, DEFAULt_DOC_TYPE_ID)
        doc_type_entities = []
        for doc_type_id in add_doc_type_ids:
            doc_type_entity = DocumentTypeEntity(
                id=doc_type_id,
                kb_id=kb_id,
                name=new_doc_type_map[doc_type_id],
            )
            doc_type_entities.append(doc_type_entity)
        await DocumentTypeManager.add_document_types(doc_type_entities)
        for update_doc_type_id in update_doc_type_ids:
            try:
                await DocumentTypeManager.update_doc_type_by_doc_type_id(update_doc_type_id, new_doc_type_map[update_doc_type_id])
            except Exception as e:
                err = "更新文档类型失败"
                logging.exception("[KnowledgeBaseService] %s", err)
                continue

    @staticmethod
    async def update_kb_by_kb_id(kb_id: uuid.UUID, req: UpdateKnowledgeBaseRequest) -> uuid.UUID:
        """更新知识库"""
        try:
            knowledge_base_dict = await Convertor.convert_update_knowledge_base_request_to_dict(req)
            knowledge_base_entity = await KnowledgeBaseManager.update_knowledge_base_by_kb_id(kb_id, knowledge_base_dict)
            if knowledge_base_entity is None:
                err = "更新知识库失败"
                logging.exception("[KnowledgeBaseService] %s", err)
                raise e
            await KnowledgeBaseService.update_doc_types(kb_id, req.doc_types)
            return knowledge_base_entity.id
        except Exception as e:
            err = "更新知识库失败"
            logging.exception("[KnowledgeBaseService] %s", err)
            raise e

    @staticmethod
    async def delete_kb_by_kb_ids(kb_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """删除知识库"""
        kb_ids_deleted = []
        for kb_id in kb_ids:
            try:
                document_entities = await DocumentManager.list_all_document_by_kb_id(kb_id)
                dataset_entities = await DataSetService.list_dataset_by_kb_id(kb_id)
                testing_entities = await TestingService.list_testing_by_kb_id(kb_id)
                doc_ids = [doc_entity.id for doc_entity in document_entities]
                await DocumentService.delete_docs_by_ids(doc_ids)
                dataset_ids = [dataset_entity.id for dataset_entity in dataset_entities]
                await DataSetService.delete_data_by_data_ids(dataset_ids)
                testing_ids = [testing_entity.id for testing_entity in testing_entities]
                await TestingService.delete_testing_by_testing_ids(testing_ids)
                task_entity = await TaskManager.get_current_task_by_op_id(kb_id)
                if task_entity is not None:
                    await TaskQueueService.stop_task(task_entity.id)
                await KnowledgeBaseManager.update_knowledge_base_by_kb_id(
                    kb_id, {"status": KnowledgeBaseStatus.DELETED.value})
                kb_ids_deleted.append(kb_id)
            except Exception as e:
                err = "删除知识库失败"
                logging.exception("[KnowledgeBaseService] %s", err)
                continue
        return kb_ids_deleted
