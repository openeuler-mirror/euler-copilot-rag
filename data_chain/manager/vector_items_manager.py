# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
from typing import List
from sqlalchemy import insert, delete, update, text
import traceback
from data_chain.logger.logger import logger as logging
from data_chain.stores.postgres.postgres import PostgresDB,TemporaryVectorItemstEntity




class VectorItemsManager:
    @staticmethod
    async def add(VectorItems, vector):
        # 构建插入语句
        insert_stmt = insert(VectorItems).values(
            user_id=vector['user_id'],
            chunk_id=vector['chunk_id'],
            kb_id=vector['kb_id'],
            document_id=vector['doc_id'],
            vector=vector['vector'],
            enabled=vector['enabled']
        ).returning(VectorItems.c.id)

        # 获取会话
        async with await PostgresDB.get_session() as session:
            result = await session.execute(insert_stmt)
            inserted_id = result.scalar()
            await session.commit()
            return inserted_id
    @staticmethod
    async def add_all(VectorItems, vector_list):
        # 构建插入语句
        insert_stmt = (
            insert(VectorItems)
            .values([
                {
                    "user_id": vector['user_id'],
                    "chunk_id": vector['chunk_id'],
                    "kb_id": vector['kb_id'],
                    "document_id": vector['doc_id'],
                    "vector": vector['vector'],
                    "enabled": vector['enabled']
                }
                for vector in vector_list
            ])
            .returning(VectorItems.c.id)  # 假设VectorItems有id字段
        )

        # 获取会话
        async with await PostgresDB.get_session() as session:
            result = await session.execute(insert_stmt)
            inserted_ids = result.scalars().all()
            await session.commit()
            return inserted_ids
    @staticmethod
    async def del_by_id(VectorItems, id):
        try:
            # 构建删除语句
            delete_stmt = delete(VectorItems).where(VectorItems.c.id == id)

            # 获取会话
            async with await PostgresDB.get_session() as session:
                await session.execute(delete_stmt)
                await session.commit()
        except Exception as e:
            logging.error(f"Delete vector item failed due to error: {e}")

    @staticmethod
    async def del_by_chunk_ids(VectorItems, chunk_ids):
        try:
            # 构建删除语句
            delete_stmt = delete(VectorItems).where(VectorItems.c.chunk_id.in_(chunk_ids))

            # 获取会话
            async with await PostgresDB.get_session() as session:
                await session.execute(delete_stmt)
                await session.commit()
        except Exception as e:
            logging.error(f"Delete vector item failed due to error: {e}")

    @staticmethod
    async def del_by_doc_ids(VectorItems, doc_ids):
        try:
            # 构建删除语句
            delete_stmt = delete(VectorItems).where(VectorItems.c.doc_id.in_(doc_ids))

            # 获取会话
            async with await PostgresDB.get_session() as session:
                await session.execute(delete_stmt)
                await session.commit()
        except Exception as e:
            logging.error(f"Delete vector item failed due to error: {e}")

    @staticmethod
    async def update_by_chunk_id(VectorItems, chunk_id, up_dict):
        try:
            # 构建删除语句
            update_stmt = update(VectorItems).where(VectorItems.c.chunk_id == chunk_id).values(**up_dict)
            # 获取会话
            async with await PostgresDB.get_session() as session:
                await session.execute(update_stmt)
                await session.commit()
        except Exception as e:
            logging.error(f"Update vector item failed due to error: {e}")
    @staticmethod
    async def find_top_k_similar_vectors(VectorItems, target_vector, kb_id, topk=3, banned_ids=[]):
        try:
            if topk<=0:
                return []
            # 构造查询
            if banned_ids:
                query_sql = (
                    f"SELECT v.chunk_id "
                    f"FROM \"{VectorItems.name}\" AS v "
                    f"INNER JOIN document ON v.document_id = document.id "
                    f"WHERE v.kb_id = :kb_id AND v.chunk_id!=ANY(:banned_ids) AND v.enabled = true AND document.enabled = true "
                    f"ORDER BY v.vector <=> :target_vector "
                    f"LIMIT :topk")
            else:
                query_sql = (
                    f"SELECT v.chunk_id "
                    f"FROM \"{VectorItems.name}\" AS v "
                    f"INNER JOIN document ON v.document_id = document.id "
                    f"WHERE v.kb_id = :kb_id AND v.enabled = true AND document.enabled = true "
                    f"ORDER BY v.vector <=> :target_vector "
                    f"LIMIT :topk")
            async with await PostgresDB.get_session() as session:
                # 使用execute执行原始SQL语句，并传递参数
                result = await session.execute(
                    text(query_sql),
                    {
                        "kb_id": kb_id,
                        "banned_ids": banned_ids,
                        "target_vector": str(target_vector),
                        "topk": topk
                    }
                )
                result = result.scalars().all()
                return result
        except Exception as e:
            logging.error(f"Query for similar vectors failed due to error: {e}")
            logging.error(f"Error details: {traceback.format_exc()}")
            return []
class TemporaryVectorItemsManager:
    @staticmethod
    async def add(temporary_vector_items_entity:TemporaryVectorItemstEntity)->TemporaryVectorItemstEntity:
        try:
            async with await PostgresDB.get_session() as session:
                session.add(temporary_vector_items_entity)
                await session.commit()
                await session.refresh(temporary_vector_items_entity)
                return temporary_vector_items_entity
        except Exception as e:
            logging.error(f"Add temporary vector items failed due to error: {e}")
            return None
    @staticmethod
    async def add_all(temporary_vector_items_entity_list:List[TemporaryVectorItemstEntity])->List[TemporaryVectorItemstEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                session.add_all(temporary_vector_items_entity_list)
                await session.commit()
                for temporary_vector_items_entity in temporary_vector_items_entity_list:
                    await session.refresh(temporary_vector_items_entity)
                return temporary_vector_items_entity_list
        except Exception as e:
            logging.error(f"Add temporary vector items failed due to error: {e}")
            return None
    @staticmethod
    async def find_top_k_similar_temporary_vectors(target_vector, document_ids:List[uuid.UUID],topk=3)->List[uuid.UUID]:
        try:
            if topk<=0:
                return []
            # 构造查询
            if document_ids:
                query_sql = (
                    f"SELECT v.chunk_id "
                    f"FROM temporary_vector_items AS v "
                    f"INNER JOIN temporary_document ON v.document_id = temporary_document.id "
                    f"WHERE v.document_id= ANY(:document_ids) AND temporary_document.status!='deleted'"
                    f"ORDER BY v.vector <=> :target_vector "
                    f"LIMIT :topk"
                    )
            else:
                return []
            # 获取会话并执行查询
            async with await PostgresDB.get_session() as session:
                # 使用execute执行原始SQL语句，并传递参数
                result = await session.execute(
                    text(query_sql),
                    {
                        "document_ids": document_ids,
                        "target_vector": str(target_vector),
                        "topk": topk
                    }
                )
                result = result.scalars().all()
                return result
        except Exception as e:
            logging.error(f"Query for similar temporary vectors failed due to error: {e}")
            return []