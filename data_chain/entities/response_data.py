# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

from typing import Any, Optional

from pydantic import BaseModel, Field
import uuid

from data_chain.entities.enum import (
    TeamType,
    ActionType,
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


class ResponseData(BaseModel):
    """基础返回数据结构"""

    code: int = Field(default=200, description="返回码")
    message: str = Field(default="", description="返回信息")
    result: Any


class Team(BaseModel):
    """团队信息"""
    team_id: uuid.UUID = Field(description="团队ID", alias="teamId")
    team_name: str = Field(min_length=1, max_length=30, description="团队名称", alias="teamName")
    description: str = Field(max_length=150, description="团队描述")
    author_name: str = Field(description="团队创建者的用户ID", alias="authorName")
    member_cnt: int = Field(description="团队成员数量", alias="memberCount")
    is_public: bool = Field(description="是否为公开团队", alias="isPublic")
    created_time: str = Field(description="团队创建时间", alias="createdTime")


class ListTeamMsg(BaseModel):
    """GET /team 数据结构"""
    total: int = Field(default=0, description="总数")
    teams: list[Team] = Field(default=[], description="团队列表")


class ListTeamResponse(ResponseData):
    """GET /team 响应"""

    result: ListTeamMsg = Field(default=ListTeamMsg(), description="团队列表数据结构")


class TeamUser(BaseModel):
    """团队成员信息"""
    user_id: uuid.UUID = Field(description="用户ID", alias="userId")
    user_name: str = Field(description="用户名", alias="userName")
    role_name: str = Field(description="角色名称", alias="roleName")


class ListTeamUserMsg(BaseModel):
    """GET /team/usr 数据结构"""
    total: int = Field(default=0, description="总数")
    team_users: list[TeamUser] = Field(default=[], description="团队成员列表", alias="teamUsers")


class ListTeamUserResponse(ResponseData):
    result: ListTeamUserMsg = Field(default=ListTeamUserMsg(), description="团队成员列表数据结构")


class TeamMsg(BaseModel):
    """团队信息"""
    msg_id: uuid.UUID = Field(description="消息ID", alias="msgId")
    author_name: str = Field(description="消息发送者的用户名", alias="authorName")
    message: str = Field(description="消息内容")


class ListTeamMsgMsg(BaseModel):
    """GET /team/msg 数据结构"""
    total: int = Field(default=0, description="总数")
    team_msgs: list[TeamMsg] = Field(default=[], description="团队消息列表", alias="teamMsgs")


class ListTeamMsgResponse(ResponseData):
    result: ListTeamMsgMsg = Field(default=ListTeamMsgMsg(), description="团队消息列表数据结构")


class CreateTeamResponse(ResponseData):
    """POST /team 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="团队ID")


class InviteTeamUserResponse(ResponseData):
    """POST /team/invitation 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="邀请ID")


class JoinTeamResponse(ResponseData):
    """POST /team/application 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="申请ID")


class UpdateTeamResponse(ResponseData):
    """PUT /team 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="团队ID")


class UpdateTeamUserRoleResponse(ResponseData):
    """PUT /team/usr 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="团队成员ID")


class UpdateTeamAuthorResponse(ResponseData):
    """PUT /team/author 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="团队ID")


