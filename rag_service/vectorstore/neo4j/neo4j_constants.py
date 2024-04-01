# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
EXTRACT_ENTITY_SYSTEM_PROMPT = """
# 知识图谱构建指南

## 1. 概述
您是一个专门从结构化格式中提取信息以构建知识图谱的顶级算法专家。
在保证准确性的情况下，尽可能多地从文本中提取信息，不得添加文本中未明确提及的任何信息。
- **节点**代表实体和概念。
- 目标是使知识图谱实现简洁清晰，使之易于广大受众理解。

## 2. 节点标注
- **一致性**：确保使用已有的类型为节点标签。
确保使用基本或初级类型作为节点标签。
- 例如，当识别出代表人物的实体时，始终将其标记为 **"人物"**。避免使用"数学家"或"科学家"等更为具体的术语
- **节点ID**：切勿使用整数作为节点ID。节点ID应为文本中出现的名称或可读标识符。
- **关系**表示实体或概念之间的联系。
构建知识图谱时，确保关系类型的连贯性和通用性。不要使用"成为专家"这类特定且瞬时的关系类型，而应使用"专家"等更为通用且持久的关系类型。务必使用通用且持久的关系类型！

## 3. 共指消解
- **保持实体一致性**：在提取实体时，确保其一致性至关重要。

如果一个实体（如"John Joe"）在文本中多次被提及，但通过不同的名字或代词（如"Joe"、"他"）来指代，那么在整个知识图谱中始终使用该实体最完整的标识符。
在此例中，使用"John Joe"作为实体ID。

请记住，知识图谱应具有连贯性且易于理解，因此保持实体引用的一致性至关重要。

## 4. 严格遵守
严格遵守规则，否则将导致终止运行。
"""

EXTRACT_HUMAN_PROMPT = """
提示：确保按照正确的格式作答，且不包含任何解释。使用给定的格式从以下输入中提取信息：{{input}}

格式： {"nodes":[{"id": "openEuler","type":"操作系统"},{"id":"Linux_Kernel_5.10","type":"内核"}], "edges":[{"source":{"id": "openEuler","type":"操作系统"},"target":{"id":"Linux_Kernel_5.10","type":"内核"},"type":"基于"}]}
"""

GENERATE_CYPHER_SYSTEM_PROMPT = """
根据以下Neo4j schema，编写一个Cypher查询语句以回答用户的问题。仅返回Cypher查询语句，不包括反引号，不包含其他内容。
{{schema}}

openEuler常见的组织机构有: openEuler委员会, openEuler顾问专家委员会, openEuler品牌委员会, openEuler技术委员会, openEuler用户委员会

以下是一些示例：
示例1:
问题: 顾问专家委员的主席是谁
Cypher: match (p:人物)-[r:主席]->(po:组织机构 {id:'openEuler委员会'}) return p.id

示例2:
问题: 执行秘书是谁
Cypher: match (p:人物)-[r:执行秘书]->() return p.id

示例3:
问题: 在常务委员会成员里面, 谁在中国科学院软件研究所参加工作
Cypher: match (p:人物)-[r:就职于]->(po:组织机构 {id:'中国科学院软件研究所'}) return p.id

示例4:
问题: 运维管理平台包含哪些功能模块
Cypher: match (n:运维管理平台)-[r:包含]->(p:功能模块) return p.id

示例5:
问题: PilotGo的日志审计功能模块追踪了那些内容
Cypher: match (n)-[r:包含]->(f:功能模块)-[r2:追踪]->(f2) where n.id contains 'PilotGo' and f.id contains '日志审计' return f2.id
"""
