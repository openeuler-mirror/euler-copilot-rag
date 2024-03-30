# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
class ApiRequestValidationError(Exception):
    ...


class KnowledgeBaseAssetNotExistsException(Exception):
    ...


class KnowledgeBaseAssetJobIsRunning(Exception):
    ...


class KnowledgeBaseAssetProductValidationError(Exception):
    ...


class DuplicateKnowledgeBaseAssetException(Exception):
    ...


class KnowledgeBaseAssetAlreadyInitializedException(Exception):
    ...


class KnowledgeBaseAssetNotInitializedException(Exception):
    ...


class KnowledgeBaseExistNonEmptyKnowledgeBaseAsset(Exception):
    ...


class KnowledgeBaseNotExistsException(Exception):
    ...


class TokenCheckFailed(Exception):
    ...


class LlmRequestException(Exception):
    ...


class LlmAnswerException(Exception):
    ...


class PostgresQueryException(Exception):
    ...


class Neo4jQueryException(Exception):
    ...