class DeleteTeamResponse(ResponseData):
    """DELETE /team 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="团队ID")


class DeleteTeamUserResponse(ResponseData):
    """DELETE /team/usr 响应"""
    result: list[uuid.UUID] = Field(default=[], description="团队成员ID列表")


class DocumentType(BaseModel):
    """文档类型信息"""
    doc_type_id: uuid.UUID = Field(description="文档类型ID", alias="docTypeId")
    doc_type_name: str = Field(description="文档类型名称", alias="docTypeName")


class Knowledgebase(BaseModel):
    """知识库信息"""
    kb_id: uuid.UUID = Field(description="知识库ID", alias="kbId")
    kb_name: str = Field(description="知识库名称", min=1, max=20, alias="kbName")
    author_name: str = Field(description="知识库创建者的用户名", alias="authorName")
    tokenizer: Tokenizer = Field(description="分词器", alias="tokenizer")
    embedding_model: str = Field(description="嵌入模型", alias="embeddingModel")
    description: str = Field(description="知识库描述", max=150)
    doc_cnt: int = Field(description="知识库文档数量", alias="docCnt")
    doc_size: int = Field(description="知识库文档大小", alias="docSize")
    upload_count_limit: int = Field(description="知识库单次文件上传数量限制", alias="uploadCountLimit")
    upload_size_limit: int = Field(description="知识库单次文件上传大小限制", alias="uploadSizeLimit")
    default_parse_method: ParseMethod = Field(description="默认解析方法", alias="defaultParseMethod")
    default_chunk_size: int = Field(description="默认分块大小", alias="defaultChunkSize")
    created_time: str = Field(description="知识库创建时间", alias="createdTime")
    doc_types: list[DocumentType] = Field(default=[], description="知识库文档类型列表", alias="docTypes")


class TeamKnowledgebase(BaseModel):
    """团队知识库信息"""
    team_id: uuid.UUID = Field(description="团队ID", alias="teamId")
    team_name: str = Field(description="团队名称", alias="teamName")
    kb_list: list[Knowledgebase] = Field(default=[], description="知识库列表", alias="kbList")


class ListAllKnowledgeBaseMsg(BaseModel):
    """GET /kb 数据结构"""
    team_knowledge_bases: list[TeamKnowledgebase] = Field(default=[], description="团队知识库列表", alias="teamKnowledgebases")


class ListAllKnowledgeBaseResponse(ResponseData):
    """GET /kb 响应"""
    result: ListAllKnowledgeBaseMsg = Field(default=ListAllKnowledgeBaseMsg(), description="团队知识库列表数据结构")


class ListKnowledgeBaseMsg(BaseModel):
    total: int = Field(default=0, description="总数")
    kb_list: list[Knowledgebase] = Field(default=[], description="知识库列表数据结构", alias="kbList")


class ListKnowledgeBaseResponse(ResponseData):
    """GET /kb/team 响应"""
    result: ListKnowledgeBaseMsg = Field(ListKnowledgeBaseMsg())


class ListDocumentTypesResponse(ResponseData):
    """GET /kb/doc_type 响应"""
    result: list[DocumentType] = Field(default=[], description="文档类型列表数据结构")


class Task(BaseModel):
    """任务信息"""
    op_id: uuid.UUID = Field(description="关联实体ID", alias="opId")
    op_name: str = Field(description="关联实体的名称", alias="opName")
    task_id: uuid.UUID = Field(description="任务ID", alias="taskId")
    task_status: TaskStatus = Field(description="任务状态", alias="taskStatus")
    task_type: TaskType = Field(description="任务类型", alias="taskType")
    task_completed: float = Field(description="任务完成度", alias="taskCompleted")
    finished_time: Optional[str] = Field(default=None, description="任务完成时间", alias="finishedTime")
    created_time: str = Field(description="任务创建时间", alias="createdTime")


class CreateKnowledgeBaseResponse(ResponseData):
    """POST /kb 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="知识库ID")


class ImportKnowledgeBaseResponse(ResponseData):
    """POST /kb/import 响应"""
    result: list[uuid.UUID] = Field(default=[], description="任务ID")


class ExportKnowledgeBaseResponse(ResponseData):
    """POST /kb/export 响应"""
    result: list[uuid.UUID] = Field(default=[], description="任务ID")


