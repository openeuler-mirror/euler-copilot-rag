# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import aiofiles
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
import uuid
import traceback
import os
from data_chain.entities.request_data import (
    ListChunkRequest,
    UpdateChunkRequest,
    SearchChunkRequest,
)
from data_chain.entities.response_data import (
    Task,
    Document,
    Chunk,
    DocChunk,
    ListChunkMsg,
    SearchChunkMsg
)
from data_chain.apps.base.convertor import Convertor
from data_chain.apps.service.task_queue_service import TaskQueueService
from data_chain.apps.service.knwoledge_base_service import KnowledgeBaseService
from data_chain.apps.service.document_service import DocumentService
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.manager.role_manager import RoleManager
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.task_report_manager import TaskReportManager
from data_chain.stores.database.database import DocumentEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.entities.enum import ParseMethod, DataSetStatus, DocumentStatus, TaskType
from data_chain.entities.common import DOC_PATH_IN_OS, DOC_PATH_IN_MINIO, DEFAULT_KNOWLEDGE_BASE_ID, DEFAULT_DOC_TYPE_ID
from data_chain.logger.logger import logger as logging
from data_chain.rag.base_searcher import BaseSearcher
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.embedding.embedding import Embedding


class ChunkService:
    """Chunk Service"""
    async def validate_user_action_to_chunk(user_sub: str, chunk_id: uuid.UUID, action: str) -> bool:
        """验证用户对分片的操作权限"""
        try:
            chunk_entity = await ChunkManager.get_chunk_by_chunk_id(chunk_id)
            if chunk_entity is None:
                err = f"分片不存在，分片ID: {chunk_id}"
                logging.error("[ChunkService] %s", err)
                return False
            action_entity = await RoleManager.get_action_by_team_id_user_sub_and_action(
                user_sub, chunk_entity.team_id, action)
            if action_entity is None:
                return False
            return True
        except Exception as e:
            err = "验证用户对分片的操作权限失败"
            logging.exception("[ChunkService] %s", err)
            raise e

    async def list_chunks_by_document_id(req: ListChunkRequest) -> ListChunkMsg:
        """根据文档ID列出分片"""
        try:
            doc_entity = await DocumentManager.get_document_by_doc_id(req.doc_id)
            if doc_entity.status != DocumentStatus.IDLE.value:
                return ListChunkMsg(total=0, chunks=[])
            total, chunk_entities = await ChunkManager.list_chunk(req)
            chunks = []
            for chunk_entity in chunk_entities:
                chunk = await Convertor.convert_chunk_entity_to_chunk(chunk_entity)
                chunks.append(chunk)
            return ListChunkMsg(total=total, chunks=chunks)
        except Exception as e:
            err = "根据文档ID列出分片失败"
            logging.exception("[ChunkService] %s", err)
            raise e

    async def search_chunks(user_sub: str, action: str, req: SearchChunkRequest) -> SearchChunkMsg:
        """根据查询条件搜索分片"""
        logging.error("[ChunkService] 搜索分片，查询条件: %s", req)
        chunk_entities = []
        for kb_id in req.kb_ids:
            if kb_id != DEFAULT_KNOWLEDGE_BASE_ID:
                try:
                    if not (await KnowledgeBaseService.validate_user_action_to_knowledge_base(
                            user_sub, kb_id, action)):
                        err = f"用户没有权限访问知识库中的块，知识库ID: {kb_id}"
                        logging.error("[ChunkService] %s", err)
                        continue
                except Exception as e:
                    err = f"验证用户对知识库的操作权限失败，error: {e}"
                    logging.exception(err)
                    continue
            try:
                chunk_entities += await BaseSearcher.search(req.search_method.value, kb_id, req.query, 2*req.top_k, req.doc_ids, req.banned_ids)
            except Exception as e:
                err = f"[ChunkService] 搜索分片失败，error: {e}"
                logging.exception(err)
                return SearchChunkMsg(docChunks=[])
        if len(chunk_entities) == 0:
            return SearchChunkMsg(docChunks=[])
        if req.is_rerank:
            chunk_entities = await BaseSearcher.rerank(chunk_entities, req.query)
        chunk_entities = chunk_entities[:req.top_k]
        chunk_ids = [chunk_entity.id for chunk_entity in chunk_entities]
        logging.error("[ChunkService] 搜索分片，查询结果数量: %s", len(chunk_entities))
        if req.is_related_surrounding:
            # 关联上下文
            tokens_limit = req.tokens_limit
            tokens_limit_every_chunk = tokens_limit // len(chunk_entities) if len(chunk_entities) > 0 else tokens_limit
            leave_tokens = 0
            related_chunk_entities = []
            for chunk_entity in chunk_entities:
                leave_tokens = tokens_limit_every_chunk+leave_tokens
                try:
                    sub_related_chunk_entities = await BaseSearcher.related_surround_chunk(chunk_entity, leave_tokens-chunk_entity.tokens, chunk_ids)
                except Exception as e:
                    leave_tokens += tokens_limit_every_chunk
                    err = f"[ChunkService] 关联上下文失败，error: {e}"
                    logging.exception(err)
                    continue
                tokens_sum = 0
                for related_chunk_entity in sub_related_chunk_entities:
                    tokens_sum += related_chunk_entity.tokens
                leave_tokens -= tokens_sum
                if leave_tokens < 0:
                    leave_tokens = 0
                chunk_ids += [chunk_entity.id for chunk_entity in sub_related_chunk_entities]
                related_chunk_entities += sub_related_chunk_entities
            chunk_entities += related_chunk_entities
        logging.error(len(chunk_entities))
        search_chunk_msg = SearchChunkMsg(docChunks=[])
        if req.is_classify_by_doc:
            doc_chunks = await BaseSearcher.classify_by_doc_id(chunk_entities)
            for doc_chunk in doc_chunks:
                for chunk in doc_chunk.chunks:
                    if req.is_compress:
                        chunk.text = TokenTool.compress_tokens(chunk.text)
                search_chunk_msg.doc_chunks.append(doc_chunk)
        else:
            for chunk_entity in chunk_entities:
                chunk = await Convertor.convert_chunk_entity_to_chunk(chunk_entity)
                if req.is_compress:
                    chunk.text = TokenTool.compress_tokens(chunk.text)
                dc = DocChunk(docId=chunk_entity.doc_id, docName=chunk_entity.doc_name, chunks=[chunk])
                search_chunk_msg.doc_chunks.append(dc)
        for doc_chunk in search_chunk_msg.doc_chunks:
            doc_chunk.doc_link = await DocumentService.generate_doc_download_url(doc_chunk.doc_id)
        return search_chunk_msg

    async def update_chunk_by_id(chunk_id: uuid.UUID, req: UpdateChunkRequest) -> uuid.UUID:
        try:
            chunk_dict = await Convertor.convert_update_chunk_request_to_dict(req)
            if req.text:
                vector = await Embedding.vectorize_embedding(req.text)
                chunk_dict["text_vector"] = vector
            chunk_entity = await ChunkManager.update_chunk_by_chunk_id(chunk_id, chunk_dict)
            return chunk_entity.id
        except Exception as e:
            err = "更新分片失败"
            logging.exception("[ChunkService] %s", err)
            raise Exception(err)

    async def update_chunks_enabled_by_id(chunk_ids: list[uuid.UUID], enabled: bool) -> list[uuid.UUID]:
        try:
            chunk_dict = {"enabled": enabled}
            chunk_entities = await ChunkManager.update_chunk_by_chunk_ids(chunk_ids, chunk_dict)
            chunk_ids = [chunk_entity.id for chunk_entity in chunk_entities]
            return chunk_ids
        except Exception as e:
            err = "更新分片失败"
            logging.exception("[ChunkService] %s", err)
            raise Exception(err)
