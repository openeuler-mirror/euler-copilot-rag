# bge-large-zh微调指南

### BGE简介

BGE（BAAI General Embedding）是北京智源人工智能研究院开源的一系列embedding大模型，其核心功能是将文本转换为高维向量表示。这些向量捕捉了文本中的语义信息，为后续的相似性搜索提供了便利。

bge-large-zh是BGE系列中参数规模最大的中文向量大模型，参数3.26亿。输入序列512，输出维度1024，是本文所使用的BGE模型版本。

### 准备工作

#### 安装 FlagEmbedding
- 使用pip
```
pip install -U FlagEmbedding
```

- 源码安装
```
git clone https://github.com/FlagOpen/FlagEmbedding.git
cd FlagEmbedding
pip install  .
```
### 数据处理
请执行 data_processing.py 脚本将你的数据处理成如下 jsonl 格式：
```
{"query": str, "pos": List[str], "neg":List[str]}
```
query是查询指令，pos是正例列表，neg是负例列表

```
python data_processing.py --input_dir data_path --output_dir output_path --train_num 10000
```
- input_dir 问答对数据存放目录
- output_dir 训练集和测试机输出目录
- train_num 训练集数量

如果数据中没有负例，则可以使用以下命令从整个语料库中随机抽取样本做负例增强：
```
python -m FlagEmbedding.baai_general_embedding.finetune.hn_mine \
    --model_name_or_path BAAI/bge-large-zh-v1.5 \
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

### 运行微调
```
torchrun \
    --nproc_per_node 2 \
    -m FlagEmbedding.baai_general_embedding.finetune.run \
    --output_dir path/to/fine_tuned_model \
    --model_name_or_path BAAI/bge-large-zh-v1.5 \
    --train_data path/to/data_minedHN.jsonl \
    --learning_rate 1e-5 \
    --fp16 \
    --num_train_epochs 30 \
    --per_device_train_batch_size 4 \
    --gradient_accumulation_steps 10 \
    --dataloader_drop_last True \
    --normlized True \
    --temperature 0.02 \
    --query_max_len 64 \
    --passage_max_len 512 \
    --train_group_size 2 \
    --negatives_cross_device \
    --logging_steps 10 \
    --save_steps 0.2 \
    --query_instruction_for_retrieval ""
```
### 模型合并[可选的]
```
from LM_Cocktail import mix_models, mix_models_with_data

model = mix_models(
    model_names_or_paths=["BAAI/bge-large-zh-v1.5", "your_fine-tuned_model"], 
    model_type='encoder', 
    weights=[0.5, 0.5],  # you can change the weights to get a better trade-off.
    output_path='./mixed_model_1')
```
### 评估
- 首先，安装 faiss （近似最近邻搜索库）：
```
pip install faiss-gpu
```
- 执行 eval.py 脚本评估模型，计算召回率和 MRR 指标：
```
python eval.py \
    --encoder your_model_path \
    --fp16 \
    --max_query_length 64 \
    --max_passage_length 512 \
    --batch_size 4 \
    --val_data your_val_dataset_path_ \
    --add_instruction \
    --k 100
```
- 评估结果示例：
```
# 微调前
{'MRR@1': 0.48, 'MRR@10': 0.4985634920634917, 'MRR@100': 0.5121167012782633, 'Recall@1': 0.296, 'Recall@10': 0.368, 'Recall@100': 0.65}
# 微调后
{'MRR@1': 0.702, 'MRR@10': 0.7113190476190476, 'MRR@100': 0.721750086730327, 'Recall@1': 0.418, 'Recall@10': 0.49, 'Recall@100': 0.918}
# 微调前后模型合并[0.5, 0.5]
{'MRR@1': 0.722, 'MRR@10': 0.7387634920634922, 'MRR@100': 0.7472510142865891, 'Recall@1': 0.432, 'Recall@10': 0.519, 'Recall@100': 0.901}
```