# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
from pydantic import BaseModel, Field
import random
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.convertor import Convertor
from data_chain.stores.database.database import ChunkEntity
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.entities.response_data import Chunk, DocChunk


class BaseSearcher:
    @staticmethod
    def find_worker_class(worker_name: str):
        subclasses = BaseSearcher.__subclasses__()
        for subclass in subclasses:
            if subclass.name == worker_name:
                return subclass
        return None

    @staticmethod
    async def search(
            search_method: str, kb_id: uuid.UUID, query: str, top_k: int = 5, doc_ids: list[uuid.UUID] = None,
            banned_ids: list[uuid.UUID] = []) -> list[ChunkEntity]:
        """
        检索器
        :param search_method: 检索器方法
        :param query: 查询
        :param top_k: 返回的结果数量
        :return: 检索结果
        """
        search_class = BaseSearcher.find_worker_class(search_method)
        if search_class:
            return await search_class.search(
                query=query, kb_id=kb_id, top_k=top_k, doc_ids=doc_ids, banned_ids=banned_ids
            )
        else:
            err = f"[BaseSearch] 检索器不存在，search_method: {search_method}"
            logging.exception(err)
            raise Exception(err)

    @staticmethod
    async def rerank(chunk_entities: list[ChunkEntity], query: str) -> list[ChunkEntity]:
        """
        重新排序
        :param list: 检索结果
        :param query: 查询
        :return: 重新排序后的结果
        """
        score_chunk_entities = []
        for chunk_entity in chunk_entities:
            score = TokenTool.cal_jac(chunk_entity.text, query)
            score_chunk_entities.append((score, chunk_entity))
        score_chunk_entities.sort(key=lambda x: x[0], reverse=True)
        sorted_chunk_entities = [chunk_entity for _, chunk_entity in score_chunk_entities]
        return sorted_chunk_entities

    @staticmethod
    async def related_surround_chunk(
            chunk_entity: ChunkEntity, tokens_limit: int = 1024, banned_ids: list[uuid.UUID] = []) -> list[ChunkEntity]:
        """
        相关上下文
        :param list: 检索结果
        :param query: 查询
        :return: 相关上下文
        """
        chunk_entities = await ChunkManager.fetch_surrounding_chunk_by_doc_id_and_global_offset(chunk_entity.doc_id, chunk_entity.global_offset, 100, banned_ids)
        chunk_entity_dict = {}
        lower = chunk_entity.global_offset-1
        upper = chunk_entity.global_offset+1
        min_offset = chunk_entity.global_offset
        max_offset = chunk_entity.global_offset
        for chunk_entity in chunk_entities:
            if chunk_entity.global_offset < min_offset:
                min_offset = chunk_entity.global_offset
            if chunk_entity.global_offset > max_offset:
                max_offset = chunk_entity.global_offset
            chunk_entity_dict[chunk_entity.global_offset] = chunk_entity
        related_chunk_entities = []
        tokens_sub = 0
        tokens_sum = 0
        find_lower = True
        while 1:
            if tokens_sum >= tokens_limit:
                break
            if lower < min_offset and upper > max_offset:
                break
            if tokens_sub < 0:
                if lower >= min_offset:
                    find_lower = True
                else:
                    find_lower = False
            elif tokens_sub > 0:
                if upper <= max_offset:
                    find_lower = False
                else:
                    find_lower = True
            else:
                rd = random.randint(0, 1)
                if rd == 0:
                    if lower >= min_offset:
                        find_lower = True
                    else:
                        find_lower = False
                else:
                    if upper <= max_offset:
                        find_lower = False
                    else:
                        find_lower = True
            if find_lower:
                if chunk_entity_dict.get(lower) is not None:
                    tokens_sub += chunk_entity_dict[lower].tokens
                    related_chunk_entities.append(chunk_entity_dict[lower])
                    tokens_sum += chunk_entity_dict[lower].tokens
                lower -= 1
            else:
                if chunk_entity_dict.get(upper) is not None:
                    tokens_sub -= chunk_entity_dict[upper].tokens
                    related_chunk_entities.append(chunk_entity_dict[upper])
                    tokens_sum += chunk_entity_dict[upper].tokens
                upper += 1
        return related_chunk_entities

    @staticmethod
    async def unique_chunk(chunk_entities: list[ChunkEntity]) -> list[ChunkEntity]:
        """
        去重
        :param list: 检索结果
        :return: 去重后的结果
        """
        unique_chunk_entities = []
        chunk_entity_dict = {}
        for chunk_entity in chunk_entities:
            if chunk_entity.doc_id not in chunk_entity_dict:
                chunk_entity_dict[chunk_entity.doc_id] = chunk_entity
                unique_chunk_entities.append(chunk_entity)
        return unique_chunk_entities

    @staticmethod
    async def classify_by_doc_id(chunk_entities: list[ChunkEntity]) -> list[DocChunk]:
        """
        按照文档ID分类
        :param list: 检索结果
        :return: 分类后的结果
        """
        doc_chunk_dict = {}
        chunk_entities = sorted(chunk_entities, key=lambda x: x.global_offset)
        for chunk_entity in chunk_entities:
            if chunk_entity.doc_id not in doc_chunk_dict:
                doc_chunk_dict[chunk_entity.doc_id] = DocChunk(
                    docId=chunk_entity.doc_id, docName=chunk_entity.doc_name, chunks=[])
            chunk = await Convertor.convert_chunk_entity_to_chunk(chunk_entity)
            doc_chunk_dict[chunk_entity.doc_id].chunks.append(chunk)
        return list(doc_chunk_dict.values())
