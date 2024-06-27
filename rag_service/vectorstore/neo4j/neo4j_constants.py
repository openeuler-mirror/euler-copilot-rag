# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
EXTRACT_HUMAN_PROMPT = """
使用给定的格式从以下输入中提取信息：{{input}}

格式： {"nodes":[{"id": "openEuler","type":"操作系统"},{"id":"Linux_Kernel_5.10","type":"内核"}], "edges":[{"source":{"id": "openEuler","type":"操作系统"},"target":{"id":"Linux_Kernel_5.10","type":"内核"},"type":"基于"}]}

尽可能使用到输入信息里面的内容生成若干个问答对, 并根据提取到的图数据关系生成对应的cypher查询语句
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

EXTRACT_ENTITY_SYSTEM_PROMPT = """
# 实体词提取指南

## 1. 概述

你的任务是从用户输入当中提取实体词

**实体**: 实体通常指代具有唯一标识的逻辑对象, 或者具有特定意义的事物, 实体应当是有具体含义的, 而不是"人", "动物"这种抽象的词汇

实体包括但是不限制于以下类别:

- 人名: 真实的人物全名或者简称
- 组织机构: 公司, 学校, 政府机构, 非营利性组织等正式团体的全称
- 地理位置: 国家, 城市, 地区, 街道, 地标等地理实体
- 日期与时间: 具体的日期, 时刻, 时间段或者持续时间
- 数字于量词: 金额, 百分比, 数量, 度量单位等数值信息
- 产品与服务: 商品, 软件, 服务项目的名称以及详细规格
- 事件: 会议, 发布会, 竞赛, 展览等具体发生的活动
- 专有名词: 行业术语, 科学概念, 法律法规, 商标品牌等特定领域的专用词汇

## 2. 提取指南

- 深度理解文本: 全面理解文本内容, 把握其主题, 背景信息以及上下文关联性. 这有助于正确是被隐含或复杂的实体

- 细致扫描: 逐句逐字地仔细阅读文本, 留意可能包含实体的词汇, 短语和句子结构

- 避免冗余: 确保每个实体只会被提取一次, 对于重复出现的实体, 只需要在首次出现时提取即可, 同时确保提取的实体不包含任何无关字符或者多余的空格

- 处理复杂实体: 对于复合实体(如"openEuler社区的委员会主席是谁"), 需要去掉修饰词仅保留实体部分, 拆分后提取的实体为 ["委员会","主席"]

- 考虑上下文: 某些实体的含义可能随着上下文发生变化, 确保提取的实体与其在文本中的实际意义相符合, 避免因为脱离语境导致的理解错误

## 3. 返回格式

将提取到的所有实体以数组的形式返回, 例如["实体词1","实体词2"]
"""

NEO4J_ENTITY_SQL = """
match (n:Node) where n.id contains '{{entity}}'
return properties(n) as props
"""

NEO4J_EDGE_SQL = """
match (n:Node)-[r:{{entity}}]->(ne:Node)
return n.id + ' - ' + type(r) + ' -> ' + ne.id
"""

NEO4J_RELATIONSHIP_SQL = """
match (n:Node)-[r]->(ne:Node)
where n.id contains '{{entity}}'
return n.id + ' - ' + type(r) + ' -> ' + ne.id as output
union 
match (n:Node)<-[r]-(ne:Node)
where n.id contains '{{entity}}'
return ne.id + ' - ' + type(r) + ' -> ' + n.id as output
"""
