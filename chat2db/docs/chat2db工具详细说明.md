# 1. 背景说明
工具聚焦于利用大模型能力智能生成SQL语句，查询数据库数据，为最终的模型拟合提供能力增强。工具可增强RAG多路召回能力，增强RAG对本地用户的数据适应性，同时对于服务器、硬件型号等关键字场景，在不训练模型的情况下，RAG也具备一定检索能力

# 2. 工具设计框架
## 2.1 目录结构
```
chat2db
|-- app                                   # 应用主入口及相关功能模块
|-- |-- app.py                            # 服务请求入口，处理用户请求并返回结果
|-- |-- __init__.py                       # 初始化
|-- |                                       
|-- |-- base                              # 基础功能模块
|-- |-- |-- ac_automation.py              # AC 自动机
|-- |-- |-- mysql.py                      # MySQL 数据库操作封装
|-- |-- |-- postgres.py                   # PostgreSQL 数据库操作封装
|-- |-- |-- vectorize.py                  # 数据向量化处理模块
|-- |                                     
|-- |-- router                            # 路由模块，负责分发请求到具体服务
|-- |-- |-- database.py                   # 数据库相关路由逻辑
|-- |-- |-- sql_example.py                # SQL 示例管理路由
|-- |-- |-- sql_generate.py               # SQL 生成相关路由
|-- |-- |-- table.py                      # 表信息管理路由
|-- |                                     
|-- |-- service                           # 核心服务模块
|-- |-- |-- diff_database_service.py      # 不同数据库类型的服务适配
|-- |-- |-- keyword_service.py            # 关键字检索服务
|-- |-- |-- sql_generate_service.py       # SQL 生成服务逻辑
|
|-- common                                # 公共资源及配置
|-- |-- .env                              # 环境变量配置文件
|-- |-- init_sql_example.py               # 初始化 SQL 示例数据脚本
|-- |-- table_name_id.yaml                # 表名与 ID 映射配置
|-- |-- table_name_sql_example.yaml       # 表名与 SQL 示例映射配置
|
|-- config                                # 配置模块
|-- |-- config.py                         # 工具全局配置文件
|
|-- database                              # 数据库相关模块
|-- |-- postgres.py                       # PostgreSQL 数据库连接及操作封装
|
|-- llm                                   # 大模型交互模块
|-- |-- chat_with_model.py                # 与大模型交互的核心逻辑
|
|-- manager                               # 数据管理模块
|-- |-- column_info_manager.py            # 列信息管理逻辑
|-- |-- database_info_manager.py          # 数据库信息管理逻辑
|-- |-- sql_example_manager.py            # SQL 示例管理逻辑
|-- |-- table_info_manager.py             # 表信息管理逻辑
|
|-- model                                 # 数据模型模块
|-- |-- request.py                        # 请求数据模型定义
|-- |-- response.py                       # 响应数据模型定义
|
|-- scripts                               # 脚本工具模块
|-- |-- chat2db_config                    # 工具配置相关脚本
|-- |-- |-- config.yaml                   # 工具配置文件模板
|-- |-- output_example                    # 输出示例相关脚本
|-- |-- |-- output_examples.txt           # 输出示例文件
|-- |-- run_chat2db.py                    # 启动工具进行交互的主脚本
|
|-- security                              # 安全模块
|-- |-- security.py                       # 安全相关逻辑（如权限校验、加密等）
|
|-- template                              # 模板及提示词相关模块
|-- |-- change_txt_to_yaml.py             # 将文本提示转换为 YAML 格式的脚本
|-- |-- prompt.yaml                       # 提示词模板文件，用于生成 SQL 或问题
```
# 3. 主要功能介绍
## **3.1 智能生成 SQL 查询**
- **功能描述**：
  - 工具的核心功能是利用大模型（如 LLM）智能生成符合用户需求的 SQL 查询语句。
  - 用户可以通过自然语言提问，工具会根据问题内容、表结构、示例数据等信息生成对应的 SQL 查询。
- **实现模块**：
  - **路由模块**：`router/sql_generate.py` 负责接收用户请求并调用相关服务。
  - **服务模块**：`service/sql_generate_service.py` 提供 SQL 生成的核心逻辑。
  - **提示词模板**：`template/prompt.yaml` 中定义了生成 SQL 的提示词模板。
  - **数据库适配**：`base/postgres.py` 和 `base/mysql.py` 提供不同数据库的操作封装。
- **应用场景**：
  - 用户无需掌握复杂的 SQL 语法，只需通过自然语言即可完成查询。
  - 支持多种数据库类型（如 PostgreSQL 和 MySQL）

---

