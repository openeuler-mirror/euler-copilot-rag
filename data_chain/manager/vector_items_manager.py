# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from data_chain.logger.logger import logger as logging
from sqlalchemy import insert, delete, update, text
import traceback
from data_chain.stores.postgres.postgres import PostgresDB




class VectorItemsManager:
    @staticmethod
    async def add(VectorItems, params):
        # 构建插入语句
        insert_stmt = insert(VectorItems).values(
            user_id=params['user_id'],
            chunk_id=params['chunk_id'],
            kb_id=params['kb_id'],
            document_id=params['doc_id'],
            vector=params['vector'],
            enabled=params['enabled']
        ).returning(VectorItems.c.id)

        # 获取会话
        async with await PostgresDB.get_session() as session:
            result = await session.execute(insert_stmt)
            inserted_id = result.scalar()
            await session.commit()
            return inserted_id

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
                    f"WHERE v.kb_id = :kb_id AND v.chunk_id not in :banned_ids AND v.enabled = true AND document.enabled = true "
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
            # 获取会话并执行查询
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
