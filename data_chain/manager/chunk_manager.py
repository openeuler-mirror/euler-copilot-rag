# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, update, func, text, or_, and_
from typing import List, Tuple, Dict, Optional
import uuid
from data_chain.logger.logger import logger as logging
from data_chain.config.config import config
from data_chain.stores.postgres.postgres import PostgresDB, ChunkEntity, ChunkLinkEntity, DocumentEntity, TemporaryChunkEntity
from data_chain.models.service import ChunkDTO
from data_chain.exceptions.exception import ChunkException


class ChunkManager():
    @staticmethod
    async def insert_chunk(chunk_entity: ChunkEntity) -> ChunkEntity:
        async with await PostgresDB.get_session() as session:
            session.add(chunk_entity)
            await session.commit()
            await session.refresh(chunk_entity)
            return chunk_entity

    @staticmethod
    async def insert_chunks(chunk_entity_list: List[ChunkEntity]) -> List[ChunkEntity]:
        async with await PostgresDB.get_session() as session:
            try:
                session.add_all(chunk_entity_list)
                await session.commit()
                for chunk_entity in chunk_entity_list:
                    await session.refresh(chunk_entity)
                return chunk_entity_list
            except Exception as e:
                logging.error(f'Error saving chunk entities due to: {e}')

    @staticmethod
    async def select_by_chunk_id(chunk_id: uuid.UUID) -> Optional[ChunkEntity]:
        async with await PostgresDB.get_session() as session:
            stmt = select(ChunkEntity).where(ChunkEntity.id == chunk_id)
            result = await session.execute(stmt)
            chunk_entity = result.scalars().first()
            return chunk_entity

    @staticmethod
    async def select_by_chunk_ids(chunk_ids: List[uuid.UUID]) -> Optional[List[ChunkEntity]]:
        async with await PostgresDB.get_session() as session:
            stmt = select(ChunkEntity).where(ChunkEntity.id.in_(chunk_ids))
            result = await session.execute(stmt)
            chunk_entity_list = result.scalars().all()
            return chunk_entity_list

    @staticmethod
    async def fetch_surrounding_context(
            document_id: uuid.UUID, global_offset: int, expand_method='all', max_tokens: int = 1024, max_rd_cnt: int = 50):
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
                if expand_method == 'nex':
                    min_global_offset = global_offset
                if expand_method == 'pre':
                    max_global_offset = global_offset
                tokens_sub = 0
                mv_flag = None
                rd_it = 0
                chunk_entity_list = (
                    await session.execute(
                        select(ChunkEntity).
                        where(
                            and_(
                                ChunkEntity.document_id == document_id,
                                ChunkEntity.global_offset >= global_offset-max_rd_cnt,
                                ChunkEntity.global_offset <= global_offset+max_rd_cnt,
                                ChunkEntity.enabled == True
                            )
                        )
                    )
                ).scalars().all()
                global_offset_set_dict = {}
                for chunk_entity in chunk_entity_list:
                    global_offset_set_dict[chunk_entity.global_offset] = (
                        chunk_entity.id,
                        chunk_entity.document_id,
                        chunk_entity.global_offset,
                        chunk_entity.tokens,
                        chunk_entity.text)
                while tokens < max_tokens and (min(global_offset_set) > min_global_offset or max(global_offset_set) <
                                               max_global_offset) and rd_it < max_rd_cnt:
                    result = None
                    new_global_offset = None
                    if tokens_sub <= 0 and min(global_offset_set) > min_global_offset:
                        mv_flag = True
                        new_global_offset = min(global_offset_set)-1
                    elif tokens_sub > 0 and max(global_offset_set) < max_global_offset:
                        mv_flag = False
                        new_global_offset = max(global_offset_set)+1
                    elif rd_it % 2 == 0 and min(global_offset_set) > min_global_offset:
                        mv_flag = True
                        new_global_offset = min(global_offset_set)-1
                    elif max(global_offset_set) < max_global_offset:
                        mv_flag = False
                        new_global_offset = max(global_offset_set)+1
                    else:
                        break
                    result = global_offset_set_dict.get(new_global_offset, None)
                    global_offset_set.add(new_global_offset)
                    if result:
                        tokens += result[3]
                        para_cnt += 1
                        results.append(result)
                        if mv_flag:
                            tokens_sub += result[3]
                        else:
                            tokens_sub -= result[3]
                    rd_it += 1
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
                chunk_entity_list = results.scalars().all()
                return (chunk_entity_list, total)
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
    async def find_top_k_similar_chunks(kb_id, content, topk=3, banned_ids=[]):
        try:
            if topk <= 0:
                return []
            async with await PostgresDB.get_session() as session:
                # 构建SQL查询语句
                if config['DATABASE_TYPE'] == 'postgres':
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
                                c.id NOT!=ANY(:banned_ids) AND
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
                elif config['DATABASE_TYPE'] == 'opengauss':
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
                                c.id NOT!=ANY(:banned_ids) AND
                                c.kb_id = :kb_id AND
                                c.enabled = true AND
                                d.enabled = true AND
                                to_tsvector('chparser', c.text) @@ plainto_tsquery('chparser', :content)
                            ORDER BY 
                                ts_rank_cd(to_tsvector('chparser', c.text), plainto_tsquery('chparser', :content)) DESC 
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
                                to_tsvector('chparser' c.text) @@ plainto_tsquery('chparser', :content)
                            ORDER BY 
                                ts_rank_cd(to_tsvector('chparser', c.text), plainto_tsquery('chparser', :content)) DESC 
                            LIMIT :topk;
                        """)
                if config['DATABASE_TYPE'] == 'postgres':
                    # 安全地绑定参数
                    params = {
                        'banned_ids': banned_ids,
                        'language': 'zhparser',
                        'kb_id': kb_id,
                        'content': content,
                        'topk': topk,
                    }
                elif config['DATABASE_TYPE'] == 'opengauss':
                    params = {
                        'banned_ids': banned_ids,
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
    async def insert_chunk_link(chunk_link_entity: ChunkLinkEntity) -> ChunkLinkEntity:
        async with await PostgresDB.get_session() as session:
            try:
                session.add(chunk_link_entity)
                await session.commit()
                await session.refresh(chunk_link_entity)
                return chunk_link_entity
            except Exception as e:
                logging.error(f"Insert chunk link failed due to: {e}")
                return None

    @staticmethod
    async def insert_chunk_links(chunk_link_entity_list: List[ChunkLinkEntity]) -> List[ChunkLinkEntity]:
        async with await PostgresDB.get_session() as session:
            try:
                session.add_all(chunk_link_entity_list)
                await session.commit()
                for chunk_link_entity in chunk_link_entity_list:
                    await session.refresh(chunk_link_entity)
                return chunk_link_entity_list

            except Exception as e:
                logging.error(f'Insert chunk link entities failed due to: {e}')


class TemporaryChunkManager():
    @staticmethod
    async def insert_temprorary_chunk(temprorary_chunk_entity: TemporaryChunkEntity) -> TemporaryChunkEntity:
        async with await PostgresDB.get_session() as session:
            try:
                session.add(temprorary_chunk_entity)
                await session.commit()
                await session.refresh(temprorary_chunk_entity)
                return temprorary_chunk_entity
            except Exception as e:
                logging.error(f'Insert temprorary chunk entity failed due to: {e}')

    @staticmethod
    async def insert_temprorary_chunks(
            temprorary_chunk_entity_list: List[TemporaryChunkEntity]) -> List[TemporaryChunkEntity]:
        async with await PostgresDB.get_session() as session:
            try:
                session.add_all(temprorary_chunk_entity_list)
                await session.commit()
                for temprorary_chunk_entity in temprorary_chunk_entity_list:
                    await session.refresh(temprorary_chunk_entity)
                return temprorary_chunk_entity_list
            except Exception as e:
                logging.error(f'Insert temporary chunks entities failed due to: {e}')

    @staticmethod
    async def delete_by_temporary_document_ids(document_ids: List[str]) -> None:
        async with await PostgresDB.get_session() as session:
            try:
                stmt = await session.execute(
                    select(TemporaryChunkEntity).where(ChunkEntity.document_id.in_(document_ids))
                )
                entities = stmt.scalars().all()
                for entity in entities:
                    await session.delete(entity)
                await session.commit()
            except Exception as e:
                logging.error(f'Delete temporary chunks entities failed due to: {e}')

    @staticmethod
    async def select_by_temporary_chunk_ids(temporary_chunk_ids: List[uuid.UUID]) -> Optional[List[TemporaryChunkEntity]]:
        async with await PostgresDB.get_session() as session:
            try:
                stmt = select(TemporaryChunkEntity).where(TemporaryChunkEntity.id.in_(temporary_chunk_ids))
                result = await session.execute(stmt)
                temporary_chunk_entity_list = result.scalars().all()
                return temporary_chunk_entity_list
            except Exception as e:
                logging.error(f'Select temporary chunks entities failed due to: {e}')
                return None

    @staticmethod
    async def find_top_k_similar_chunks(document_ids: List[uuid.UUID], content: str, topk=3):
        try:
            if topk <= 0:
                return []
            async with await PostgresDB.get_session() as session:
                # 构建SQL查询语句
                if config['DATABASE_TYPE'] == 'postgres':
                    if document_ids:
                        query = text("""
                            SELECT 
                                c.id, 
                                c.document_id, 
                                c.global_offset, 
                                c.tokens, 
                                c.text
                            FROM 
                                temporary_chunk c
                            JOIN 
                                temporary_document d ON c.document_id = d.id
                            WHERE
                                c.document_id=ANY(:document_ids) AND
                                d.status!='deleted' AND
                                to_tsvector(:language, c.text) @@ plainto_tsquery(:language, :content) 
                            ORDER BY 
                                ts_rank_cd(to_tsvector(:language, c.text), plainto_tsquery(:language, :content)) DESC 
                            LIMIT :topk;
                        """)
                    else:
                        return []
                elif config['DATABASE_TYPE'] == 'opengauss':
                    if document_ids:
                        query = text("""
                            SELECT 
                                c.id, 
                                c.document_id, 
                                c.global_offset, 
                                c.tokens, 
                                c.text
                            FROM 
                                temporary_chunk c
                            JOIN 
                                temporary_document d ON c.document_id = d.id
                            WHERE
                                c.document_id=ANY(:document_ids) AND
                                d.status!='deleted' AND
                                to_tsvector('chparser', c.text) @@ plainto_tsquery('chparser', :content) 
                            ORDER BY 
                                ts_rank_cd(to_tsvector('chparser', c.text), plainto_tsquery('chparser', :content)) DESC 
                            LIMIT :topk;
                        """)
                    else:
                        return []
                if config['DATABASE_TYPE'] == 'postgres':
                    # 安全地绑定参数
                    params = {
                        'document_ids': document_ids,
                        'language': 'zhparser',
                        'content': content,
                        'topk': topk,
                    }
                elif config['DATABASE_TYPE'] == 'opengauss':
                    # 安全地绑定参数
                    params = {
                        'document_ids': document_ids,
                        'content': content,
                        'topk': topk,
                    }
                result = await session.execute(query, params)
                return result.all()
        except Exception as e:
            logging.error(f"Find top k similar temporary chunks failed due to: {e}")
            return []

    @staticmethod
    async def fetch_surrounding_temporary_context(
            document_id: uuid.UUID, global_offset: int, expand_method='all', max_tokens: int = 1024, max_rd_cnt: int = 50):
        try:
            if max_tokens <= 0:
                return []
            results = []
            async with await PostgresDB.get_session() as session:
                tokens = 0
                para_cnt = 0
                global_offset_set = set([global_offset])
                result = await session.execute(
                    select(func.min(TemporaryChunkEntity.global_offset), func.max(TemporaryChunkEntity.global_offset)).
                    where(
                        TemporaryChunkEntity.document_id == document_id
                    )
                )
                min_global_offset, max_global_offset = result.one()
                if expand_method == 'nex':
                    min_global_offset = global_offset
                if expand_method == 'pre':
                    max_global_offset = global_offset
                tokens_sub = 0
                mv_flag = None
                rd_it = 0
                temporary_chunk_entity_list = (
                    await session.execute(
                        select(TemporaryChunkEntity).
                        where(
                            and_(
                                TemporaryChunkEntity.document_id == document_id,
                                TemporaryChunkEntity.global_offset >= global_offset-max_rd_cnt,
                                TemporaryChunkEntity.global_offset <= global_offset+max_rd_cnt
                            )
                        )
                    )
                ).scalars().all()
                global_offset_set_dict = {}
                for temporary_chunk_entity in temporary_chunk_entity_list:
                    global_offset_set_dict[temporary_chunk_entity.global_offset] = (
                        temporary_chunk_entity.id,
                        temporary_chunk_entity.document_id,
                        temporary_chunk_entity.global_offset,
                        temporary_chunk_entity.tokens,
                        temporary_chunk_entity.text)
                while tokens < max_tokens and (min(global_offset_set) > min_global_offset or max(global_offset_set) <
                                               max_global_offset) and rd_it < max_rd_cnt:
                    result = None
                    new_global_offset = None
                    if tokens_sub <= 0 and min(global_offset_set) > min_global_offset:
                        mv_flag = True
                        new_global_offset = min(global_offset_set)-1
                    elif tokens_sub > 0 and max(global_offset_set) < max_global_offset:
                        mv_flag = False
                        new_global_offset = max(global_offset_set)+1
                    elif rd_it % 2 == 0:
                        if min(global_offset_set) > min_global_offset:
                            mv_flag = True
                            new_global_offset = min(global_offset_set)-1
                        elif max(global_offset_set) < max_global_offset:
                            mv_flag = False
                            new_global_offset = max(global_offset_set)+1

                    elif rd_it % 2 != 0:
                        if max(global_offset_set) < max_global_offset:
                            mv_flag = False
                            new_global_offset = max(global_offset_set)+1
                        elif min(global_offset_set) > min_global_offset:
                            mv_flag = True
                            new_global_offset = min(global_offset_set)-1
                    else:
                        break
                    result = global_offset_set_dict.get(new_global_offset, None)
                    global_offset_set.add(new_global_offset)
                    if result:
                        tokens += result[3]
                        para_cnt += 1
                        results.append(result)
                        if mv_flag:
                            tokens_sub += result[3]
                        else:
                            tokens_sub -= result[3]
                    rd_it += 1
            return results
        except Exception as e:
            logging.error(f"Fetch surrounding temporary context failed due to: {e}")
            return []