## **3.2 关键字检索与多路召回**
- **功能描述**：
  - 工具支持基于关键字的检索功能，增强 RAG 的多路召回能力。
  - 对于服务器、硬件型号等特定场景，即使未训练模型，也能通过关键字匹配快速检索相关数据。
- **实现模块**：
  - **路由模块**：`router/keyword.py` 负责处理关键字检索请求。
  - **服务模块**：`service/keyword_service.py` 提供关键字检索的核心逻辑。
  - **AC 自动机**：`base/ac_automation.py` 实现高效的多模式字符串匹配。
- **应用场景**：
  - 在不依赖大模型的情况下，快速检索与关键字相关的 SQL 示例或表信息。
  - 适用于硬件型号、服务器配置等特定场景的快速查询。

---

## **3.3 数据库表与列信息管理**
- **功能描述**：
  - 工具提供对数据库表和列信息的管理功能，包括元数据存储、查询和更新。
  - 用户可以通过工具查看表结构、列注释等信息，并将其用于 SQL 查询生成。
- **实现模块**：
  - **路由模块**：`router/table.py` 负责表信息相关的请求分发。
  - **管理模块**：
    - `manager/table_info_manager.py`：管理表信息。
    - `manager/column_info_manager.py`：管理列信息。
  - **数据模型**：`model/request.py` 和 `model/response.py` 定义了表和列信息的数据结构。
- **应用场景**：
  - 用户可以快速了解数据库的表结构，辅助生成更准确的 SQL 查询。
  - 支持动态更新表和列信息，适应本地数据的变化。

---

## **3.4 SQL 示例管理**
- **功能描述**：
  - 工具支持对 SQL 示例的增删改查操作，并结合向量相似度检索最相关的 SQL 示例。
  - 用户可以通过问题向量找到与当前问题最相似的历史 SQL 示例，从而加速查询生成。
- **实现模块**：
  - **路由模块**：`router/sql_example.py` 负责 SQL 示例相关的请求分发。
  - **管理模块**：`manager/sql_example_manager.py` 提供 SQL 示例的管理逻辑。
  - **向量化处理**：`base/vectorize.py` 将问题文本转换为向量表示。
  - **余弦距离排序**：利用 PostgreSQL 的向量计算能力，按余弦距离排序检索最相似的 SQL 示例。
- **应用场景**：
  - 在生成新 SQL 查询时，参考历史 SQL 示例，提高查询的准确性和效率。
  - 支持对 SQL 示例的灵活管理，便于维护和扩展。

# 4. 工具使用

## 4.1 服务启动与配置

### 服务环境配置

- 在common/.env文件中配置数据库连接信息，大模型API密钥等必要参数

### 数据库配置

```bash
# 进行数据库初始化，例如
postgres=# CREATE EXTENSION zhparser;
postgres=# CREATE EXTENSIONpostgres=# CREATE EXTENSION vector;
postgres=# CREATE TEXT SEARCH CONFIGURATION zhparser (PARSER = zhparser);
postgres=# ALTER TEXT SEARCH CONFIGURATION zhparser ADD MAPPING FOR n,v,a,i,e,l WITH simple;
postgres=# exit
```

### 启动服务

```bash
# 读取.env 环境配置，app.py入口启动服务
python3 chat2db/app/app.py
# 配置run_chat2db.py端口
python3 chat2db/scripts/run_chat2db.py config --ip xxx --port xxx
```

---

## 4.2 命令行工具操作指南

### 1. 数据库操作

#### 添加数据库
```bash
python3 run_chat2db.py add_db --database_url "postgresql+psycopg2://user:password@localhost:5444/mydb"

# 成功返回示例
>> success
>> database_id: 27fa7fd3-949b-41f9-97bc-530f498c0b57
```

#### 删除数据库

```bash
python3 run_chat2db.py del_db --database_id mydb_database_id
```

#### 查询已配置数据库

```bash
python3 run_chat2db.py query_db

# 返回示例
----------------------------------------
查询数据库配置成功
----------------------------------------
database_id: 27fa7fd3-949b-41f9-97bc-530f498c0b57
database_url: postgresql+psycopg2://postgres:123456@0.0.0.0:5444/mydb
created_at: 2025-04-08T01:49:27.544521Z
----------------------------------------
```

#### 查询在数据库中的表

```bash
python3 run_chat2db.py list_tb_in_db --database_id mydb_database_id
# 返回示例
----------------------------------------
{'database_id': '27fa7fd3-949b-41f9-97bc-530f498c0b57', 'table_filter': None}
查询数据库配置成功
my_table
----------------------------------------
# 可过滤表名
python3 run_chat2db.py list_tb_in_db --database_id mydb_database_id --table_filter my_table
# 返回示例
----------------------------------------
{'database_id': '27fa7fd3-949b-41f9-97bc-530f498c0b57', 'table_filter': 'my_table'}
查询数据库配置成功
my_table
----------------------------------------
```

