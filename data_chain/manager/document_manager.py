# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, delete, update, func, between, asc, desc, and_, Float, literal_column, text
from datetime import datetime, timezone
import uuid
from typing import Dict, List, Tuple

from data_chain.config.config import config
from data_chain.entities.enum import TaskStatus, OrderType
from data_chain.stores.database.database import DataBase, KnowledgeBaseEntity, DocumentTypeEntity, DocumentEntity, TaskEntity
from data_chain.entities.enum import KnowledgeBaseStatus, DocumentStatus
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.entities.enum import Tokenizer, ChunkStatus
from data_chain.entities.request_data import ListDocumentRequest
from data_chain.logger.logger import logger as logging


class DocumentManager():
    """文档管理类"""

    @staticmethod
    async def add_document(document_entity: DocumentEntity) -> DocumentEntity:
        """添加文档"""
        try:
            async with await DataBase.get_session() as session:
                session.add(document_entity)
                await session.commit()
                return document_entity
        except Exception as e:
            err = "添加文档失败"
            logging.exception("[DocumentManager] %s", err)

    @staticmethod
    async def add_documents(document_entities: List[DocumentEntity]) -> List[DocumentEntity]:
        """批量添加文档"""
        try:
            async with await DataBase.get_session() as session:
                session.add_all(document_entities)
                await session.commit()
                for document_entity in document_entities:
                    await session.refresh(document_entity)
                return document_entities
        except Exception as e:
            err = "批量添加文档失败"
            logging.exception("[DocumentManager] %s", err)

    @staticmethod
    async def get_top_k_document_by_kb_id_vector(
            kb_id: uuid.UUID, vector: list[float],
            top_k: int = 5, doc_ids: list[uuid.UUID] = None, banned_ids: list[uuid.UUID] = []) -> List[DocumentEntity]:
        """根据知识库ID和向量获取前K个文档"""
        try:
            async with await DataBase.get_session() as session:
                similarity_score = DocumentEntity.abstract_vector.cosine_distance(vector).label("similarity_score")
                stmt = (
                    select(DocumentEntity, similarity_score)
                    .where(similarity_score > 0)
                    .where(DocumentEntity.kb_id == kb_id)
                    .where(DocumentEntity.id.notin_(banned_ids))
                    .where(DocumentEntity.status != DocumentStatus.DELETED.value)
                    .where(DocumentEntity.enabled == True)
                )
                if doc_ids:
                    stmt = stmt.where(DocumentEntity.id.in_(doc_ids))
                stmt = stmt.order_by(
                    similarity_score.desc()
                )

                result = await session.execute(stmt)

                document_entities = result.scalars().all()
                return document_entities
        except Exception as e:
            err = "获取前K个文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def get_top_k_document_by_kb_id_keyword(
            kb_id: uuid.UUID, query: str, top_k: int = 5, doc_ids: list[uuid.UUID] = None, banned_ids: list[uuid.UUID] = []) -> List[DocumentEntity]:
        """根据知识库ID和关键词获取前K个文档"""
        try:
            async with await DataBase.get_session() as session:
                kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
                tokenizer = ''
                if kb_entity.tokenizer == Tokenizer.ZH.value:
                    if config['DATABASE_TYPE'].lower() == 'opengauss':
                        tokenizer = 'chparser'
                    else:
                        tokenizer = 'zhparser'
                elif kb_entity.tokenizer == Tokenizer.EN.value:
                    tokenizer = 'english'
                similarity_score = func.ts_rank_cd(
                    func.to_tsvector(tokenizer, DocumentEntity.abstract),
                    func.plainto_tsquery(tokenizer, query)
                ).label("similarity_score")
                stmt = (
                    select(DocumentEntity, similarity_score)
                    .where(DocumentEntity.kb_id == kb_id)
                    .where(DocumentEntity.id.notin_(banned_ids))
                    .where(DocumentEntity.status != DocumentStatus.DELETED.value)
                    .where(DocumentEntity.enabled == True)
                )
                if doc_ids:
                    stmt = stmt.where(DocumentEntity.id.in_(doc_ids))

                stmt = stmt.order_by(
                    similarity_score.desc()
                )
                stmt = stmt.limit(top_k)
                result = await session.execute(stmt)
                document_entities = result.scalars().all()
                return document_entities
        except Exception as e:
            err = "获取前K个文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    async def get_top_k_document_by_kb_id_dynamic_weighted_keyword(
            kb_id: uuid.UUID, keywords: List[str], weights: List[float],
            top_k: int, doc_ids: list[uuid.UUID] = None, banned_ids: list[uuid.UUID] = []) -> List[DocumentEntity]:
        """根据知识库ID和关键词和关键词权重查询文档解析结果"""
        try:
            async with await DataBase.get_session() as session:
                kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
                if kb_entity.tokenizer == Tokenizer.ZH.value:
                    if config['DATABASE_TYPE'].lower() == 'opengauss':
                        tokenizer = 'chparser'
                    else:
                        tokenizer = 'zhparser'
                elif kb_entity.tokenizer == Tokenizer.EN.value:
                    tokenizer = 'english'
                else:
                    if config['DATABASE_TYPE'].lower() == 'opengauss':
                        tokenizer = 'chparser'
                    else:
                        tokenizer = 'zhparser'

                # 构建VALUES子句的参数
                params = {}
                values_clause = []

                for i, (term, weight) in enumerate(zip(keywords, weights)):
                    # 使用单独的参数名，避免与类型转换冲突
                    params[f"term_{i}"] = term
                    params[f"weight_{i}"] = weight
                    # 在VALUES子句中使用类型转换函数
                    values_clause.append(f"(CAST(:term_{i} AS TEXT), CAST(:weight_{i} AS FLOAT8))")

                # 构建VALUES子句
                values_text = f"(VALUES {', '.join(values_clause)}) AS t(term, weight)"

                # 创建weighted_terms CTE
                weighted_terms = (
                    select(
                        literal_column("t.term").label("term"),
                        literal_column("t.weight").cast(Float).label("weight")
                    )
                    .select_from(text(values_text))
                    .cte("weighted_terms")
                )

                # 计算相似度得分
                similarity_score = func.sum(
                    func.ts_rank_cd(
                        func.to_tsvector(tokenizer, DocumentEntity.abstract),
                        func.to_tsquery(tokenizer, weighted_terms.c.term)
                    ) * weighted_terms.c.weight
                ).label("similarity_score")

                stmt = (
                    select(DocumentEntity, similarity_score)
                    .where(DocumentEntity.enabled == True)
                    .where(DocumentEntity.status != DocumentStatus.DELETED.value)
                    .where(DocumentEntity.kb_id == kb_id)
                    .where(DocumentEntity.id.notin_(banned_ids))
                )
                # 添加 GROUP BY 子句，按 ChunkEntity.id 分组
                stmt = stmt.group_by(DocumentEntity.id)

                stmt.having(similarity_score > 0)

                if doc_ids is not None:
                    stmt = stmt.where(DocumentEntity.id.in_(doc_ids))

                # 按相似度分数排序
                stmt = stmt.order_by(similarity_score.desc())
                stmt = stmt.limit(top_k)

                # 执行最终查询
                result = await session.execute(stmt, params=params)
                doc_entites = result.scalars().all()

                return doc_entites
        except Exception as e:
            err = f"根据知识库ID和关键字动态查询文档失败: {str(e)}"
            logging.exception("[ChunkManager] %s", err)
            return []

    @staticmethod
    async def get_doc_cnt_by_kb_id(kb_id: uuid.UUID) -> int:
        """根据知识库ID获取文档数量"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(func.count()).select_from(DocumentEntity).where(
                    and_(DocumentEntity.kb_id == kb_id,
                         DocumentEntity.status != DocumentStatus.DELETED.value))
                result = await session.execute(stmt)
                return result.scalar()
        except Exception as e:
            err = "获取文档数量失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def list_document(req: ListDocumentRequest) -> tuple[int, List[DocumentEntity]]:
        """
        列出文档
        :param req: 请求参数
        :return: 文档列表
        """
        try:
            async with await DataBase.get_session() as session:
                subq = (select(TaskEntity.op_id, TaskEntity.status, func.row_number().over(
                    partition_by=TaskEntity.op_id, order_by=desc(TaskEntity.created_time)).label('rn')).subquery())

                stmt = (
                    select(DocumentEntity)
                    .outerjoin(subq, and_(DocumentEntity.id == subq.c.op_id, subq.c.rn == 1))
                )
                stmt = stmt.where(DocumentEntity.status != DocumentStatus.DELETED.value)
                if req.kb_id is not None:
                    stmt = stmt.where(DocumentEntity.kb_id == req.kb_id)
                if req.doc_id is not None:
                    stmt = stmt.where(DocumentEntity.id == req.doc_id)
                if req.doc_name is not None:
                    stmt = stmt.where(DocumentEntity.name.ilike(f"%{req.doc_name}%"))
                if req.doc_type_ids is not None:
                    stmt = stmt.where(DocumentEntity.type_id.in_(req.doc_type_ids))
                if req.parse_status is not None:
                    stmt = stmt.where(subq.c.status.in_([status.value for status in req.parse_status]))
                if req.parse_methods is not None:
                    stmt = stmt.where(DocumentEntity.parse_method.in_(
                        [parse_method.value for parse_method in req.parse_methods]))
                if req.author_name is not None:
                    stmt = stmt.where(DocumentEntity.author_name.ilike(f"%{req.author_name}%"))
                if req.enabled is not None:
                    stmt = stmt.where(DocumentEntity.enabled == req.enabled)
                if req.created_time_start and req.created_time_end:
                    stmt = stmt.where(
                        between(DocumentEntity.created_time,
                                datetime.strptime(req.created_time_start,
                                                  '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc),
                                datetime.strptime(req.created_time_end, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc))
                    )
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.offset((req.page - 1) * req.page_size).limit(req.page_size)
                if req.created_time_order == OrderType.DESC:
                    stmt = stmt.order_by(DocumentEntity.created_time.desc())
                else:
                    stmt = stmt.order_by(DocumentEntity.created_time.asc())
                stmt = stmt.order_by(DocumentEntity.id.desc())
                result = await session.execute(stmt)
                document_entities = result.scalars().all()
                return (total, document_entities)
        except Exception as e:
            err = "获取文档列表失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def list_all_document_by_kb_id(kb_id: uuid.UUID) -> List[DocumentEntity]:
        """根据知识库ID获取文档列表"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(DocumentEntity).where(
                    and_(DocumentEntity.kb_id == kb_id,
                         DocumentEntity.status != DocumentStatus.DELETED.value))
                result = await session.execute(stmt)
                document_entities = result.scalars().all()
                return document_entities
        except Exception as e:
            err = "获取所有文档列表失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def list_document_by_doc_ids(doc_ids: list[uuid.UUID]) -> List[DocumentEntity]:
        """根据文档ID获取文档列表"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(DocumentEntity).where(
                    and_(DocumentEntity.id.in_(doc_ids),
                         DocumentEntity.status != DocumentStatus.DELETED.value))
                result = await session.execute(stmt)
                document_entities = result.scalars().all()
                return document_entities
        except Exception as e:
            err = "获取文档列表失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def get_document_by_doc_id(doc_id: uuid.UUID) -> DocumentEntity:
        """根据文档ID获取文档"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(DocumentEntity).where(
                    and_(DocumentEntity.id == doc_id,
                         DocumentEntity.status != DocumentStatus.DELETED.value))
                result = await session.execute(stmt)
                document_entity = result.scalars().first()
                return document_entity
        except Exception as e:
            err = "获取文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def update_doc_type_by_kb_id(
            kb_id: uuid.UUID, old_doc_type_ids: list[uuid.UUID],
            new_doc_type_id: uuid.UUID) -> None:
        """根据知识库ID更新文档类型"""
        try:
            async with await DataBase.get_session() as session:
                stmt = update(DocumentEntity).where(
                    and_(DocumentEntity.kb_id == kb_id,
                         DocumentEntity.status != DocumentStatus.DELETED.value,
                         DocumentEntity.type_id.in_(old_doc_type_ids))
                ).values(type_id=new_doc_type_id)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "更新文档类型失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def update_document_by_doc_id(doc_id: uuid.UUID, doc_dict: Dict[str, str]) -> DocumentEntity:
        """根据文档ID更新文档"""
        try:
            async with await DataBase.get_session() as session:
                stmt = update(DocumentEntity).where(
                    and_(DocumentEntity.id == doc_id,
                         DocumentEntity.status != DocumentStatus.DELETED.value)
                ).values(**doc_dict)
                await session.execute(stmt)
                await session.commit()
                return await DocumentManager.get_document_by_doc_id(doc_id)
        except Exception as e:
            err = "更新文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def update_document_by_doc_ids(doc_ids: list[uuid.UUID], doc_dict: Dict[str, str]) -> list[DocumentEntity]:
        """根据文档ID批量更新文档"""
        try:
            async with await DataBase.get_session() as session:
                stmt = update(DocumentEntity).where(
                    and_(DocumentEntity.id.in_(doc_ids),
                         DocumentEntity.status != DocumentStatus.DELETED.value)
                ).values(**doc_dict)
                await session.execute(stmt)
                await session.commit()
                stmt = select(DocumentEntity).where(
                    DocumentEntity.id.in_(doc_ids)
                )
                result = await session.execute(stmt)
                document_entities = result.scalars().all()
                return document_entities
        except Exception as e:
            err = "批量更新文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def delte_document_by_doc_id(doc_id: uuid.UUID) -> None:
        """根据文档ID删除文档"""
        pass

    @staticmethod
    async def delete_document_by_kb_id(kb_id: uuid.UUID) -> None:
        """根据知识库ID删除文档"""
        pass

    @staticmethod
    async def delete_document_by_doc_id(doc_id: uuid.UUID) -> None:
        """根据文档ID删除文档"""
        pass

    @staticmethod
    async def delete_document_by_doc_ids(doc_ids: list[uuid.UUID]) -> None:
        """根据文档ID批量删除文档"""
        pass
