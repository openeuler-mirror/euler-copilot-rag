# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from rag_service.models.api.models import QueryRequest
from rag_service.llms.llm import llm_with_rag_stream_answer


def get_llm_stream_answer(
        req: QueryRequest
):
    yield from llm_with_rag_stream_answer(req)
