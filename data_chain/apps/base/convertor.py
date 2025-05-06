# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from typing import Any, Dict
import uuid
from data_chain.entities.request_data import (
    CreateTeamRequest,
    CreateKnowledgeBaseRequest
)
from data_chain.entities.response_data import (
    User,
    Team,
    Knowledgebase,
    DocumentType
)

from data_chain.entities.enum import UserStatus, TeamStatus
from data_chain.entities.common import default_roles
from data_chain.stores.database.database import (
    UserEntity,
    TeamEntity,
    KnowledgeBaseEntity,
    DocumentTypeEntity,
    TeamUserEntity,
    UserRoleEntity,
    RoleEntity,
    RoleActionEntity
)
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
    async def convert_team_entity_to_team(team_entity: TeamEntity) -> Team:
        """将团队实体转换为团队"""
        try:
            team = Team(
                teamId=team_entity.id,
                teamName=team_entity.name,
                description=team_entity.description,
                authorName=team_entity.author_name,
                memberCount=team_entity.member_cnt,
                isPublic=team_entity.is_public
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
                defaultParserMethod=knowledge_base_entity.default_parse_method,
                defaultChunkSize=knowledge_base_entity.default_chunk_size,
                createdTime=knowledge_base_entity.created_time.strftime('%Y-%m-%d %H:%M'),
            )
            return knowledge_base
        except Exception as e:
            err = "知识库实体转换为知识库失败"
            logging.exception("[Convertor] %s", err)
            raise e

    @staticmethod
    async def convert_document_type_entity_to_document_type(
            document_type_entity: DocumentTypeEntity) -> DocumentType:
        """将文档类型实体转换为文档类型"""
        try:
            document_type = DocumentType(
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
