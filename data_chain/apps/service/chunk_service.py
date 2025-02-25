# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
import random
import time
import jieba
import traceback
import asyncio

import jieba.analyse
from data_chain.logger.logger import logger as logging
from data_chain.apps.service.llm_service import get_question_chunk_relation
from data_chain.models.constant import ChunkRelevance
from data_chain.manager.document_manager import DocumentManager, TemporaryDocumentManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.chunk_manager import ChunkManager, TemporaryChunkManager
from data_chain.manager.vector_items_manager import VectorItemsManager, TemporaryVectorItemsManager
from data_chain.exceptions.exception import ChunkException
from data_chain.stores.postgres.postgres import PostgresDB
from data_chain.models.constant import embedding_model_out_dimensions, DocumentEmbeddingConstant
from data_chain.apps.service.embedding_service import Vectorize
from data_chain.config.config import config
from data_chain.apps.base.convertor.chunk_convertor import ChunkConvertor


async def _validate_chunk_belong_to_user(user_id: uuid.UUID, chunk_id: uuid.UUID) -> bool:
    chunk_entity = await ChunkManager.select_by_chunk_id(chunk_id)
    if chunk_entity is None:
        raise ChunkException("Chunk not exist")
    if chunk_entity.user_id != user_id:
        raise ChunkException("Chunk not belong to user")


async def list_chunk(params, page_number, page_size):
    doc_entity = await DocumentManager.select_by_id(params['document_id'])
    if doc_entity is None or doc_entity.status == DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_RUNNING:
        return [], 0

    chunk_entity_list, total = await ChunkManager.select_by_page(params, page_number, page_size)
    chunk_dto_list = []
    for chunk_entity in chunk_entity_list:
        chunk_dto = ChunkConvertor.convert_entity_to_dto(chunk_entity)
        chunk_dto_list.append(chunk_dto)
    return (chunk_dto_list, total)


async def switch_chunk(id, enabled):
    await ChunkManager.update(id, {'enabled': enabled})
    doc_entity = await DocumentManager.select_by_id(id)
    if doc_entity is None:
        return
    kb_entity = await KnowledgeBaseManager.select_by_id(doc_entity.kb_id)
    if kb_entity is None:
        return
    try:
        VectorItems = await PostgresDB.get_dynamic_vector_items_table(
            kb_entity.vector_items_id, embedding_model_out_dimensions[kb_entity.embedding_model])
    except Exception as e:
        raise ChunkException("Failed to get vector items table")
        return
    await VectorItemsManager.update_by_chunk_id(VectorItems, id, {'enabled': enabled})


async def expand_chunk(document_id, global_offset, expand_method='all', max_tokens=1024, is_temporary_document=False):
    #
    # 这里返回的ex_chunk_tuple_list是个n*5二维列表
    # 内部的每个列表内容： [id, document_id, global_offset, tokens, text]
    #
    if is_temporary_document:
        ex_chunk_tuple_list = await TemporaryChunkManager.fetch_surrounding_temporary_context(document_id, global_offset, expand_method=expand_method, max_tokens=max_tokens)
    else:
        ex_chunk_tuple_list = await ChunkManager.fetch_surrounding_context(document_id, global_offset, expand_method=expand_method, max_tokens=max_tokens)
    return ex_chunk_tuple_list


