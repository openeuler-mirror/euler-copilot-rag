from typing import Any, Optional
import uuid
from pydantic import BaseModel, Field, validator, constr
from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.entities.common import DEFAULT_DOC_TYPE_ID


class ParseNode(BaseModel):
    """节点"""
    id: uuid.UUID = Field(..., description="节点ID")
    pre_id: Optional[uuid.UUID] = Field(None, description="父节点ID")
    title: Optional[str] = Field(None, description="节点标题")
    lv: int = Field(..., description="节点层级")
    parse_topology_type: ChunkParseTopology = Field(..., description="解析拓扑类型")
    text_feature: str = Field(default='', description="节点特征")
    vector: Optional[list[float]] = Field(default=None, description="节点向量")
    text: str = Field(default='', description="节点文本")
    content: Any = Field(..., description="节点内容")
    type: ChunkType = Field(..., description="节点类型")
    link_nodes: list = Field(..., description="链接节点")
    is_need_newline: bool = Field(default=False, description="是否需要换行")


class ParseResult(BaseModel):
    """解析结果"""
    parse_topology_type: DocParseRelutTopology = Field(..., description="解析拓扑类型")
    nodes: list[ParseNode] = Field(..., description="节点列表")