---

### 2. 表操作

#### 添加数据表
```bash
python3 run_chat2db.py add_tb --database_id mydb_database_id --table_name users

# 成功返回示例
>> 数据表添加成功
>> table_id: tb_0987654321
```

#### 查询已添加的表

```bash
python3 run_chat2db.py query_tb --database_id mydb_database_id
# 返回示例
查询表格成功
----------------------------------------
table_id: 984d1c82-c6d5-4d3d-93d9-8d5bc11254ba
table_name: oe_compatibility_cve_database
table_note: openEuler社区组cve漏洞信息表，存储了cve漏洞的公告时间、id、关联的软件包名称、简介、cvss评分
created_at: 2025-03-16T12:13:51.920663Z
----------------------------------------
```

#### 删除数据表

```bash
python3 run_chat2db.py del_tb --table_id my_table_id
# 返回示例
删除表格成功
```

#### 查询表的列信息

```bash
python run_chat2db.py query_col --table_id my_table_id

# 返回示例
--------------------------------------------------------
column_id: 5ef50ebb-310b-48cc-bbc7-cf161c779055
column_name: id
column_note: None
column_type: bigint
enable: False
--------------------------------------------------------
column_id: 69cf3c00-8e3c-4b99-83a5-6942278a60f3
column_name: architecture
column_note: openEuler支持的板卡信息的支持架构
column_type: character varying
enable: False
--------------------------------------------------------
```

#### 启用禁用指定列

```bash
python3 run_chat2db.py enable_col --column_id my_column_id --enable False
# 返回示例
列关键字功能开启/关闭成功
```

---

### 3. SQL示例操作

#### 生成SQL示例

```bash
python3 run_chat2db.py add_sql_exp --table_id "your_table_id" --question "查询所有用户" --sql "SELECT * FROM users"
# 返回示例
success
sql_example_id:  4282bce7-f2fd-42b0-a63b-7afd53d9e704
```

#### 批量添加SQL示例

1. 创建Excel文件（示例格式）：

   | question | sql                                          |
   |----------|----------------------------------------------|
   | 查询所有用户   | SELECT * FROM users                          |
   | 统计北京地区用户 | SELECT COUNT(*) FROM users WHERE region='北京' |

2. 执行导入命令：

```bash
python3 run_chat2db.py add_sql_exp --table_id "your_table_id" --dir "path/to/examples.xlsx"
# 成功返回示例
>> 成功添加示例：查询所有用户
>> sql_example_id: exp_556677
>> 成功添加示例：统计北京地区用户 
>> sql_example_id: exp_778899
```

---

#### 删除SQL示例

```bash
python3 run_chat2db.py del_sql_exp --sql_example_id "your_example_id"
# 返回示例
sql案例删除成功
```

#### 查询指定表的SQL示例

```bash
python3 run_chat2db.py query_sql_exp --table_id "your_table_id"
# 返回示例
查询SQL案例成功
--------------------------------------------------------
sql_example_id: 5ab552db-b122-4653-bfdc-085c0b8557d6
question: 查询所有用户
sql: SELECT * FROM users
--------------------------------------------------------
```

#### 更新SQL示例

```bash
python3 run_chat2db.py update_sql_exp --sql_example_id "your_example_id" --question "新问题" --sql "新SQL语句"
# 返回示例
sql案例更新成功
```

#### 生成指定数据表SQL示例

```bash
python run_chat2db.py generate_sql_exp --table_id "your_table_id" --generate_cnt 5 --sql_var True --dir "output.xlsx"
# --generate_cnt 参数: 生成sql对的数量 ；--sql_var: 是否验证生成的sql对，True为验证，False不验证
# 返回示例
sql案例生成成功
Data written to Excel file successfully.
```

### 4. 智能查询

#### 通过自然语言生成SQL（需配合前端或API调用）

```python
# 示例API请求
import requests

url = "http://localhost:8000/sql/generate"
payload = {
    "question": "显示最近7天注册的用户",
    "table_id": "tb_0987654321"
}

response = requests.post(url, json=payload)
print(response.json())

# 返回示例
{
    "sql": "SELECT * FROM users WHERE registration_date >= CURRENT_DATE - INTERVAL '7 days'",
    "confidence": 0.92
}
```

---

5. **执行智能查询**
```http
POST /sql/generate
Content-Type: application/json

{
    "question": "找出过去一个月销售额超过1万元的商品",
    "table_id": "tb_yyyy"
}
```







