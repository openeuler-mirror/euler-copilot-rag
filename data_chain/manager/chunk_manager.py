# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, update, func, text, or_, and_
from typing import List, Tuple, Dict, Optional
import uuid
from data_chain.entities.enum import DocumentStatus, ChunkStatus, Tokenizer
from data_chain.entities.request_data import ListChunkRequest
from data_chain.config.config import config
from data_chain.stores.database.database import DocumentEntity, ChunkEntity, DataBase
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.logger.logger import logger as logging


class ChunkManager():
    @staticmethod
    async def add_chunk(chunk: ChunkEntity) -> ChunkEntity:
        """添加文档"""
        try:
            async with await DataBase.get_session() as session:
                session.add(chunk)
                await session.commit()
                return chunk
        except Exception as e:
            err = "添加文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)

    @staticmethod
    async def add_chunks(chunks: List[ChunkEntity]) -> List[ChunkEntity]:
        """批量添加文档"""
        try:
            async with await DataBase.get_session() as session:
                session.add_all(chunks)
                await session.commit()
                return chunks
        except Exception as e:
            err = "批量添加文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)

    @staticmethod
    async def get_chunk_by_chunk_id(chunk_id: uuid.UUID) -> Optional[ChunkEntity]:
        """根据文档ID查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(ChunkEntity)
                    .where(ChunkEntity.id == chunk_id)
                )
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            err = "根据文档ID查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    @staticmethod
    async def get_chunk_cnt_by_doc_ids(doc_ids: List[uuid.UUID]) -> int:
        """根据文档ID查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(func.count())
                    .where(ChunkEntity.doc_id.in_(doc_ids))
                    .where(ChunkEntity.status != ChunkStatus.DELETED.value)
                )
                result = await session.execute(stmt)
                return result.scalar()
        except Exception as e:
            err = "根据文档ID查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    async def get_chunk_cnt_by_kb_id(kb_id) -> int:
        """根据文档ID查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(func.count())
                    .where(ChunkEntity.kb_id == kb_id)
                    .where(ChunkEntity.status != ChunkStatus.DELETED.value)
                )
                result = await session.execute(stmt)
                return result.scalar()
        except Exception as e:
            err = "根据文档ID查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    @staticmethod
    async def get_chunk_tokens_by_doc_ids(doc_ids: List[uuid.UUID]) -> int:
        """根据文档ID查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(func.sum(ChunkEntity.tokens))
                    .where(ChunkEntity.doc_id.in_(doc_ids))
                    .where(ChunkEntity.status != ChunkStatus.DELETED.value)
                )
                result = await session.execute(stmt)
                return result.scalar()
        except Exception as e:
            err = "根据文档ID查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    @staticmethod
    async def get_chunk_tokens_by_kb_id(kb_id) -> int:
        """根据文档ID查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(func.sum(ChunkEntity.tokens))
                    .where(ChunkEntity.kb_id == kb_id)
                    .where(ChunkEntity.status != ChunkStatus.DELETED.value)
                )
                result = await session.execute(stmt)
                return result.scalar()
        except Exception as e:
            err = "根据文档ID查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    async def list_chunk(
            req: ListChunkRequest,
    ) -> Tuple[int, List[ChunkEntity]]:
        """根据文档ID查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(ChunkEntity)
                    .where(ChunkEntity.status != ChunkStatus.DELETED.value)
                )
                if req.doc_id:
                    stmt = stmt.where(ChunkEntity.doc_id == req.doc_id)
                if req.text:
                    stmt = stmt.where(ChunkEntity.text.ilike(f"%{req.text}%"))
                if req.types:
                    stmt = stmt.where(ChunkEntity.type.in_([t.value for t in req.types]))
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.offset((req.page - 1) * req.page_size).limit(req.page_size)
                stmt = stmt.order_by(ChunkEntity.global_offset)
                result = await session.execute(stmt)
                chunk_entities = result.scalars().all()
                return total, chunk_entities
        except Exception as e:
            err = "根据文档ID查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    @staticmethod
    async def list_all_chunk_by_doc_id(doc_id: uuid.UUID) -> List[ChunkEntity]:
        """根据文档ID查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(ChunkEntity)
                    .where(and_(ChunkEntity.doc_id == doc_id,
                                ChunkEntity.status != ChunkStatus.DELETED.value))
                    .order_by(ChunkEntity.global_offset)
                )
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "根据文档ID查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    @staticmethod
    async def get_top_k_chunk_by_kb_id_vector(
            kb_id: uuid.UUID, vector: List[float],
            top_k: int, doc_ids: list[uuid.UUID] = None, banned_ids: list[uuid.UUID] = [],
            chunk_to_type: str = None, pre_ids: list[uuid.UUID] = None) -> List[ChunkEntity]:
        """根据知识库ID和向量查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(ChunkEntity)
                    .join(DocumentEntity,
                          DocumentEntity.id == ChunkEntity.doc_id
                          )
                    .where(DocumentEntity.enabled == True)
                    .where(DocumentEntity.status != DocumentStatus.DELETED.value)
                    .where(ChunkEntity.kb_id == kb_id)
                    .where(ChunkEntity.status != ChunkStatus.DELETED.value)
                    .where(ChunkEntity.id.notin_(banned_ids))
                    .order_by(ChunkEntity.text_vector.cosine_distance(vector).desc())
                    .limit(top_k)
                )
                if doc_ids:
                    stmt = stmt.where(DocumentEntity.id.in_(doc_ids))
                if chunk_to_type:
                    stmt = stmt.where(ChunkEntity.parse_topology_type == chunk_to_type)
                if pre_ids:
                    stmt = stmt.where(ChunkEntity.pre_id_in_parse_topology.in_(pre_ids))
                result = await session.execute(stmt)
                chunk_entities = result.scalars().all()
                return chunk_entities
        except Exception as e:
            err = "根据知识库ID和向量查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    @staticmethod
    async def get_top_k_chunk_by_kb_id_keyword(
            kb_id: uuid.UUID, query: str, top_k: int, doc_ids: list[uuid.UUID] = None, banned_ids: list[uuid.UUID] = [],
            chunk_to_type: str = None, pre_ids: list[uuid.UUID] = None) -> List[ChunkEntity]:
        """根据知识库ID和关键词查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
                tokenizer = ''
                if kb_entity.tokenizer == Tokenizer.ZH.value:
                    if 'opengauss' in config['DATABASE_URL']:
                        tokenizer = 'chparser'
                    else:
                        tokenizer = 'zhparser'
                elif kb_entity.tokenizer == Tokenizer.EN.value:
                    tokenizer = 'english'
                stmt = (
                    select(ChunkEntity)
                    .join(DocumentEntity,
                          DocumentEntity.id == ChunkEntity.doc_id
                          )
                    .where(DocumentEntity.enabled == True)
                    .where(DocumentEntity.status != DocumentStatus.DELETED.value)
                    .where(ChunkEntity.kb_id == kb_id)
                    .where(ChunkEntity.status != ChunkStatus.DELETED.value)
                    .where(ChunkEntity.id.notin_(banned_ids))
                    .order_by(
                        func.ts_rank_cd(
                            func.to_tsvector(tokenizer, ChunkEntity.text),
                            func.plainto_tsquery(tokenizer, query)
                        ).desc()
                    )
                    .limit(top_k)
                )
                if doc_ids:
                    stmt = stmt.where(DocumentEntity.id.in_(doc_ids))
                if chunk_to_type:
                    stmt = stmt.where(ChunkEntity.parse_topology_type == chunk_to_type)
                if pre_ids:
                    stmt = stmt.where(ChunkEntity.pre_id_in_parse_topology.in_(pre_ids))
                result = await session.execute(stmt)
                chunk_entities = result.scalars().all()
                return chunk_entities
        except Exception as e:
            err = "根据知识库ID和关键词查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    @staticmethod
    async def fetch_surrounding_chunk_by_doc_id_and_global_offset(
            doc_id: uuid.UUID, global_offset: int,
            top_k: int = 50, banned_ids: list[uuid.UUID] = []) -> List[ChunkEntity]:
        """根据文档ID和全局偏移量查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(ChunkEntity)
                    .where(and_(ChunkEntity.doc_id == doc_id,
                                ChunkEntity.status != ChunkStatus.DELETED.value))
                    .where(and_(ChunkEntity.global_offset >= global_offset - top_k,
                                ChunkEntity.global_offset <= global_offset + top_k))
                    .where(ChunkEntity.id.notin_(banned_ids))
                    .order_by(ChunkEntity.global_offset)
                )
                result = await session.execute(stmt)
                chunk_entities = result.scalars().all()
                return chunk_entities
        except Exception as e:
            err = "根据文档ID和全局偏移量查询文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
            raise e

    @staticmethod
    async def update_chunk_by_doc_id(doc_id: uuid.UUID, chunk_dict: Dict[str, str]) -> bool:
        """根据文档ID更新文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(ChunkEntity)
                    .where(ChunkEntity.doc_id == doc_id)
                    .values(**chunk_dict)
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            err = "根据文档ID更新文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)

    @staticmethod
    async def update_chunk_by_chunk_id(chunk_id: uuid.UUID, chunk_dict: Dict[str, str]) -> ChunkEntity:
        """根据文档ID更新文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(ChunkEntity)
                    .where(ChunkEntity.id == chunk_id)
                    .values(**chunk_dict)
                )
                await session.execute(stmt)
                await session.commit()
                stmt = (
                    select(ChunkEntity)
                    .where(ChunkEntity.id == chunk_id)
                )
                result = await session.execute(stmt)
                chunk_entity = result.scalars().first()
                return chunk_entity
        except Exception as e:
            err = "根据文档ID更新文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)

    @staticmethod
    async def update_chunk_by_chunk_ids(chunk_ids: List[uuid.UUID], chunk_dict: Dict[str, str]) -> list[ChunkEntity]:
        """根据文档ID更新文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(ChunkEntity)
                    .where(ChunkEntity.id.in_(chunk_ids))
                    .values(**chunk_dict)
                )
                await session.execute(stmt)
                await session.commit()
                stmt = (
                    select(ChunkEntity)
                    .where(ChunkEntity.id.in_(chunk_ids))
                )
                result = await session.execute(stmt)
                chunk_entities = result.scalars().all()
                return chunk_entities
        except Exception as e:
            err = "根据文档ID更新文档解析结果失败"
            logging.exception("[ChunkManager] %s", err)
