# 脚本使用指南

## 1. 生成问答对

### 1.1 功能简介

该功能用于将原始数据转换为问答对，并将问答对保存为 json (默认) /xlsx/yaml 格式的文件。

### 1.2 功能参数说明

| 参数名 | 默认值 | 说明                                            |
| --- | --- |-----------------------------------------------|
| path |  | 必填，指定待处理的文件路径，支持 docx、pdf、txt 等格式             |
| output_path |  | 必填，指定输出路径                                     |
| output_format | json | 可选，指定输出格式，支持 json、xlsx、yaml 三种格式              |
| enhance | False | 可选，是否使用增强模式，增强模式下，将通过验证机制增强生成的问答对的准确率         |
| qa_count | 5 | 可选，指定生成问答对的数量，对于每个文档随机选择若干chunk生成qa_count个问答对 |


### 1.3 使用示范
```bash
python utils/main.py \
qa_generate \
--path docs/examples.xlsx \
--output_path output  \
--output_format json \
--enhance \
--qa_count 10
```

### 1.4 结果输出

结果输出在 output_path 目录下

## 2. 文档治理

### 2.1 功能简介

该功能用于优化文档的表现形式，功能包括 
1. 去除重复段落、文本
2. 敏感信息脱敏（自定义敏感词、敏感内容格式）
3. 文档内容标准化，包括统一编码格式、统一全半角等
4. 文档内容格式化，包括通用场景（段落总结，支持自定义格式）、开发场景（代码注释）、运维场景（案例整理）三种类别

### 2.2 功能参数说明

| 参数名 | 默认值     | 说明                                                     |
| --- |---------|--------------------------------------------------------|
| method |         | 必填，指定脚本的功能，此处为 "document_governance"                   |
| path |         | 必填，指定待处理的文件路径，支持 docx、pdf、txt 等格式                      |
| output_path |         | 必填，指定输出路径                                              |
| output_format | json    | 可选，指定输出格式，支持 json、xlsx、yaml 三种格式                       |
| standardize | False   | 可选，是否进行文档内容标准化，包括统一编码格式、统一全半角等                         |
| unique | False   | 可选，是否去除重复段落、文本                                         |
| format | False   | 可选，是否进行文档内容格式化，包括通用场景（段落总结）、开发场景（代码注释）、运维场景（案例整理）三种类别  |
| format_mode | general | 可选，指定文档内容格式化模式，包括 "general"、"develop"、"OPS" 分别对应上述三种场景 |


### 2.3 使用示范
```bash
python3 utils/main.py \
  document_governance \
  --path docs/test_for_document.txt \
  --output_path output/document \
  --standardize \
  --format \
  --unique \
  --output_format md \
  --format_mode develop 
```

### 2.4 自定义内容

#### 2.4.1 自定义敏感词
敏感词文件为 sensitive_words.txt，每行一个敏感词，示例如下：
```text
暴力
色情
赌博
毒品
诈骗
```
敏感格式表文件为 sensitive_pattern.txt，每行一个敏感句式，通过正则表达式匹配，示例如下：
```text
\b(赌|博)\b
\b(毒|品)\b
\b(诈|骗)\b
\b(暴|力)\b
\b(色|情)\b
```
术语替换文件为 term_replacements.txt，每行一个替换词，示例如下：
```text
医生:医师
护士:护理人员
医院:医疗机构
手术:外科操作
药物:药剂
```

### 3.5 结果输出

结果输出在 output_path 目录下

## 3. 向量模型微调

### 3.1 功能简介

该功能用于微调指定的向量模型，包括 bge-large-zh、bge-large-en、bge-small-zh、bge-small-en 等。


### 3.2 数据集/测试集

#### 3.2.1 数据格式
数据集格式为jsonl，示例如下：
```
{"query": str, "pos": List[str], "neg":List[str], "pos_scores": List[int], "neg_scores": List[int], "prompt": str, "type": str}
```
其中 query 为问题，pos 为正例，neg 为负例，pos_scores 为正例的打分，neg_scores 为负例的打分，prompt 为提示词，type 为数据分类。

