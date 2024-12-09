# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.


class OssConstant():
    IMPORT_FILE_SAVE_FOLDER = "./stash"
    EXPORT_FILE_SAVE_FOLDER = "./export"
    UPLOAD_DOCUMENT_SAVE_FOLDER = "./document"
    ZIP_FILE_SAVE_FOLDER = "./zip"
    PARSER_SAVE_FOLDER = "./parser" 

    MINIO_BUCKET_DOCUMENT = "document"
    MINIO_BUCKET_KNOWLEDGEBASE = "knowledgebase"
    MINIO_BUCKET_EXPORTZIP = "exportzip"
    MINIO_BUCKET_PICTURE = "picture"

class DocumentEmbeddingConstant():
    DOCUMENT_EMBEDDING_RUN = 'run'
    DOCUMENT_EMBEDDING_CANCEL = 'cancel'

    DOCUMENT_EMBEDDING_STATUS_PENDING = "pending"
    DOCUMENT_EMBEDDING_STATUS_RUNNING = "running"


class TaskConstant():
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


class KnowledgeStatusEnum():
    IMPORTING = "importing"
    EXPROTING = "exporting"
    IDLE = 'idle'
    DELETE = 'delete'


class TaskActionEnum():
    CANCEL = "cancel"
    RESTART = "restart"
    DELETE = "delete"


class KnowledgeLanguageEnum():
    ZH = "简体中文"
    EN = "English"
    @classmethod
    def get_all_values(cls):
        return [value for name, value in cls.__dict__.items()
                if not name.startswith("__") and isinstance(value, str)]

class EmbeddingModelEnum():
    BGE_LARGE_ZH = "bge_large_zh"
    BGE_LARGE_EN = "bge_large_en"
    @classmethod
    def get_all_values(cls):
        return [value for name, value in cls.__dict__.items()
                if not name.startswith("__") and isinstance(value, str)]


embedding_model_out_dimensions = {
    'bge_large_zh': 1024,
    'bge_large_en': 1024
}


class ParseMethodEnum():
    GENERAL = "general"
    OCR = "ocr"
    ENHANCED = "enhanced"
    @classmethod
    def get_all_values(cls):
        return [value for name, value in cls.__dict__.items()
                if not name.startswith("__") and isinstance(value, str)]

class ParseExtensionEnum():
    PDF = ".pdf"
    DOCX = ".docx"
    DOC = ".doc"
    TXT = ".txt"
    XLSX = ".xlsx"
    HTML = ".html"
    MD = ".md"
    @classmethod
    def get_all_values(cls):
        return [value for name, value in cls.__dict__.items()
                if not name.startswith("__") and isinstance(value, str)]
class ChunkRelevance():
    IRRELEVANT = 1
    WEAKLY_RELEVANT = 2
    RELEVANT_BUT_LACKS_PREVIOUS_CONTEXT = 3
    RELEVANT_BUT_LACKS_FOLLOWING_CONTEXT = 4
    RELEVANT_BUT_LACKS_BOTH_CONTEXTS = 5
    RELEVANT_AND_COMPLETE = 6

default_document_type_id = '00000000-0000-0000-0000-000000000000'