class UpdateKnowledgeBaseResponse(ResponseData):
    """PUT /kb 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="知识库ID")


class DeleteKnowledgeBaseResponse(ResponseData):
    """DELETE /kb 响应"""
    result: list[uuid.UUID] = Field(default=[], description="知识库ID列表")


class Document(BaseModel):
    """文档信息"""
    doc_id: uuid.UUID = Field(description="文档ID", alias="docId")
    doc_name: str = Field(description="文档名称", alias="docName")
    doc_type: DocumentType = Field(description="文档类型", alias="docType")
    chunk_size: int = Field(description="文档分片大小", alias="chunkSize")
    created_time: str = Field(description="文档创建时间", alias="createdTime")
    parse_task: Optional[Task] = Field(default=None, description="文档任务", alias="docTask")
    parse_method: ParseMethod = Field(description="文档解析方法", alias="parseMethod")
    enabled: bool = Field(description="文档是否启用", alias="enabled")
    author_name: str = Field(description="文档创建者的用户名", alias="authorName")
    status: DocumentStatus = Field(description="文档状态", alias="status")


class ListDocumentMsg(BaseModel):
    """GET /doc 数据结构"""
    total: int = Field(default=0, description="总数")
    documents: list[Document] = Field(default=[], description="文档列表", alias="documents")


class ListDocumentResponse(ResponseData):
    """GET /doc 响应"""
    result: ListDocumentMsg = Field(default=ListDocumentMsg(), description="文档列表数据结构")


class GetDocumentReportResponse(ResponseData):
    """GET /doc/report 响应"""
    result: str = Field(default="", description="文档报告数据结构")


class UploadDocumentResponse(ResponseData):
    """POST /doc 响应"""
    result: list[uuid.UUID] = Field(default=[], description="文档ID列表")


class ParseDocumentResponse(ResponseData):
    """POST /doc/parse 响应"""
    result: list[uuid.UUID] = Field(default=[], description="文档ID列表")


class UpdateDocumentResponse(ResponseData):
    """PUT /doc 响应"""
    result: uuid.UUID = Field(default=None, description="文档ID")


class DeleteDocumentResponse(ResponseData):
    """DELETE /doc 响应"""
    result: list[uuid.UUID] = Field(default=[], description="文档ID列表")


class Chunk(BaseModel):
    """文档分片信息"""
    chunk_id: uuid.UUID = Field(description="分片ID", alias="chunkId")
    chunk_type: ChunkType = Field(description="分片类型", alias="chunkType")
    text: str = Field(description="分片文本")


class ListChunkMsg(BaseModel):
    """GET /chunk 数据结构"""
    total: int = Field(default=0, description="总数")
    chunks: list[Chunk] = Field(default=[], description="分片列表", alias="chunks")


class ListChunkResponse(ResponseData):
    """GET /chunk 响应"""
    result: ListChunkMsg = Field(default=ListChunkMsg(), description="分片列表数据结构")


class UpdateChunkResponse(ResponseData):
    """PUT /chunk 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="分片ID")


class UpdateChunkEnabledResponse(ResponseData):
    """PUT /chunk 响应"""
    result: list[uuid.UUID] = Field(default=[], description="分片ID列表")


class DocChunk(BaseModel):
    """Post /chunk/search 数据结构"""
    doc_id: uuid.UUID = Field(description="文档ID", alias="docId")
    doc_name: str = Field(description="文档名称", alias="docName")
    chunks: list[Chunk] = Field(default=[], description="分片列表", alias="chunks")


class SearchChunkMsg(BaseModel):
    """Post /chunk/search 数据结构"""
    doc_chunks: list[DocChunk] = Field(default=[], description="文档分片列表", alias="docChunks")


class SearchChunkResponse(ResponseData):
    """POST /chunk/search 响应"""
    result: SearchChunkMsg = Field(default=SearchChunkMsg(), description="文档分片列表数据结构")


class LLM(BaseModel):
    llm_id: str = Field(description="大模型ID", alias="llmId")
    llm_name: str = Field(description="大模型名称", min=1, max=20, alias="llmName")
    llm_icon: str = Field(description="大模型图标", alias="llmIcon")


class Dataset(BaseModel):
    """数据集信息"""
    dataset_id: uuid.UUID = Field(description="数据集ID", alias="datasetId")
    dataset_name: str = Field(description="数据集名称", min=1, max=20, alias="datasetName")
    description: str = Field(description="数据集描述", max=150)
    data_cnt: int = Field(description="数据集数据数量", alias="dataCnt")
    is_data_cleared: bool = Field(default=False, description="数据集是否进行清洗", alias="isDataCleared")
    is_chunk_related: bool = Field(default=False, description="数据集进行上下文关联", alias="isChunkRelated")
    is_imported: bool = Field(default=False, description="数据集是否导入", alias="isImported")
    llm: Optional[LLM] = Field(default=None, description="生成数据集使用的大模型信息", alias="llm")
    generate_task: Optional[Task] = Field(default=None, description="数据集生成任务", alias="generateTask")
    score: Optional[float] = Field(description="数据集评分", default=None)
    author_name: str = Field(description="数据集创建者的用户名", alias="authorName")
    status: DataSetStatus = Field(description="数据集状态", alias="status")


class ListDatasetMsg(BaseModel):
    """GET /dataset 数据结构"""
    total: int = Field(default=0, description="总数")
    datasets: list[Dataset] = Field(default=[], description="数据集列表", alias="datasets")


