# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

class BaseConstant():
    @classmethod
    def get_all_values(cls):
        return [value for name, value in cls.__dict__.items()
                if not name.startswith("__") and isinstance(value, str)]
class OssConstant(BaseConstant):
    IMPORT_FILE_SAVE_FOLDER = "./stash"
    EXPORT_FILE_SAVE_FOLDER = "./export"
    UPLOAD_DOCUMENT_SAVE_FOLDER = "./document"
    ZIP_FILE_SAVE_FOLDER = "./zip"
    PARSER_SAVE_FOLDER = "./parser" 

    MINIO_BUCKET_DOCUMENT = "document"
    MINIO_BUCKET_KNOWLEDGEBASE = "knowledgebase"
    MINIO_BUCKET_PICTURE = "picture"

class DocumentEmbeddingConstant(BaseConstant):
    DOCUMENT_EMBEDDING_RUN = 'run'
    DOCUMENT_EMBEDDING_CANCEL = 'cancel'

    DOCUMENT_EMBEDDING_STATUS_PENDING = "pending"
    DOCUMENT_EMBEDDING_STATUS_RUNNING = "running"

class DocumentStatusEnum(BaseConstant):
    PENDIND='pending'
    RUNNING='running'
    DELETED='deleted'

class TemporaryDocumentStatusEnum(BaseConstant):
    EXIST='exist'
    DELETED='deleted'
class TaskConstant(BaseConstant):
    TASK_REDIS_QUEUE_KEY = "TASK_QUEUE"

    TASK_STATUS_PENDING = "pending"
    TASK_STATUS_SUCCESS = "success"
    TASK_STATUS_FAILED = "failed"
    TASK_STATUS_RUNNING = "running"
    TASK_STATUS_CANCELED = "canceled"
    TASK_STATUS_DELETED = "deleted"

    IMPORT_KNOWLEDGE_BASE = "import_knowledge_base"
    EXPORT_KNOWLEDGE_BASE = "export_knowledge_base"
    PARSE_DOCUMENT = "parse_document"
    PARSE_TEMPORARY_DOCUMENT = "parse_temporary_document"

class KnowledgeStatusEnum(BaseConstant):
    IMPORTING = "importing"
    EXPROTING = "exporting"
    IDLE = 'idle'
    DELETE = 'delete'

class TaskActionEnum(BaseConstant):
    CANCEL = "cancel"
    RESTART = "restart"
    DELETE = "delete"

class KnowledgeLanguageEnum(BaseConstant):
    ZH = "简体中文"
    EN = "English"

class EmbeddingModelEnum(BaseConstant):
    BGE_LARGE_ZH = "bge_large_zh"
    BGE_LARGE_EN = "bge_large_en"

class ParseMethodEnum(BaseConstant):
    GENERAL = "general"
    OCR = "ocr"
    ENHANCED = "enhanced"

class ParseExtensionEnum(BaseConstant):
    PDF = ".pdf"
    DOCX = ".docx"
    DOC = ".doc"
    TXT = ".txt"
    XLSX = ".xlsx"
    HTML = ".html"
    MD = ".md"
class ChunkRelevance(BaseConstant):
    IRRELEVANT = 1
    WEAKLY_RELEVANT = 2
    RELEVANT_BUT_LACKS_PREVIOUS_CONTEXT = 3
    RELEVANT_BUT_LACKS_FOLLOWING_CONTEXT = 4
    RELEVANT_BUT_LACKS_BOTH_CONTEXTS = 5
    RELEVANT_AND_COMPLETE = 6

default_document_type_id = '00000000-0000-0000-0000-000000000000'
embedding_model_out_dimensions = {
    'bge_large_zh': 1024,
    'bge_large_en': 1024
}