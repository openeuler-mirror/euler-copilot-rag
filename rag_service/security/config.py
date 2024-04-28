# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os

from dotenv import dotenv_values


class Config:
    config: dict

    def __init__(self):
        if os.getenv("CONFIG"):
            config_file = os.getenv("CONFIG")
        else:
            config_file = "./config/.env"
        self.config = dotenv_values(config_file)

        if os.getenv("PROD"):
            os.remove(config_file)

    def __getitem__(self, key):
        if key in self.config:
            return self.config[key]
        else:
            return None


config = Config()