# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from rag_service.models.api.models import QueryRequest
from rag_service.llms.llm import qwen_llm_stream_answer, spark_llm_stream_answer


def get_qwen_llm_stream_answer(req: QueryRequest):
    yield from qwen_llm_stream_answer(req)


def get_spark_llm_stream_answer(req: QueryRequest):
    return spark_llm_stream_answer(req)
