import glob

import pandas as pd
import jsonlines
import json
import os
import random
import argparse


def get_all_file(path):
    path_list = []

    # 获取文件路径
    if os.path.isfile(path):
        # 如果是单个文件，直接添加到路径列表
        path_list.append(path)
    elif os.path.isdir(path):
        # 如果是目录，遍历目录下的所有文件
        for root, _, files in os.walk(path):
            for file in files:
                path_list.append(os.path.join(root, file))
    else:
        # 如果是通配符路径，使用 glob 匹配文件
        for path in glob.glob(path):
            if os.path.isfile(path):
                path_list.append(path)

    return path_list

parser = argparse.ArgumentParser()
parser.add_argument("--input_dir", required=True, type=str, help="path to data dir")
parser.add_argument("--output_dir", required=True, type=str, help="path to output dir")
parser.add_argument("--train_num", required=True, type=int, help="number of train data")

args = parser.parse_args()

#TODO: 适配输入格式
data_dir = args.input_dir
output_dir = args.output_dir
file_list = get_all_file(data_dir)
df = pd.DataFrame(columns=['question', 'answer', 'text'])
for file in file_list:
    path = file
    if not path.endswith('.xlsx'):
        continue
    print('current: ', path)
    _df = pd.read_excel(path).loc[:, ['question', 'answer', 'text']]
    _df.dropna(inplace=True)
    df = pd.concat([df, _df])
df.reset_index(drop=True, inplace=True)

ids = df.index.to_list()
#TODO： 统一输入转换成list


random.shuffle(ids)
ids_count = len(ids)
if args.train_num > ids_count:
    print('train_num > ids_count')
    exit()
train_ids, val_ids = ids[:args.train_num], ids[args.train_num:]

print("train_data:", len(train_ids), "test_data:", len(val_ids))

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 生成训练集
print('正在生成训练集...')
train_data_path = os.path.join(output_dir, 'train_data.jsonl')
with jsonlines.open(train_data_path, 'a') as f:
    for i in train_ids:
        dic = {}
        dic['query'] = df['question'][i]
        # score = df['score'][i]
        # if not score == "是":
        #     continue
        dic['pos'], dic['neg'] = [], []
        pos = str(df['answer'][i])
        length = len(pos)
        cut_idx = length // 2
        if length > 700:
            pos1 = pos[:cut_idx]
            pos2 = pos[cut_idx:]
            dic['pos'].append(pos1)
            dic['pos'].append(pos2)
        else:
            dic['pos'].append(pos)

        pos = str(df['text'][i])
        length = len(pos)
        cut_idx = length // 2
        if length > 700:
            pos1 = pos[:cut_idx]
            pos2 = pos[cut_idx:]
            dic['pos'].append(pos1)
            dic['pos'].append(pos2)
        else:
            dic['pos'].append(pos)
        f.write(dic)
print(f'训练集生成完成: {train_data_path}')

# 生成测试集
print('正在生成测试集...')
test_data_path = os.path.join(output_dir, 'test_data.json')
test_dataset = {
    "corpus": {
        "content": []
    },
    "test_data": {
        "query": [],
        "mapper": {
        }
    }
}
for idx in range(len(df)):
    cor = df['answer'][idx]
    length = len(cor)
    cut_idx = length // 2
    if length > 700:
        cor1 = cor[:cut_idx]
        cor2 = cor[cut_idx:]
        test_dataset['corpus']['content'].append(cor1)
        test_dataset['corpus']['content'].append(cor2)
    else:
        test_dataset['corpus']['content'].append(cor)
for idx in val_ids:
    query = df['question'][idx]
    test_dataset['test_data']['query'].append(query)
    poses = []
    pos = df['answer'][idx]
    length = len(pos)
    cut_idx = length // 2
    if length > 700:
        pos1 = pos[:cut_idx]
        pos2 = pos[cut_idx:]
        poses.append(pos1)
        poses.append(pos2)
    else:
        poses.append(pos)
    test_dataset['test_data']['mapper'][query] = poses

with open(test_data_path, 'w', encoding='utf-8') as f:
    json.dump(test_dataset, f, indent=2, ensure_ascii=False)

print(f'测试集生成完成: {test_data_path}')