class ListDatasetResponse(ResponseData):
    """GET /dataset 响应"""
    result: ListDatasetMsg = Field(default=ListDatasetMsg(), description="数据集列表数据结构")


class Data(BaseModel):
    data_id: uuid.UUID = Field(description="数据ID", alias="dataId")
    doc_name: str = Field(description="数据关联的文档名称", alias="docName")
    question: str = Field(description="数据的问题")
    answer: str = Field(description="数据的答案")
    chunk: str = Field(description="数据的片段")
    chunk_type: ChunkType = Field(description="数据的片段类型", alias="chunkType")


class ListDataInDatasetMsg(BaseModel):
    """GET /dataset/data 数据结构"""
    total: int = Field(default=0, description="总数")
    datas: list[Data] = Field(default=[], description="数据列表", alias="datas")


class ListDataInDatasetResponse(ResponseData):
    """GET /dataset/data 响应"""
    result: ListDataInDatasetMsg = Field(default=ListDataInDatasetMsg(), description="数据列表数据结构")


class IsDatasetHaveTestingResponse(ResponseData):
    """GET /dataset/testing/exist 响应"""
    result: bool = Field(default=False, description="数据集是否有测试任务")


class ListDatasetTaskResponse(ResponseData):
    """GET /dataset/task 响应"""
    result: list[Task] = Field(default=[], description="数据集任务列表数据结构")


class CreateDatasetResponse(ResponseData):
    """POST /dataset 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="数据集生成任务ID")


class ImportDatasetResponse(ResponseData):
    """POST /dataset/import 响应"""
    result: list[uuid.UUID] = Field(default=[], description="任务ID列表")


class ExportDatasetResponse(ResponseData):
    """POST /dataset/export 响应"""
    result: list[uuid.UUID] = Field(default=[], description="任务ID列表")


class GenerateDatasetResponse(ResponseData):
    """POST /dataset/generate 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="数据集ID")


class UpdateDatasetResponse(ResponseData):
    """PUT /dataset 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="数据集ID")


class UpdateDataResponse(ResponseData):
    """PUT /dataset/data 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="数据ID")


class DeleteDatasetResponse(ResponseData):
    """DELETE /dataset 响应"""
    result: list[uuid.UUID] = Field(default=[], description="数据集ID列表")


class DeleteDataResponse(ResponseData):
    """DELETE /dataset/data 响应"""
    result: list[uuid.UUID] = Field(default=[], description="数据ID列表")


class Testing(BaseModel):
    """测试信息"""
    testing_id: uuid.UUID = Field(description="测试ID", alias="testingId")
    testing_name: str = Field(description="测试名称", min=1, max=20, alias="testingName")
    description: str = Field(description="测试描述", max=150)
    llm: Optional[LLM] = Field(default=None, description="测试使用的大模型信息", alias="llm")
    search_method: SearchMethod = Field(description="搜索方法", alias="searchMethod")
    testing_task: Optional[Task] = Field(default=None, description="测试任务", alias="testingTask")
    ave_score: float = Field(default=-1, description="综合得分", alias="aveScore")
    ave_pre: float = Field(default=-1, description="精确率", alias="avePre")   # 精确度
    ave_rec: float = Field(default=-1, description="召回率", alias="aveRec")  # 召回率
    ave_fai: float = Field(default=-1, description="忠实值", alias="aveFai")  # 忠实值
    ave_rel: float = Field(default=-1, description="可解释性", alias="aveRel")  # 可解释性
    ave_lcs: float = Field(default=-1, description="最长公共子串得分", alias="aveLcs")  # 最长公共子序列得分
    ave_leve: float = Field(default=-1, description="编辑距离得分", alias="aveLeve")  # 编辑距离得分
    ave_jac: float = Field(default=-1, description="杰卡德相似系数", alias="aveJac")  # 杰卡德相似系数
    author_name: str = Field(description="测试创建者的用户名", alias="authorName")
    topk: int = Field(description="检索到的片段数量", alias="topk")
    status: TestingStatus = Field(description="测试状态", alias="status")


class DatasetTesting(BaseModel):
    """数据集测试信息"""
    dataset_id: uuid.UUID = Field(description="数据集ID", alias="datasetId")
    dataset_name: str = Field(description="数据集名称", alias="datasetName")
    testings: list[Testing] = Field(default=[], description="测试列表", alias="testings")


