import datetime
import json

import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt

# 读取数据
data = []
with open('./logs/embedding/temp.log', 'r') as file:
    for line in file:
        try:
            data.append(eval(line))
        except:
            print(line)
file_path = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
# 将数据转换为DataFrame
df = pd.DataFrame(data)
if os.path.exists(f'./report'):
    pass
else:
    os.mkdir(f'./report')
if os.path.exists(f'./report/{file_path}'):
    pass
else:
    os.mkdir(f'./report/{file_path}')

print(df)
plt.xticks(np.arange(0, int(df['epoch'].max()) + 1))
# 绘制损失随时间变化的图表
plt.figure(figsize=(10, 5))
plt.plot(df['epoch'], df['loss'], label='Loss')
plt.title('Training Loss Over Epochs')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.grid(True)
plt.savefig(f'./report/{file_path}/loss_over_epochs.png')

# 绘制学习率随时间变化的图表
plt.figure(figsize=(10, 5))
plt.plot(df['epoch'], df['learning_rate'], label='Learning Rate', color='orange')
plt.title('Learning Rate Over Epochs')
plt.xlabel('Epoch')
plt.ylabel('Learning Rate')
plt.legend()
plt.grid(True)
plt.savefig(f'./report/{file_path}/learning_rate_over_epochs.png')

df.to_excel(f'./report/{file_path}/training_report.xlsx', index=False)

# 读取日志文件
def read_log(file_path):
    data = {}
    with open(file_path, 'r') as f:
        for line in f:
            record = json.loads(line.strip())
            key = list(record.keys())[0]
            value = record[key]
            data[key] = value
    return data

# 读取 base.log 和 target.log
base_data = read_log('./logs/embedding/base.log')
target_data = read_log('./logs/embedding/target.log')

# 生成表格
def generate_table(base_data, target_data):

    # 生成 Markdown 表格
    table = "| Metric | Base Value | final Value |\n"
    table += "|--------|------------|--------------|\n"
    for key,v in base_data.items():
        base_value = base_data.get(key, "-")
        target_value = target_data.get(key, "-")
        table += f"| {key} | {base_value} | {target_value} |\n"
    return table

# 生成表格
table = generate_table(base_data, target_data)


def get_evenly_spaced_losses(df, num_samples=30):
    total_rounds = len(df)

    if total_rounds <= num_samples:
        # 如果总轮数小于等于所需样本数，直接返回所有样本
        return df['loss']
    else:
        # 计算间隔
        step = total_rounds // (num_samples - 1)
        indices = list(range(0, total_rounds, step))[:num_samples]
        return df['loss'].iloc[indices]


# 获取30轮的损失（平均分配）
selected_losses = get_evenly_spaced_losses(df)
with open('./temp/losses.txt', 'w') as file:
    file.write(f"{selected_losses}")
# 生成训练报告
report = f"""
训练报告
================

- **总训练时间**: {df['train_runtime'].iloc[-1]:.2f} 秒
- **平均每秒样本数**: {df['train_samples_per_second'].iloc[-1]:.2f}
- **平均每秒步骤数**: {df['train_steps_per_second'].iloc[-1]:.2f}
- **最终损失值**: {df['loss'].iloc[-2]}
- **最终学习率**: {df['learning_rate'].iloc[-2]}
- **最终轮次**: {df['epoch'].iloc[-1]:.2f}

损失和学习率图表：
-----------------------------
![各轮次的损失变化](./loss_over_epochs.png)
![各轮次的学习率变化](./learning_rate_over_epochs.png)

选取的指标：
-------------------
在评估模型性能时，我们选择了以下几类关键指标来衡量不同方面的表现。这些指标有助于全面理解模型在推荐或检索任务中的效果。

- **MRR (Mean Reciprocal Rank)**: 用于评估排序质量，特别是对于首位相关性高的项目。MRR 能够反映出模型将相关项排在前面的能力，较高的MRR值表明模型更早地呈现了相关项。
- **Recall (召回率)**: 表示正确推荐的项目占所有相关项目的比例，反映了模型覆盖真实相关项的能力。高召回率意味着模型能够找到更多的相关项。
- **Precision (精确率)**: 表示推荐列表中真正相关的项目比例，尤其对高位置的推荐项重要。高精确率意味着推荐的大多数项都是用户感兴趣的。
- **F1-Score**: 是精确率和召回率的调和平均数，提供了一个综合考虑两者平衡的评价标准。F1-Score 在精确率和召回率之间寻求平衡，特别适用于两者都重要的场景。当模型需要同时优化精确率和召回率时，F1-Score 是一个非常有用的指标。
- **HitRate (命中率)**: 指的是是否至少有一个相关项被推荐，是二元评价标准。HitRate 强调了模型是否有能力将任何相关项包含在推荐列表中。
- **NDCG (Normalized Discounted Cumulative Gain)**: 考虑了推荐列表中项目的位置权重，越靠前的相关项得分越高。NDCG 是一个综合性的评价指标，既考虑了相关性也考虑了位置因素。

上述指标均在不同的K值下计算（如@1, @5, @10等），以评估不同长度结果列表的性能。选择这些指标是因为它们在信息检索和推荐系统中广泛应用，并且可以从不同角度全面评估模型的性能。

指标对比：
-------------------
{table}
"""

# 保存报告到文件
with open(f'./report/{file_path}/training_report.md', 'w') as file:
    file.write(report)

print(f"Training report generated successfully. Report in ./report/{file_path}.")