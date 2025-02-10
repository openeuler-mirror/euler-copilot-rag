# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import re
import time
import json
import random

from rag_service.logger import get_logger
from rag_service.llms.llm import select_llm
from rag_service.models.api import QueryRequest
from rag_service.constant.prompt_manageer import prompt_template_dict
from rag_service.utils.rag_document_util import get_query_context, get_rag_document_info

logger = get_logger()


def domain_classifier(req: QueryRequest) -> bool:
    documents_info = get_rag_document_info(req=req)
    query_context = get_query_context(documents_info)
    res = select_llm(req).nonstream(req, prompt=prompt_template_dict['DOMAIN_CLASSIFIER_PROMPT_TEMPLATE'].format(
        question=req.question, context=query_context)).content
    return re.fullmatch("其他领域", res)


def domain_check_failed_return():
    default_str = '''您好，本智能助手专注于提供提供关于Linux和openEuler领域的知识和帮助，\
对于其他领域的问题可能无法提供详细的解答。'''
    index = 0
    while index < len(default_str):
        chunk_size = random.randint(1, 3)
        chunk = default_str[index:index+chunk_size]
        time.sleep(random.uniform(0.1, 0.25))
        yield "data: "+json.dumps({"content": chunk}, ensure_ascii=False)+'\n\n'
        index += chunk_size
    yield "data: [DONE]"
