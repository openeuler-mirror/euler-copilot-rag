# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
class KnowledgeBaseNotExistsException(Exception):
    ...


class TokenCheckFailed(Exception):
    ...


class ElasitcsearchEmptyKeyException(Exception):
    ...


class PostgresQueryException(Exception):
    ...