class ListTestingMsg(BaseModel):
    """GET /testing 数据结构"""
    total: int = Field(default=0, description="总数")
    dataset_testings: list[DatasetTesting] = Field(default=[], description="数据集测试列表", alias="datasetTestings")


class ListTestingResponse(ResponseData):
    """GET /testing 响应"""
    result: ListTestingMsg = Field(default=ListTestingMsg(), description="测试列表数据结构")


class TestCase(BaseModel):
    """测试用例信息"""
    test_case_id: uuid.UUID = Field(description="测试用例ID", alias="testCaseId")
    question: str = Field(description="问题")
    answer: str = Field(description="标准答案")
    llm_answer: str = Field(description="大模型的回答", alias="llmAnswer")
    related_chunk: str = Field(description="检索到的片段", alias="relatedChunk")
    doc_name: str = Field(description="来源文档", alias="docName")
    score: float = Field(description="综合得分")
    pre: float = Field(description="精确率")   # 精确度
    rec: float = Field(description="召回率")  # 召回率
    fai: float = Field(description="忠实值")  # 忠实值
    rel: float = Field(description="可解释性")  # 可解释性
    lcs: float = Field(description="最长公共子串得分")  # 最长公共子序列得分
    leve: float = Field(description="编辑距离得分")  # 编辑距离得分
    jac: float = Field(description="杰卡德相似系数")  # 杰卡德相似系数


class TestingTestCase(BaseModel):
    """GET /testing/testcase 数据结构"""
    ave_score: float = Field(default=-1, description="平均综合得分", alias="aveScore")
    ave_pre: float = Field(default=-1, description="平均精确率", alias="avePre")
    ave_rec: float = Field(default=-1, description="平均召回率", alias="aveRec")
    ave_fai: float = Field(default=-1, description="平均忠实值", alias="aveFai")
    ave_rel: float = Field(default=-1, description="平均可解释性", alias="aveRel")
    ave_lcs: float = Field(default=-1, description="平均最长公共子串得分", alias="aveLcs")
    ave_leve: float = Field(default=-1, description="平均编辑距离得分", alias="aveLeve")
    ave_jac: float = Field(default=-1, description="平均杰卡德相似系数", alias="aveJac")
    total: int = Field(default=0, description="总数")
    test_cases: list[TestCase] = Field(default=[], description="测试用例列表", alias="testCases")


class ListTestCaseResponse(ResponseData):
    """GET /testing/testcase 响应"""
    result: TestingTestCase = Field(default=TestingTestCase(), description="测试用例列表数据结构")


class CreateTestingResponsing(ResponseData):
    """POST /testing 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="测试ID")


class RunTestingResponse(ResponseData):
    """POST /testing/run 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="测试ID")


class UpdateTestingResponse(ResponseData):
    """PUT /testing 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="测试ID")


class DeleteTestingResponse(ResponseData):
    """DELETE /testing 响应"""
    result: list[uuid.UUID] = Field(default=[], description="测试ID列表")


class action(BaseModel):
    """操作信息"""
    action_name: str = Field(description="操作名称", min=1, max=20, alias="actionName")
    action: str = Field(description="操作", min=1, max=20)
    is_used: bool = Field(description="是否启用", alias="isUsed")


class TypeAction(BaseModel):
    """不同类别的类别操作"""
    action_type: ActionType = Field(description="操作类型", alias="actionType")
    actions: list[action] = Field(default=[], description="操作列表", alias="actions")


class ListActionMsg(BaseModel):
    """GET /role/action 数据结构"""
    type_actions: list[TypeAction] = Field(default=[], description="操作类型列表", alias="actionTypes")


class ListActionResponse(ResponseData):
    result: ListActionMsg = Field(default=ListActionMsg(), description="操作列表数据结构")


class role(BaseModel):
    """角色信息"""
    role_id: uuid.UUID = Field(description="角色ID", alias="roleId")
    role_name: str = Field(description="角色名称", min=1, max=20, alias="roleName")
    type_actions: list[TypeAction] = Field(default=[], description="操作类型列表", alias="typeActions")


class ListRoleMsg(BaseModel):
    """GET /role 数据结构"""
    roles: list[role] = Field(default=[], description="角色列表", alias="roles")


class ListRoleResponse(ResponseData):
    """GET /role 响应"""
    result: ListRoleMsg = Field(default=ListRoleMsg(), description="角色列表数据结构")


class CreateRoleResponse(ResponseData):
    """POST /role 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="角色ID")


