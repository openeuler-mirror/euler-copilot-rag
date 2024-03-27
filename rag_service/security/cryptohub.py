#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import hashlib
import json
import os
import shutil

from rag_service.security.util import Security
from rag_service.logger import get_logger


class CryptoHub:

    @staticmethod
    def generate_str_from_sha256(plain_txt):
        hash_object = hashlib.sha256(plain_txt.encode('utf-8'))
        hex_dig = hash_object.hexdigest()
        return hex_dig[:]

    @staticmethod
    def decrypt_with_config(encrypted_plaintext):
        secret_dict_key_list = [
            "encrypted_work_key",
            "encrypted_work_key_iv",
            "encrypted_iv",
            "half_key1"
        ]
        encryption_config = {}
        for key in secret_dict_key_list:
            encryption_config[key] = encrypted_plaintext[1][CryptoHub.generate_str_from_sha256(
                key)]
        plaintext = Security.decrypt(encrypted_plaintext[0], encryption_config)
        del encryption_config
        return plaintext

    @staticmethod
    def query_plaintext_by_config_name(config_name,
                                       config_file='/config/encrypted_config.json'):
        plaintext = ''
        try:
            config_name_sha256 = CryptoHub.generate_str_from_sha256(config_name)

            with open(config_file, 'r') as file:
                full_config_dict = json.load(file)
            encrypted_plaintext = full_config_dict[config_name_sha256]
            plaintext = CryptoHub.decrypt_with_config(encrypted_plaintext)
        except Exception as ex:
            logger = get_logger()
            logger.error(f"Query plaintext by config name failed due to error: {ex}")
        return plaintext
