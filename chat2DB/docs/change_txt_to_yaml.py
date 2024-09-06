import yaml
text = {
    'sql_generate_prompt': '''你是一个数据库专家，你的任务是参考给出的表结构以及表注释和示例，基于给出的问题生成一条在{database_url}连接下可进行查询的sql语句。
注意：
#01 sql语句中，特殊字段需要带上双引号。
#02 sql语句中，如果要使用 as，请用双引号把别名包裹起来。
#03 sql语句中，查询字段必须使用`distinct`关键字去重。
#04 sql语句中，只返回生成的sql语句, 不要返回其他任何无关的内容
#05 sql语句中，参考问题，对查询字段进行冗余。
#06 sql语句中，需要以分号结尾。

以下是表结构以及表注释：
{table_note}
以下是{k}个示例：
{sql_example}
以下是问题：
{question}
''',
    'table_choose_prompt': '''你是一个数据库专家，你的任务是参考给出的表名以及表的条目（主键，表名、表注释），输出最适配于问题回答检索的{table_cnt}张表，并返回表对应的主键。
注意：
#01 输出的表名用python的list格式返回，下面是list的一个示例：
[\"prime_key1\",\"prime_key2\"]。
#02 只输出包含主键的list即可不要输出其他内容!!!
#03 list重主键的顺序，按表与问题的适配程度从高到底排列。
#04 若无任何一张表适用于问题的回答，请返回空列表。

以下是表的条目：
{table_entries}
以下是问题：
{question}
'''
}
print(text)
with open('./prompt.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(text, f, allow_unicode=True)