class UpdateRoleResponse(ResponseData):
    """PUT /role 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="角色ID")


class DeleteRoleResponse(ResponseData):
    """DELETE /role 响应"""
    result: list[uuid.UUID] = Field(default=[], description="角色ID列表")


class UserMsg(BaseModel):
    """用户消息"""
    team_id: uuid.UUID = Field(description="团队ID", alias="teamId")
    msg_id: uuid.UUID = Field(description="消息ID", alias="msgId")
    sender_id: uuid.UUID = Field(description="发送者ID", alias="senderId")
    sender_name: str = Field(description="发送者名称", alias="senderName")
    receiver_id: uuid.UUID = Field(description="接收者ID", alias="receiverId")
    receiver_name: str = Field(description="接收者名称", alias="receiverName")
    msg_type: UserMessageType = Field(description="消息类型", alias="msgType")
    msg_status: UserMessageStatus = Field(description="消息状态", alias="msgStatus")
    created_time: str = Field(description="创建时间", alias="createdTime")


class ListUserMessageMsg(BaseModel):
    """GET /usr_msg 数据结构"""
    total: int = Field(default=0, description="总数")
    user_messages: list[UserMsg] = Field(default=[], description="用户消息列表", alias="userMessages")


class ListUserMessageResponse(ResponseData):
    result: ListUserMessageMsg = Field(default=ListUserMessageMsg(), description="用户消息列表数据结构")


class UpdateUserMessageResponse(ResponseData):
    """PUT /usr_msg 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="消息ID")


class DeleteUserMessageResponse(ResponseData):
    """DELETE /usr_msg 响应"""
    result: list[uuid.UUID] = Field(default=[], description="消息ID列表")


class User(BaseModel):
    """用户数据结构"""
    user_sub: str = Field(description="用户id")
    user_name: str = Field(description="用户名称")


class ListUserMsg(BaseModel):
    """GET /user 数据结构"""
    users: list[User] = Field(default=[], description="用户列表")


class ListUserResponse(ResponseData):
    result: ListUserMsg = Field(ListUserMsg(), description="大模型列表数据结构")


class ListLLMMsg(BaseModel):
    """GET /other/llm 数据结构"""
    llms: list[LLM] = Field(default=[], description="大模型列表", alias="llms")


class ListLLMResponse(ResponseData):
    """GET /other/llm 响应"""
    result: ListLLMMsg = Field(default=ListLLMMsg(), description="大模型列表数据结构")


class Entity(BaseModel):
    name: str = Field(description="实体名称")
    description: str = Field(description="实体描述")


class ListEmbeddingResponse(ResponseData):
    """GET /other/embedding 数据结构"""
    result: list[str] = Field(default=[], description="向量化模型的列表数据结构")


class ListTokenizerResponse(ResponseData):
    """GET /other/tokenizer 响应"""
    result: list[str] = Field(default=[], description="分词器的列表数据结构")


class ListParseMethodResponse(ResponseData):
    """"GET /other/parse_method 响应"""
    result: list[str] = Field(default=[], description="解析方法的列表数据结构")


class ListSearchMethodResponse(ResponseData):
    """GET /other/search_method 响应"""
    result: list[str] = Field(default=[], description="搜索方法的列表数据结构")


class ListTaskMsg(BaseModel):
    """GET /task 数据结构"""
    total: int = Field(default=0, description="总数")
    tasks: list[Task] = Field(default=[], description="任务列表", alias="tasks")


class ListTaskResponse(ResponseData):
    """GET /task 响应"""
    result: ListTaskMsg = Field(default=ListTaskMsg(), description="任务列表数据结构")


class GetTaskReportResponse(ResponseData):
    """GET /task/report 响应"""
    result: str = Field(default='', description="任务报告")


class DeleteTaskByIdResponse(ResponseData):
    """DELETE /task/one 响应"""
    result: Optional[uuid.UUID] = Field(default=None, description="任务ID")


class DeleteTaskByTypeResponse(ResponseData):
    """DELETE /task/all 响应"""
    result: list[uuid.UUID] = Field(default=[], description="任务ID列表")
