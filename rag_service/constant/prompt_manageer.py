# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import yaml

with open('./config/prompt_template.yaml', 'r', encoding='utf-8') as f:
    prompt_template_dict = yaml.load(f, Loader=yaml.SafeLoader)