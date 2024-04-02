# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import re

from rag_service.logger import get_logger
from rag_service.llms.llm import llm_call
from rag_service.models.api.models import QueryRequest
from rag_service.config import DOMAIN_CLASSIFIER_PROMPT

logger = get_logger()

def domain_classifier(req: QueryRequest, query_context: str) -> bool:
    res = llm_call(prompt="",
                   question=DOMAIN_CLASSIFIER_PROMPT.replace(
                       '{{question}}', req.question).replace(
                       '{{context}}', query_context),
                   history=[]).strip()
    logger.info("domain classifier: "+res)
    return re.fullmatch("其他领域", res)
