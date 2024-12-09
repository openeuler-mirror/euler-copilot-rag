import pandas as pd
import jsonlines
import json
import os
import random
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--input_dir", required=True, type=str, help="path to data dir")
parser.add_argument("--output_dir", required=True, type=str, help="path to output dir")
args = parser.parse_args()

data_dir = args.input_dir
output_dir = args.output_dir
file_list = os.listdir(data_dir)
df = pd.DataFrame(columns=['问题', '片段'])
for file in file_list:
    path = os.path.join(data_dir, file)
    print('current: ', path)
    _df = pd.read_excel(path).loc[:, ['问题', '片段']]
    _df.dropna(inplace=True)
    df = pd.concat([df, _df])
df.reset_index(drop=True, inplace=True)

ids = df.index.to_list()
random.shuffle(ids)
train_ids, val_ids = ids[:-1000], ids[-1000:]

print("train_data:", len(train_ids), "train_data:", len(val_ids))

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 生成训练集
print('正在生成训练集...')
train_data_path = os.path.join(output_dir, 'train_data.jsonl')
with jsonlines.open(train_data_path, 'a') as f:
    for i in train_ids:
        dic = {}
        dic['query'] = df['问题'][i]
        dic['pos'], dic['neg'] = [], []
        pos = df['片段'][i]
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
    cor = df['片段'][idx]
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
    query = df['问题'][idx]
    test_dataset['test_data']['query'].append(query)
    poses = []
    pos = df['片段'][idx]
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

print(f'训练集生成完成: {test_data_path}')