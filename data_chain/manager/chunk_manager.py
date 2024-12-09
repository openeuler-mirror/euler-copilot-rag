# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, update, func, text, or_, and_
from typing import List, Tuple, Dict, Optional
import uuid
from data_chain.logger.logger import logger as logging

from data_chain.stores.postgres.postgres import PostgresDB, ChunkEntity, ChunkLinkEntity, DocumentEntity
from data_chain.models.service import ChunkDTO
from data_chain.exceptions.exception import ChunkException



class ChunkManager():
    @staticmethod
    async def insert_chunk(chunk_entity: ChunkEntity) -> uuid.UUID:
        async with await PostgresDB.get_session() as session:
            session.add(chunk_entity)
            await session.commit()
            return chunk_entity.id

    @staticmethod
    async def select_by_chunk_id(chunk_id: uuid.UUID) -> Optional[ChunkEntity]:
        async with await PostgresDB.get_session() as session:
            stmt = select(ChunkEntity).where(ChunkEntity.id == chunk_id)
            result = await session.execute(stmt)
            chunk_entity = result.scalars().first()
            return chunk_entity

    @staticmethod
    async def select_by_chunk_ids(chunk_ids: List[uuid.UUID]) -> Optional[ChunkEntity]:
        async with await PostgresDB.get_session() as session:
            stmt = select(ChunkEntity).where(ChunkEntity.id.in_(chunk_ids))
            result = await session.execute(stmt)
            chunk_entity_list = result.scalars().all()
            return chunk_entity_list

    @staticmethod
    async def fetch_surrounding_context(
            document_id: uuid.UUID, global_offset: int,expand_method='all',max_tokens: int = 1024,max_rd_cnt:int=50):
        try:
            if max_tokens <= 0:
                return []
            results = []
            async with await PostgresDB.get_session() as session:
                tokens = 0
                para_cnt = 0
                global_offset_set = set([global_offset])
                result = await session.execute(
                    select(func.min(ChunkEntity.global_offset), func.max(ChunkEntity.global_offset)).
                    join(DocumentEntity).
                    where(
                        ChunkEntity.document_id == document_id
                        )
                    )
                min_global_offset, max_global_offset = result.one()
                if expand_method=='nex':
                    min_global_offset=global_offset
                if expand_method=='pre':
                    max_global_offset=global_offset
                tokens_sub=0
                mv_flag=None
                rd_it=0
                chunk_entity_list = (
                    await session.execute(
                    select(ChunkEntity).
                    where(
                        and_(
                        ChunkEntity.document_id == document_id,
                        ChunkEntity.global_offset>=global_offset-max_rd_cnt,
                        ChunkEntity.global_offset<=global_offset+max_rd_cnt,
                        ChunkEntity.enabled==True
                        )
                        )
                    )
                    ).scalars().all()
                global_offset_set_dict={}
                for chunk_entity in chunk_entity_list:
                    global_offset_set_dict[chunk_entity.global_offset]=(
                                chunk_entity.id, 
                                chunk_entity.document_id,
                                chunk_entity.global_offset,
                                chunk_entity.tokens,
                                chunk_entity.text)
                while tokens < max_tokens and (min(global_offset_set)>min_global_offset or max(global_offset_set)<max_global_offset) and rd_it<max_rd_cnt:
                    result = None
                    new_global_offset = None
                    if tokens_sub<=0 and min(global_offset_set) > min_global_offset:
                        mv_flag=True
                        new_global_offset = min(global_offset_set)-1
                    elif tokens_sub>0 and max(global_offset_set) < max_global_offset:
                        mv_flag=False
                        new_global_offset = max(global_offset_set)+1
                    elif rd_it%2==0 and min(global_offset_set) > min_global_offset:
                        mv_flag=True
                        new_global_offset = min(global_offset_set)-1
                    elif max(global_offset_set) < max_global_offset:
                        mv_flag=False
                        new_global_offset = max(global_offset_set)+1
                    else:
                        break
                    result = global_offset_set_dict.get(new_global_offset,None)
                    global_offset_set.add(new_global_offset)
                    if result:
                        tokens += result[3]
                        para_cnt += 1
                        results.append(result)
                        if mv_flag:
                            tokens_sub+=result[3]
                        else:
                            tokens_sub-=result[3]
                    rd_it+=1
            return results
        except Exception as e:
            logging.error(f"Fetch surrounding context failed due to: {e}")
            return []

    @staticmethod
    async def delete_by_document_ids(document_ids: List[str]) -> None:
        async with await PostgresDB.get_session() as session:
            stmt = await session.execute(
                select(ChunkEntity).where(ChunkEntity.document_id.in_(document_ids))
            )
            entities = stmt.scalars().all()
            for entity in entities:
                await session.delete(entity)
            await session.commit()

    @staticmethod
    async def select_by_page(params, page_number, page_size) -> Tuple[List[ChunkDTO], int]:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(ChunkEntity)
                if 'document_id' in params:
                    stmt = stmt.where(ChunkEntity.document_id == params['document_id'])
                if 'text' in params:
                    stmt = stmt.where(ChunkEntity.text.ilike(f"%{params['text']}%"))
                if 'types' in params:
                    types = params['types']
                    conditions = [ChunkEntity.type.ilike(f"%{type}%") for type in types]
                    stmt = stmt.filter(or_(*conditions))
                # 获取总数
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()

                # 添加排序、偏移量和限制
                stmt = stmt.order_by(ChunkEntity.global_offset).offset((page_number - 1) * page_size).limit(page_size)

                results = await session.execute(stmt)
                chunk_list = results.scalars().all()
                return (
                    [ChunkDTO(
                        id=str(chunk_entity.id),
                        text=chunk_entity.text,
                        enabled=chunk_entity.enabled,
                        type=chunk_entity.type.split('.')[1]
                    ) for chunk_entity in chunk_list],
                    total
                )
        except Exception as e:
            logging.error(f"Select by page error: {e}")
            raise ChunkException(f"Select by page ({params}) error.")

    @staticmethod
    async def update(id: str, update_dict: Dict) -> List[str]:
        try:
            async with await PostgresDB.get_session() as session:
                # 使用update方法进行更新操作
                await session.execute(
                    update(ChunkEntity).
                    where(ChunkEntity.id == id).
                    values(**update_dict)
                )
                await session.commit()
                return ["success"]
        except Exception as e:
            logging.error(f"Update chunk status ({update_dict}) error: {e}")
            raise ChunkException(f"Update chunk status ({update_dict}) error.")
    @staticmethod
    async def find_top_k_similar_chunks(kb_id, content,topk=3, banned_ids=[]):
        try:
            if topk<=0:
                return []
            async with await PostgresDB.get_session() as session:
                # 构建SQL查询语句
                if banned_ids:
                    query = text("""
                        SELECT 
                            c.id, 
                            c.document_id, 
                            c.global_offset, 
                            c.tokens, 
                            c.text
                        FROM 
                            chunk c
                        JOIN 
                            document d ON c.document_id = d.id
                        WHERE
                            c.id NOT IN :banned_ids AND
                            c.kb_id = :kb_id AND
                            c.enabled = true AND
                            d.enabled = true AND
                            to_tsvector(:language, c.text) @@ plainto_tsquery(:language, :content)
                        ORDER BY 
                            ts_rank_cd(to_tsvector(:language, c.text), plainto_tsquery(:language, :content)) DESC 
                        LIMIT :topk;
                    """)
                else:
                    query = text("""
                        SELECT 
                            c.id, 
                            c.document_id, 
                            c.global_offset, 
                            c.tokens, 
                            c.text
                        FROM 
                            chunk c
                        JOIN 
                            document d ON c.document_id = d.id
                        WHERE
                            c.kb_id = :kb_id AND
                            c.enabled = true AND
                            d.enabled = true AND
                            to_tsvector(:language, c.text) @@ plainto_tsquery(:language, :content)
                        ORDER BY 
                            ts_rank_cd(to_tsvector(:language, c.text), plainto_tsquery(:language, :content)) DESC 
                        LIMIT :topk;
                    """)

                # 安全地绑定参数
                params = {
                    'banned_ids': banned_ids,
                    'language': 'zhparser',
                    'kb_id': kb_id,
                    'content': content,
                    'topk': topk,
                }
                result = await session.execute(query, params)
                return result.all()
        except Exception as e:
            logging.error(f"Find top k similar chunks failed due to: {e}")
            return []


class ChunkLinkManager():
    @staticmethod
    async def insert_chunk_link(chunk_link_entity: ChunkLinkEntity) -> uuid.UUID:
        async with await PostgresDB.get_session() as session:
            session.add(chunk_link_entity)
            await session.commit()
            return chunk_link_entity.id
