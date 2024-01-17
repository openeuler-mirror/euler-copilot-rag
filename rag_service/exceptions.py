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


class FileDownloadTimeoutException(Exception):
    ...


class DuplicatedRedisKeyspaceException(Exception):
    ...


class KmsInvokeFailureException(Exception):
    ...


class KnowledgeBaseAssetWikiUriValidationError(Exception):
    ...


class KnowledgeBaseAssetProductValidationError(Exception):
    ...


class AppDynamicTokenException(Exception):
    ...


class KnowledgeBaseExistNonEmptyKnowledgeBaseAsset(Exception):
    ...


class KnowledgeBaseAssetJobIsRunning(Exception):
    ...