async def filter_or_expand_chunk_by_llm(kb_id, content, document_para_dict, maxtokens):
    exist_chunk_id_set = set()
    new_document_para_dict = {}
    for document_id in document_para_dict.keys():
        for chunk_tuple in document_para_dict[document_id]:
            chunk_id = chunk_tuple[0]
            exist_chunk_id_set.add(chunk_id)
    for document_id in document_para_dict.keys():
        chunk_tuple_list = document_para_dict[document_id]
        new_document_para_dict[document_id] = []
        st = 0
        en = 0
        while st < len(chunk_tuple_list):
            chunk = ''
            tokens = 0
            while en < len(chunk_tuple_list) and (en == st or chunk_tuple_list[en][2]-chunk_tuple_list[en-1][2] == 1):
                tokens += chunk_tuple_list[en][3]
                chunk += chunk_tuple_list[en][4]
                en += 1
            relation = await get_question_chunk_relation(content, chunk)
            fisrt_global_offset = chunk_tuple_list[st][2]
            last_global_offset = chunk_tuple_list[en-1][2]
            ex_chunk_tuple_list = []
            if relation == ChunkRelevance.IRRELEVANT:
                if random.random() < 0.5:
                    ex_chunk_tuple_list = await ChunkManager.find_top_k_similar_chunks(kb_id, content, 1)
                else:
                    kb_entity = await KnowledgeBaseManager.select_by_id(kb_id)
                    if kb_entity is None:
                        ex_chunk_tuple_list = []
                    else:
                        embedding_model = kb_entity.embedding_model
                        vector_items_id = kb_entity.vector_items_id
                        dim = embedding_model_out_dimensions[embedding_model]
                        vector_items_table = await PostgresDB.get_dynamic_vector_items_table(vector_items_id, dim)
                        target_vector = await Vectorize.vectorize_embedding(content)
                        chunk_id_list = await VectorItemsManager.find_top_k_similar_vectors(vector_items_table, target_vector, kb_id, 1)
                        chunk_entity_list = await ChunkManager.select_by_chunk_ids(chunk_id_list)
                        for chunk_entity in chunk_entity_list:
                            ex_chunk_tuple_list.append((chunk_entity.id, chunk_entity.document_id,
                                                        chunk_entity.global_offset, chunk_entity.tokens, chunk_entity.text))
            elif relation == ChunkRelevance.WEAKLY_RELEVANT:
                if random.random() < 0.5:
                    new_document_para_dict[document_id] += chunk_tuple_list[st:en]
            elif relation == ChunkRelevance.RELEVANT_BUT_LACKS_PREVIOUS_CONTEXT:
                new_document_para_dict[document_id] += chunk_tuple_list[st:en]
                ex_chunk_tuple_list = await expand_chunk(document_id, fisrt_global_offset, expand_method='pre', max_tokens=maxtokens-tokens)
            elif relation == ChunkRelevance.RELEVANT_BUT_LACKS_FOLLOWING_CONTEXT:
                new_document_para_dict[document_id] += chunk_tuple_list[st:en]
                ex_chunk_tuple_list = await expand_chunk(document_id, last_global_offset, expand_method='nex', max_tokens=maxtokens-tokens)
            elif relation == ChunkRelevance.RELEVANT_BUT_LACKS_BOTH_CONTEXTS:
                new_document_para_dict[document_id] += chunk_tuple_list[st:en]
                ex_chunk_tuple_list = await expand_chunk(document_id, fisrt_global_offset, expand_method='pre', max_tokens=(maxtokens-tokens)//2)
                ex_chunk_tuple_list += await expand_chunk(document_id, last_global_offset, expand_method='nex', max_tokens=(maxtokens-tokens)//2)
            elif relation == ChunkRelevance.RELEVANT_AND_COMPLETE:
                new_document_para_dict[document_id] += chunk_tuple_list[st:en]
            for ex_chunk_tuple in ex_chunk_tuple_list:
                chunk_id = ex_chunk_tuple[0]
                if chunk_id not in exist_chunk_id_set:
                    new_document_para_dict[document_id].append(ex_chunk_tuple)
                    exist_chunk_id_set.add(chunk_id)
            new_document_para_dict[document_id] = sorted(new_document_para_dict[document_id], key=lambda x: x[2])
            st = en


async def get_keywords_from_content(content: str, top_k: int = 3):
    words = list(jieba.cut(content))
    keywords = set(jieba.analyse.extract_tags(content, topK=top_k))
    result = []
    exist_words = set()
    for word in words:
        if word in keywords and word not in exist_words:
            exist_words.add(word)
            result.append(word)
    return result


async def rerank_chunks(content: str, chunks: list[str], top_k: int = 3):
    pass


async def get_keywords_from_chunk(chunk: str, top_k=30):
    try:
        keywords = jieba.analyse.extract_tags(chunk, topK=top_k, withWeight=True)
    except Exception as e:
        logging.error(f"get_keywords_from_chunk error due to: {e}")
        keywords = []
    return keywords


async def get_chunk_tuple(content, temporary_document_ids=None, kb_id=None, topk=3):
    #
    # 这里返回的chunk_tuple_list是个n*5二维列表
    # 内部的每个列表内容： （id, document_id, global_offset, tokens, text）
    #
    st = time.time()
    if temporary_document_ids:
        chunk_tuple_list = await TemporaryChunkManager.find_top_k_similar_chunks(
            temporary_document_ids,
            content,
            max(topk // 2, 1))
    elif kb_id:
        chunk_tuple_list = await ChunkManager.find_top_k_similar_chunks(
            kb_id,
            content,
            max(topk//2, 1))
    else:
        return []
    logging.info(f"关键字检索耗时: {time.time()-st}")
    try:
        st = time.time()
        target_vector = await Vectorize.vectorize_embedding(content)
        logging.info(f"向量化耗时: {time.time()-st}")
        retry_times = 3
        if target_vector is not None:
            st = time.time()
            if temporary_document_ids:
                chunk_id_list = []
                for i in range(retry_times):
                    try:
                        chunk_id_list = await asyncio.wait_for(TemporaryVectorItemsManager.find_top_k_similar_temporary_vectors(
                            target_vector,
                            temporary_document_ids,
                            topk-len(chunk_tuple_list)
                        ),
                            timeout=1
                        )
                        break
                    except Exception as e:
                        logging.error(f"检索临时向量时出错: {e}")
                        continue
                chunk_entity_list = await TemporaryChunkManager.select_by_temporary_chunk_ids(chunk_id_list)
            elif kb_id:
                kb_entity = await KnowledgeBaseManager.select_by_id(kb_id)
                if kb_entity is None:
                    return []
                embedding_model = kb_entity.embedding_model
                vector_items_id = kb_entity.vector_items_id
                dim = embedding_model_out_dimensions[embedding_model]
                vector_items_table = await PostgresDB.get_dynamic_vector_items_table(vector_items_id, dim)
                chunk_id_list = []
                for i in range(retry_times):
                    try:
                        chunk_id_list = await asyncio.wait_for(VectorItemsManager.find_top_k_similar_vectors(vector_items_table, target_vector, kb_id, topk-len(chunk_tuple_list)), timeout=1)
                        break
                    except Exception as e:
                        logging.error(f"检索向量时出错: {e}")
                        continue
                chunk_entity_list = await ChunkManager.select_by_chunk_ids(chunk_id_list)
            logging.info(f"向量化检索耗时: {time.time()-st}")
            st = time.time()
            for chunk_entity in chunk_entity_list:
                chunk_tuple_list.append((chunk_entity.id, chunk_entity.document_id,
                                        chunk_entity.global_offset, chunk_entity.tokens, chunk_entity.text))
            logging.info(f"向量化结果关联片段耗时: {time.time()-st}")
        return chunk_tuple_list
    except Exception as e:
        logging.error(f"片段关联失败: {e}")
        return []


async def get_similar_chunks(
        content, kb_id=None, temporary_document_ids=None, max_tokens=4096, topk=3, devided_by_document_id=True):
    try:
        chunk_tuple_list = await get_chunk_tuple(content=content, temporary_document_ids=temporary_document_ids, kb_id=kb_id, topk=topk)
        st = time.time()
        document_para_dict = {}
        exist_chunk_id_set = set()
        for chunk_tuple in chunk_tuple_list:
            document_id = chunk_tuple[1]
            if document_id not in document_para_dict.keys():
                document_para_dict[document_id] = []
            if chunk_tuple[0] not in exist_chunk_id_set:
                exist_chunk_id_set.add(chunk_tuple[0])
                document_para_dict[document_id].append(chunk_tuple)
        logging.info(f"片段整合耗时: {time.time()-st}")
        if len(chunk_tuple_list) == 0:
            return []
        new_document_para_dict = {}
        ex_tokens = max_tokens//len(exist_chunk_id_set)
        st = time.time()
        leave_ex_tokens = 0
        for document_id in document_para_dict.keys():
            global_offset_set = set()
            new_document_para_dict[document_id] = []
            for chunk_tuple in document_para_dict[document_id]:
                document_id = chunk_tuple[1]
                global_offset = chunk_tuple[2]
                tokens = chunk_tuple[3]
                leave_ex_tokens += ex_tokens
                if temporary_document_ids:
                    ex_chunk_tuple_list = await expand_chunk(document_id, global_offset, expand_method='all', max_tokens=leave_ex_tokens-tokens, is_temporary_document=True)
                elif kb_id:
                    ex_chunk_tuple_list = await expand_chunk(document_id, global_offset, expand_method='all', max_tokens=leave_ex_tokens-tokens)
                ex_chunk_tuple_list.append(chunk_tuple)
                for ex_chunk_tuple in ex_chunk_tuple_list:
                    global_offset = ex_chunk_tuple[2]
                    if global_offset not in global_offset_set:
                        new_document_para_dict[document_id].append(ex_chunk_tuple)
                        global_offset_set.add(global_offset)
                        leave_ex_tokens -= ex_chunk_tuple[3]
                if leave_ex_tokens <= 0:
                    leave_ex_tokens = 0
            new_document_para_dict[document_id] = sorted(new_document_para_dict[document_id], key=lambda x: x[2])
        logging.info(f"上下文关联耗时: {time.time()-st}")
        # if config['MODEL_ENH']:
        #     document_para_dict = await filter_or_expand_chunk_by_llm(kb_id, content, new_document_para_dict, ex_tokens)
        # else:
        #     document_para_dict = new_document_para_dict
        document_para_dict = new_document_para_dict
        if devided_by_document_id:
            docuemnt_chunk_list = []
            for document_id in document_para_dict:
                document_entity = None
                if temporary_document_ids:
                    document_entity = await TemporaryDocumentManager.select_by_id(document_id)
                elif kb_id:
                    document_entity = await DocumentManager.select_by_id(document_id)
                if document_entity is not None:
                    document_name = document_entity.name
                else:
                    document_name = ''
                chunk_list = []
                st = 0
                en = 0
                while st < len(document_para_dict[document_id]):
                    text = ''
                    while en < len(
                            document_para_dict[document_id]) and (
                            en == st or document_para_dict[document_id][en][2]
                            - document_para_dict[document_id][en - 1][2] ==
                            1):
                        text += document_para_dict[document_id][en][4]
                        en += 1
                    chunk_list.append(text)
                    st = en
                docuemnt_chunk_list.append({'document_name': document_name, 'chunk_list': chunk_list})
            return docuemnt_chunk_list
        else:
            chunk_list = []
            for document_id in document_para_dict:
                st = 0
                en = 0
                while st < len(document_para_dict[document_id]):
                    text = ''
                    while en < len(
                            document_para_dict[document_id]) and (
                            en == st or document_para_dict[document_id][en][2]
                            - document_para_dict[document_id][en - 1][2] ==
                            1):
                        text += document_para_dict[document_id][en][4]
                        en += 1
                    chunk_list.append(text)
                    st = en
            return chunk_list
    except Exception as e:
        logging.error(f"Get similar chun failed due to e: {e}")
        logging.error(f"Get similar chun failed due to traceback: {traceback.format_exc()}")
        return []


async def get_similar_full_text(
        content, kb_id=None, temporary_document_ids=None, topk=3):
    try:
        chunk_tuple_list = await get_chunk_tuple(content=content, temporary_document_ids=temporary_document_ids, kb_id=kb_id, topk=topk)
        full_text_list = []
        document_id_set = set()
        for chunk_tuple in chunk_tuple_list:
            if chunk_tuple[1] not in document_id_set:
                document_id_set.add(chunk_tuple[1])
                if temporary_document_ids:
                    document_entity = await TemporaryDocumentManager.select_by_id(chunk_tuple[1])
                    full_text_list.append(document_entity.full_text)
                elif kb_id:
                    document_entity = await DocumentManager.select_by_id(chunk_tuple[1])
                    full_text_list.append(document_entity.full_text)
        logging.info(f"Get similar full text success, full_text_list: {full_text_list}")
        return full_text_list
    except Exception as e:
        logging.error(f"Get similar full text failed due to e: {e}")
        logging.error(f"Get similar full text failed due to traceback: {traceback.format_exc()}")
        return []


def split_chunk(chunk):
    return list(jieba.cut(str(chunk)))
