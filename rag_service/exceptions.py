# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
class ApiRequestValidationError(Exception):
    ...


class KnowledgeBaseNotExistsException(Exception):
    ...


class DuplicateKnowledgeBaseAssetException(Exception):
    ...


class KnowledgeBaseAssetNotExistsException(Exception):
    ...


class KnowledgeBaseAssetAlreadyInitializedException(Exception):
    ...


class KnowledgeBaseAssetNotInitializedException(Exception):
    ...


class KnowledgeBaseAssetProductValidationError(Exception):
    ...


class KnowledgeBaseExistNonEmptyKnowledgeBaseAsset(Exception):
    ...


class KnowledgeBaseAssetJobIsRunning(Exception):
    ...


class TokenCheckFailed(Exception):
    ...


class KnowledgeBaseNotExistsException(Exception):
    ...


class TokenCheckFailed(Exception):
    ...


class ElasitcsearchEmptyKeyException(Exception):
    ...


class PostgresQueryException(Exception):
    ...