测试集格式为json，示例如下:
```
{
    "corpus": {
        "content": list[str],
    },
    "test_data": {
        "query": list[str],
        "mapper": {  # key: query, value: answer
          str: str,
        }
    }
}

```
其中 corpus 为语料库，test_data 为测试集，query 为问题，mapper 为正确答案。

#### 3.2.2 生成方式：
1) 使用脚本生成问答对到output_path，或者使用数据集和测试集自行构造成xlsx格式，格式为question列为query，answer列为答案。 
2) 使用脚本生成训练集和测试集，生成方法如下:请执行 data_processing.py 脚本将你的数据处理成如下 jsonl 格式：

```
{"query": str, "pos": List[str], "neg":List[str]}
```
query是查询指令，pos是正例列表，neg是负例列表

```
python utils/my_tools/bge_finetune/data_processing.py \
--input_dir data_path \
--output_dir output_path \
--train_num 10000
```
- input_dir 问答对数据存放目录
- output_dir 训练集和测试机输出目录 
- train_num 训练集数量

如果数据中没有负例，则可以使用以下命令从整个语料库中随机抽取样本做负例增强：
```
python ./utils/my_tools/bge_finetune/hn_mine.py \
    --embedder_name_or_path BAAI/bge-large-zh-v1.5 \
    --input_file path/to/data.jsonl \
    --output_file path/to/data_minedHN.jsonl \
    --range_for_sampling 2-200 \
    --negative_number 15 \
    --use_gpu_for_searching 
```
- input_file：jsonl 格式的原始训练数据
- output_file：负例增强后输出的 jsonl 数据的路径
- range_for_sampling：采样区间，例如，2-100表示从 top2-top200 文档中采样负样本
- negative_number：采样负样本的数量
- use_gpu_for_searching：是否使用 faiss-gpu 来检索

### 3.3 功能参数说明


| 参数名                | 默认值 | 说明                                  |
|--------------------| --- |-------------------------------------|
| method             |  | 必填，指定脚本的功能，此处为 "embedding_training" |
| train_data         |  | 必填，指定训练数据路径，支持 jsonl 格式             |
| test_data          |  | 必填，指定测试数据路径，支持 json 格式            |
| output_path        |  | 必填，指定模型输出路径                         |
| batch_size         | 8 | 可选，指定训练批次大小                         |
| learning_rate      | 5e-5 | 可选，指定学习率                            |
| deepspeed          |  | 可选，指定 deepspeed 配置文件路径，用于优化微调速度     |
| epochs             | 3 | 可选，指定训练轮数                           |
| save_steps         | 1000 | 可选，指定保存模型的步数                        |
| logging_steps      | 100 | 可选，指定日志输出的步数                        |
| gpu_num            | 1 | 可选，指定使用的 GPU 数量                     |
| model_name_or_path |  | 可选，指定微调的模型路径，默认为 bge-large-zh-v1.5  |
| temperature        | 0.02 | 可选，指定温度参数，默认为 0.02                  |
| warmup             | 0.1 | 可选，指定预热比例，默认为 0.1                   |



### 3.4 使用示范

```bash
python3 utils/main.py \
  embedding_training \
  --train_data output/bge/train_data_mineHN.jsonl \
  --test_data output/bge/test_data.json \
  --output_path output/test_encoder_only_base_bge-large-en-v1.5 \
  --batch_size 2 \
  --learning_rate 5e-5 \
  --deepspeed utils/my_tools/bge_finetune/ds_stage0.json \
  --epochs 1 \
  --save_steps 1000 \
  --logging_steps 100 \
  --gpu_num 4 \
  --model_name_or_path ./bge_model/bge-large-en-v1.5 \
  --temperature 0.02 \
  --warmup 0.1
```

### 3.5 结果输出
微调后模型输出在 **output_path** 对应目录下，报告输出在  **./report/embedding/{训练完成时间}** 目录下，报告包含训练过程曲线图、模型预测结果等。

需要进行模型评估和合并，请参考./utils/my_tools/bge_finetune/README.md