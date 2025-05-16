# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import re
import uuid
from typing import Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, validator, constr

from data_chain.entities.enum import (
    TeamType,
    Tokenizer,
    ParseMethod,
    UserStatus,
    UserMessageType,
    UserMessageStatus,
    KnowledgeBaseStatus,
    DocParseRelutTopology,
    DocumentStatus,
    ChunkType,
    ChunkParseTopology,
    DataSetStatus,
    TestingStatus,
    SearchMethod,
    TaskType,
    TaskStatus,
    OrderType)
from data_chain.entities.common import DEFAULt_DOC_TYPE_ID


class ListTeamRequest(BaseModel):
    team_type: TeamType = Field(default=TeamType.ALL, description="团队类型", alias="teamType")
    team_id: Optional[uuid.UUID] = Field(default=None, description="团队id", alias="teamId")
    team_name: Optional[str] = Field(default=None, description="团队名称", alias="teamName")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class ListTeamMsgRequest(BaseModel):
    team_id: Optional[uuid.UUID] = Field(default=None, description="团队id", alias="teamId")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class ListTeamUserRequest(BaseModel):
    team_id: uuid.UUID = Field(description="团队ID", alias="teamId")
    user_sub: Optional[str] = Field(default=None, description="用户ID", alias="userSub")
    user_name: Optional[str] = Field(default=None, description="用户名", alias="userName")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class CreateTeamRequest(BaseModel):
    team_name: str = Field(default='这是一个默认的团队名称', min_length=1, max_length=30, alias="teamName")
    description: str = Field(default='', max_length=150)
    is_public: bool = Field(default=False, alias="isPublic")


class UpdateTeamRequest(BaseModel):
    team_name: str = Field(default='这是一个默认的团队名称', min_length=1, max_length=30, alias="teamName")
    description: str = Field(default='', max_length=150)
    is_public: bool = Field(default=False)


class DocumentType(BaseModel):
    doc_type_id: uuid.UUID = Field(description="文档类型的id", alias="docTypeId")
    doc_type_name: str = Field(default='这是一个默认的文档类型名称', min_length=1, max_length=20, alias="docTypeName")


class ListKnowledgeBaseRequest(BaseModel):
    team_id: uuid.UUID = Field(description="团队id", alias="teamId")
    kb_id: Optional[uuid.UUID] = Field(default=None, description="资产id", alias="kbId")
    kb_name: Optional[str] = Field(default=None, description="资产名称", alias="kbName")
    author_name: Optional[str] = Field(default=None, description="资产创建者", alias="authorName")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class CreateKnowledgeBaseRequest(BaseModel):
    kb_name: str = Field(default='这是一个默认的资产名称', min_length=1, max_length=20, alias="kbName")
    description: str = Field(default='', max_length=150)
    tokenizer: Tokenizer = Field(default=Tokenizer.ZH)
    embedding_model: str = Field(default='', description="知识库使用的embedding模型", alias="embeddingModel")
    default_chunk_size: int = Field(default=512, description="知识库默认文件分块大小", alias="defaultChunkSize", min=128, max=2048)
    default_parse_method: ParseMethod = Field(
        default=ParseMethod.GENERAL, description="知识库默认解析方法", alias="defaultParseMethod")
    upload_count_limit: int = Field(default=128, description="知识库上传文件数量限制", alias="uploadCountLimit", min=128, max=1024)
    upload_size_limit: int = Field(default=512, description="知识库上传文件大小限制", alias="uploadSizeLimit", min=128, max=2048)
    doc_types: List[DocumentType] = Field(default=[], description="知识库支持的文档类型", alias="docTypes")


class UpdateKnowledgeBaseRequest(BaseModel):
    kb_name: str = Field(default='这是一个默认的资产名称', min_length=1, max_length=30, alias="kbName")
    description: str = Field(default='', max_length=150)
    tokenizer: Tokenizer = Field(default=Tokenizer.ZH)
    default_chunk_size: int = Field(default=512, description="知识库默认文件分块大小", alias="defaultChunkSize", min=128, max=2048)
    default_parse_method: ParseMethod = Field(
        default=ParseMethod.GENERAL, description="知识库默认解析方法", alias="defaultParseMethod")
    upload_count_limit: int = Field(default=128, description="知识库上传文件数量限制", alias="uploadCountLimit", min=128, max=1024)
    upload_size_limit: int = Field(default=512, description="知识库上传文件大小限制", alias="uploadSizeLimit", min=128, max=2048)
    doc_types: List[DocumentType] = Field(default=[], description="知识库支持的文档类型", alias="docTypes")


