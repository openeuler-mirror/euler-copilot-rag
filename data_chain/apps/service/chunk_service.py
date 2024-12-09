# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
import random
import time
import jieba
from data_chain.logger.logger import logger as logging
from data_chain.apps.service.llm_service import  get_question_chunk_relation
from data_chain.models.constant import ChunkRelevance
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.manager.vector_items_manager import VectorItemsManager
from data_chain.exceptions.exception import ChunkException
from data_chain.stores.postgres.postgres import PostgresDB
from data_chain.models.constant import embedding_model_out_dimensions, DocumentEmbeddingConstant
from data_chain.apps.service.embedding_service import Vectorize
from data_chain.config.config import config

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
    return await ChunkManager.select_by_page(params, page_number, page_size)


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

async def expand_chunk(document_id,global_offset,expand_method='all',max_tokens=1024):
    ex_chunk_tuple_list = await ChunkManager.fetch_surrounding_context(document_id, global_offset,expand_method=expand_method,max_tokens=max_tokens)
    return ex_chunk_tuple_list

async def filter_or_expand_chunk_by_llm(kb_id,content,document_para_dict,maxtokens):
    exist_chunk_id_set=set()
    new_document_para_dict={}
    for document_id in document_para_dict.keys():
        for chunk_tuple in document_para_dict[document_id]:
            chunk_id=chunk_tuple[0]
            exist_chunk_id_set.add(chunk_id)
    for document_id in document_para_dict.keys():
        chunk_tuple_list=document_para_dict[document_id]
        new_document_para_dict[document_id]=[]
        st=0
        en=0
        while st<len(chunk_tuple_list):
            chunk=''
            tokens=0
            while en<len(chunk_tuple_list) and (en==st or chunk_tuple_list[en][2]-chunk_tuple_list[en-1][2]==1):
                tokens+=chunk_tuple_list[en][3]
                chunk+=chunk_tuple_list[en][4]
                en+=1
            relation=await get_question_chunk_relation(content,chunk)
            fisrt_global_offset=chunk_tuple_list[st][2]
            last_global_offset=chunk_tuple_list[en-1][2]
            ex_chunk_tuple_list=[]
            if relation==ChunkRelevance.IRRELEVANT:
                if random.random()<0.5:
                    ex_chunk_tuple_list = await ChunkManager.find_top_k_similar_chunks(kb_id, content, 1)
                else:
                    kb_entity = await KnowledgeBaseManager.select_by_id(kb_id)
                    if kb_entity is None:
                        ex_chunk_tuple_list=[]
                    else:
                        embedding_model = kb_entity.embedding_model
                        vector_items_id = kb_entity.vector_items_id
                        dim = embedding_model_out_dimensions[embedding_model]
                        vector_items_table = await PostgresDB.get_dynamic_vector_items_table(vector_items_id, dim)
                        target_vector = await Vectorize.vectorize_embedding(content)
                        chunk_id_list = await VectorItemsManager.find_top_k_similar_vectors(vector_items_table, target_vector,kb_id, 1)
                        chunk_entity_list = await ChunkManager.select_by_chunk_ids(chunk_id_list)
                        for chunk_entity in chunk_entity_list:
                            ex_chunk_tuple_list.append((chunk_entity.id, chunk_entity.document_id,
                                                    chunk_entity.global_offset, chunk_entity.tokens, chunk_entity.text))
            elif relation==ChunkRelevance.WEAKLY_RELEVANT:
                if random.random()<0.5:
                    new_document_para_dict[document_id]+=chunk_tuple_list[st:en]
            elif relation==ChunkRelevance.RELEVANT_BUT_LACKS_PREVIOUS_CONTEXT:
                    new_document_para_dict[document_id]+=chunk_tuple_list[st:en]
                    ex_chunk_tuple_list=await expand_chunk(document_id,fisrt_global_offset, expand_method='pre',max_tokens=maxtokens-tokens)
            elif relation==ChunkRelevance.RELEVANT_BUT_LACKS_FOLLOWING_CONTEXT:
                new_document_para_dict[document_id]+=chunk_tuple_list[st:en]
                ex_chunk_tuple_list=await expand_chunk(document_id,last_global_offset, expand_method='nex',max_tokens=maxtokens-tokens)
            elif relation==ChunkRelevance.RELEVANT_BUT_LACKS_BOTH_CONTEXTS:
                new_document_para_dict[document_id]+=chunk_tuple_list[st:en]
                ex_chunk_tuple_list=await expand_chunk(document_id,fisrt_global_offset, expand_method='pre',max_tokens=(maxtokens-tokens)//2)
                ex_chunk_tuple_list+=await expand_chunk(document_id,last_global_offset, expand_method='nex',max_tokens=(maxtokens-tokens)//2)
            elif relation==ChunkRelevance.RELEVANT_AND_COMPLETE:
                new_document_para_dict[document_id]+=chunk_tuple_list[st:en]
            for ex_chunk_tuple in ex_chunk_tuple_list:
                        chunk_id = ex_chunk_tuple[0]
                        if chunk_id not in exist_chunk_id_set:
                            new_document_para_dict[document_id].append(ex_chunk_tuple)
                            exist_chunk_id_set.add(chunk_id)
            new_document_para_dict[document_id] = sorted(new_document_para_dict[document_id], key=lambda x: x[2])
            st=en

async def get_similar_chunks(kb_id, content, max_tokens=4096, topk=3):
    st=time.time()
    chunk_tuple_list = await ChunkManager.find_top_k_similar_chunks(kb_id, content, max(topk//2, 1))
    logging.info(f"首次关键字检索耗时: {time.time()-st}")
    kb_entity = await KnowledgeBaseManager.select_by_id(kb_id)
    if kb_entity is None:
        return []
    try:
        embedding_model = kb_entity.embedding_model
        vector_items_id = kb_entity.vector_items_id
        dim = embedding_model_out_dimensions[embedding_model]
        st=time.time()
        vector_items_table = await PostgresDB.get_dynamic_vector_items_table(vector_items_id, dim)
        target_vector = await Vectorize.vectorize_embedding(content)
        logging.info(f"向量化耗时: {time.time()-st}")
        if target_vector is not None:
            st=time.time()
            chunk_id_list = await VectorItemsManager.find_top_k_similar_vectors(vector_items_table, target_vector,kb_id, topk-len(chunk_tuple_list))
            chunk_entity_list = await ChunkManager.select_by_chunk_ids(chunk_id_list)
            logging.info(f"向量化检索耗时: {time.time()-st}")
            st=time.time()
            for chunk_entity in chunk_entity_list:
                chunk_tuple_list.append((chunk_entity.id, chunk_entity.document_id,
                                        chunk_entity.global_offset, chunk_entity.tokens, chunk_entity.text))
            logging.info(f"向量化结果关联片段耗时: {time.time()-st}")
        st=time.time()
        document_para_dict = {}
        for chunk_tuple in chunk_tuple_list:
            document_id = chunk_tuple[1]
            if document_id not in document_para_dict.keys():
                document_para_dict[document_id] = []
            document_para_dict[document_id].append(chunk_tuple)
        logging.info(f"片段整合耗时: {time.time()-st}")
        if len(chunk_tuple_list)==0:
            return []
        new_document_para_dict = {}
        ex_tokens=max_tokens//len(chunk_tuple_list)
        st=time.time()
        for document_id in document_para_dict.keys():
            global_offset_set = set()
            new_document_para_dict[document_id] = []
            for chunk_tuple in document_para_dict[document_id]:
                document_id = chunk_tuple[1]
                global_offset = chunk_tuple[2]
                tokens = chunk_tuple[3]
                ex_chunk_tuple_list = await expand_chunk(document_id,global_offset, expand_method='all',max_tokens=ex_tokens-tokens)
                ex_chunk_tuple_list.append(chunk_tuple)
                for ex_chunk_tuple in ex_chunk_tuple_list:
                    global_offset = ex_chunk_tuple[2]
                    if global_offset not in global_offset_set:
                        new_document_para_dict[document_id].append(ex_chunk_tuple)
                        global_offset_set.add(global_offset)
            new_document_para_dict[document_id] = sorted(new_document_para_dict[document_id], key=lambda x: x[2])
        logging.info(f"上下文关联耗时: {time.time()-st}")
        if config['MODEL_ENH']:
            document_para_dict=await filter_or_expand_chunk_by_llm(kb_id,content,new_document_para_dict,ex_tokens)
        else:
            document_para_dict=new_document_para_dict
        docuemnt_chunk_list=[]
        for document_id in document_para_dict:
            document_entity=await DocumentManager.select_by_id(document_id)
            document_name=document_entity.name
            chunk_list=[]
            st=0
            en=0
            while st<len(document_para_dict[document_id]):
                text=''
                while en<len(document_para_dict[document_id]) and (en==st or document_para_dict[document_id][en][2]-document_para_dict[document_id][en-1][2]==1):
                    text+=document_para_dict[document_id][en][4]
                    en+=1
                chunk_list.append(text)
                st=en
            docuemnt_chunk_list.append({'document_name':document_name,'chunk_list':chunk_list})
        return docuemnt_chunk_list
    except Exception as e:
        logging.error(f"Get similar chunking failed due to: {e}")
        return []
def split_chunk(chunk):
    return list(jieba.cut(str(chunk)))