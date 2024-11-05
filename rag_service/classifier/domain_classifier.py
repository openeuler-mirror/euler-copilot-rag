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