class ListDocumentRequest(BaseModel):
    kb_id: uuid.UUID = Field(description="资产id", alias="kbId")
    doc_id: Optional[uuid.UUID] = Field(default=None, description="文档id", alias="docId")
    doc_name: Optional[str] = Field(default=None, description="文档名称", alias="docName")
    doc_type_id: Optional[uuid.UUID] = Field(default=None, description="文档类型id", alias="docTypeId")
    parse_status: Optional[list[TaskStatus]] = Field(default=None, description="文档解析状态", alias="parseStatus")
    parse_method: Optional[ParseMethod] = Field(default=None, description="文档解析方法", alias="parseMethod")
    author_name: Optional[str] = Field(default=None, description="文档创建者", alias="authorName")
    created_time_start: Optional[str] = Field(default=None, description="文档创建时间开始", alias="createdTimeStart")
    created_time_end: Optional[str] = Field(default=None, description="文档创建时间结束", alias="createdTimeEnd")
    created_time_order: OrderType = Field(default=OrderType.DESC, description="文档创建时间排序", alias="createdTimeOrder")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class UpdateDocumentRequest(BaseModel):
    doc_name: str = Field(default='这是一个默认的文档名称', min_length=1, max_length=150, alias="docName")
    doc_type_id: uuid.UUID = Field(default=DEFAULt_DOC_TYPE_ID, description="文档类型的id", alias="docTypeId")
    parse_method: ParseMethod = Field(
        default=ParseMethod.GENERAL, description="知识库默认解析方法", alias="parseMethod")
    chunk_size: int = Field(default=512, description="知识库默认文件分块大小", alias="chunkSize", min=128, max=2048)
    enabled: bool = Field(default=True, description="文档是否启用")


class ListChunkRequest(BaseModel):
    doc_id: uuid.UUID = Field(description="文档id", alias="docId")
    text: Optional[str] = Field(default=None, description="分块文本内容", alias="text")
    types: Optional[list[ChunkType]] = Field(default=None, description="分块类型", alias="types")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class UpdateChunkRequest(BaseModel):
    text: str = Field(default='这是一个默认的分块文本', description="分块文本内容", alias="text")
    enabled: bool = Field(default=True, description="分块是否启用")


class SearchChunkRequest(BaseModel):
    kb_ids: List[uuid.UUID] = Field(default=[], description="资产id", alias="kbIds")
    query: str = Field(default='', description="查询内容")
    top_k: int = Field(default=5, description="返回的结果数量", alias="topK")
    doc_ids: Optional[List[uuid.UUID]] = Field(default=None, description="文档id", alias="docIds")
    banned_ids: Optional[List[uuid.UUID]] = Field(default=[], description="禁止的分块id", alias="bannedIds")
    search_method: SearchMethod = Field(default=SearchMethod.KEYWORD_AND_VECTOR,
                                        description="检索方法", alias="searchMethod")
    is_related_surrounding: bool = Field(default=True, description="是否关联上下文", alias="isRelatedSurrounding")
    is_classify_by_doc: bool = Field(default=False, description="是否按文档分类", alias="isClassifyByDoc")
    is_rerank: bool = Field(default=False, description="是否重新排序", alias="isRerank")
    is_compress: bool = Field(default=False, description="是否压缩", alias="isCompress")
    tokens_limit: int = Field(default=8192, description="token限制", alias="tokensLimit")


class ListDatasetRequest(BaseModel):
    kb_id: uuid.UUID = Field(description="资产id", alias="kbId")
    dataset_id: Optional[uuid.UUID] = Field(default=None, description="数据集id", alias="datasetId")
    dataset_name: Optional[str] = Field(default=None, description="数据集名称", alias="datasetName")
    data_cnt_order: Optional[OrderType] = Field(default=OrderType.DESC, description="数据集数据数量", alias="dataCnt")
    llm_id: Optional[str] = Field(default=None, description="数据集使用的大模型id", alias="llmId")
    is_data_cleared: Optional[bool] = Field(default=None, description="数据集是否清洗", alias="isDataCleared")
    is_chunk_related: Optional[bool] = Field(default=None, description="数据集是否上下文关联", alias="isChunkRelated")
    generate_status: Optional[List[TaskStatus]] = Field(default=None, description="数据集生成状态", alias="generateStatus")
    score_order: Optional[OrderType] = Field(default=OrderType.DESC, description="数据集评分的排序方法", alias="scoreOrder")
    author_name: Optional[str] = Field(default=None, description="数据集创建者", alias="authorName")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class ListDataInDatasetRequest(BaseModel):
    dataset_id: uuid.UUID = Field(description="数据集id", alias="datasetId")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class CreateDatasetRequest(BaseModel):
    kb_id: uuid.UUID = Field(description="资产id", alias="kbId")
    dataset_name: str = Field(default='这是一个默认的数据集名称', description="测试数据集名称",
                              min_length=1, max_length=30, alias="datasetName")
    description: str = Field(default='', description="测试数据集简介", max_length=200)
    document_ids: List[uuid.UUID] = Field(default=[], description="测试数据集关联的文档", alias="documentIds")
    data_cnt: int = Field(default=64, alias="dataCnt", description="测试数据集内的数据数量", min=1, max=512)
    llm_id: str = Field(description="测试数据集使用的大模型id", alias="llmId")
    is_data_cleared: bool = Field(default=False, description="测试数据集是否进行清洗", alias="isDataCleared")
    is_chunk_related: bool = Field(default=False, description="测试数据集进行上下文关联", alias="isChunkRelated")


class UpdateDatasetRequest(BaseModel):
    dataset_name: str = Field(default='这是一个默认的数据集名称', description="测试数据集名称",
                              min_length=1, max_length=30, alias="datasetName")
    description: str = Field(default='', description="测试数据集简介", max_length=200)


class UpdateDataRequest(BaseModel):
    question: str = Field(default='这是一个默认的问题', description="问题",
                          min_length=1, max_length=200, alias="question")
    answer: str = Field(default='这是一个默认的答案', description="答案",
                        min_length=1, max_length=1000, alias="answer")


class ListTestingRequest(BaseModel):
    kb_id: uuid.UUID = Field(description="资产id", alias="kbId")
    testing_id: Optional[uuid.UUID] = Field(default=None, description="测试id", alias="testingId")
    testing_name: Optional[str] = Field(default=None, description="测试名称", alias="testingName")
    llm_id: Optional[str] = Field(default=None, description="测试使用的大模型id", alias="llmId")
    run_status: Optional[List[TaskStatus]] = Field(default=None, description="测试运行状态", alias="runStatus")
    scores_order: Optional[OrderType] = Field(default=OrderType.DESC, description="测试评分", alias="scoresOrder")
    author_name: Optional[str] = Field(default=None, description="测试创建者", alias="authorName")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class CreateTestingRequest(BaseModel):
    testing_name: str = Field(default='这是一个默认的测试名称', description="测试名称",
                              min_length=1, max_length=30, alias="testingName")
    description: str = Field(default='', description="测试简介", max_length=200)
    dataset_id: uuid.UUID = Field(description="测试数据集id", alias="datasetId")
    llm_id: str = Field(description="测试使用的大模型id", alias="llmId")
    search_method: SearchMethod = Field(default=SearchMethod.KEYWORD_AND_VECTOR,
                                        description="测试使用的检索方法", alias="searchMethod")
    top_k: int = Field(default=5, description="测试中检索方法关联的片段数量", alias="topK")


class UpdateTestingRequest(BaseModel):
    testing_name: str = Field(default='这是一个默认的测试名称', description="测试名称",
                              min_length=1, max_length=150, alias="testingName")
    description: str = Field(default='', description="测试简介", max_length=200)
    llm_id: str = Field(description="测试使用的大模型id", alias="llmId")
    search_method: SearchMethod = Field(default=SearchMethod.KEYWORD_AND_VECTOR,
                                        description="测试使用的检索方法", alias="searchMethod")
    top_k: int = Field(default=5, description="测试中检索方法关联的片段数量", alias="topK")


class ListRoleRequest(BaseModel):
    team_id: uuid.UUID = Field(description="团队id", alias="teamId")
    role_id: Optional[uuid.UUID] = Field(default=None, description="角色id", alias="roleId")
    role_name: Optional[str] = Field(default=None, description="角色名称", alias="roleName")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class CreateRoleRequest(BaseModel):
    role_name: str = Field(default='这是一个默认的角色名称', min_length=1, max_length=30, alias="roleName")
    actions: List[str] = Field(default=[], description="角色拥有的操作的列表", alias="actions")


class UpdateRoleRequest(BaseModel):
    role_name: str = Field(default='这是一个默认的角色名称', min_length=1, max_length=30, alias="roleName")
    actions: List[str] = Field(default=[], description="角色拥有的操作的列表", alias="actions")


class ListUserRequest(BaseModel):
    user_name: Optional[str] = Field(default=None, description="用户名", alias="userName")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")


class ListTaskRequest(BaseModel):
    team_id: uuid.UUID = Field(description="团队id", alias="teamId")
    task_id: Optional[uuid.UUID] = Field(default=None, description="任务id", alias="taskId")
    task_type: Optional[TaskType] = Field(default=None, description="任务类型", alias="taskType")
    task_status: Optional[TaskStatus] = Field(default=None, description="任务状态", alias="taskStatus")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=40, description="每页数量", alias="pageSize")
