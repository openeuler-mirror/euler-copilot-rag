#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import argparse
import hashlib
import json
import os
import secrets
import shutil
import stat

from rag_service.security.util import Security
from rag_service.logger import get_logger


class CryptoHub:

    @staticmethod
    def generate_str_from_sha256(plain_txt):
        hash_object = hashlib.sha256(plain_txt.encode('utf-8'))
        hex_dig = hash_object.hexdigest()
        return hex_dig[:]

    @staticmethod
    def generate_key_config(config_name_sha256, plaintext):
        encrypted_plaintext, encryption_config = Security.encrypt(plaintext)
        rand_num = secrets.randbits(256)
        tmp_out_dir = '.'+str(rand_num)
        if os.path.exists(tmp_out_dir):
            shutil.rmtree(tmp_out_dir)
        os.mkdir(tmp_out_dir, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        js_file_name = config_name_sha256+'.json'
        js_file_dir = os.path.join(tmp_out_dir, js_file_name)
        tmp_config = {}
        for key, val in encryption_config.items():
            key_hash_256 = CryptoHub.generate_str_from_sha256(key)
            tmp_config[key_hash_256] = val
        del encryption_config

        encryption_config = tmp_config
        flags = os.O_WRONLY | os.O_CREAT
        mode = stat.S_IWUSR | stat.S_IRUSR
        with os.fdopen(os.open(js_file_dir, flags, mode), 'w', encoding='utf-8') as js_file:
            json.dump(encryption_config, js_file)
        del encryption_config
        return encrypted_plaintext, os.path.join(os.getcwd(), tmp_out_dir, js_file_name)

    @staticmethod
    def decrypt_with_config(config_dir, encrypted_plaintext, config_deletion_flag=False):
        secret_dict_key_list = [
            "encrypted_work_key",
            "encrypted_work_key_iv",
            "encrypted_iv",
            "half_key1"
        ]
        js_file = open(config_dir, 'r')
        tmp_config = json.load(js_file)
        js_file.close()
        encryption_config = {}
        for key in secret_dict_key_list:
            encryption_config[key] = tmp_config[CryptoHub.generate_str_from_sha256(
                key)]
        del tmp_config
        if config_deletion_flag:
            shutil.rmtree(os.path.dirname(config_dir))
        plaintext = Security.decrypt(encrypted_plaintext, encryption_config)
        del encryption_config
        return plaintext

    @staticmethod
    def generate_key_config_from_file(in_dir, out_dir='', in_dir_flag=False):
        result_dict = {}
        in_file_name_list = os.listdir(in_dir)
        for in_file_name in in_file_name_list:
            with open(os.path.join(in_dir, in_file_name), 'r') as f:
                tmp_dict_list = json.load(f)
                for tmp_dict in tmp_dict_list:
                    for key, val in tmp_dict.items():
                        config_name = str(key)
                        config_name_sha256 = CryptoHub.generate_str_from_sha256(
                            config_name)
                        plaintext = val['plaintext']
                        config_deletion_flag = val['config_deletion_flag']
                        encrypted_plaintext, js_file_dir = CryptoHub.generate_key_config(
                            config_name_sha256, plaintext)
                        result_dict[config_name_sha256] = {
                            CryptoHub.generate_str_from_sha256('encrypted_plaintext'): encrypted_plaintext,
                            CryptoHub.generate_str_from_sha256('key_config_dir'): js_file_dir,
                            CryptoHub.generate_str_from_sha256('config_deletion_flag'): config_deletion_flag
                        }
                del tmp_dict_list
        if in_dir_flag:
            shutil.rmtree(in_dir_flag)
        result_file_name = '.key_config_path_and_encrypted_plaintext.json'
        result_file_name_sha256 = CryptoHub.generate_str_from_sha256(
            result_file_name)
        flags = os.O_WRONLY | os.O_CREAT
        mode = stat.S_IWUSR | stat.S_IRUSR
        with os.fdopen(os.open(os.path.join(out_dir, result_file_name_sha256), flags, mode), 'w') as result_f:
            json.dump(result_dict, result_f)

    @staticmethod
    def query_plaintext_by_config_name(config_name,
                                       full_config_dir='.key_config_path_and_encrypted_plaintext.json'):
        plaintext = ''
        try:
            config_name_sha256 = CryptoHub.generate_str_from_sha256(config_name)
            full_config_dir_sha256 = os.path.join(os.path.dirname(
                full_config_dir), CryptoHub.generate_str_from_sha256(os.path.basename(full_config_dir)))
            with open(full_config_dir_sha256, 'r') as tmp_file:
                full_config_dict = json.load(tmp_file)
            encrypted_plaintext = full_config_dict[config_name_sha256][CryptoHub.generate_str_from_sha256(
                'encrypted_plaintext')]
            config_dir = full_config_dict[config_name_sha256][CryptoHub.generate_str_from_sha256(
                'key_config_dir')]
            config_deletion_flag = full_config_dict[config_name_sha256][CryptoHub.generate_str_from_sha256(
                'config_deletion_flag')]
            plaintext = CryptoHub.decrypt_with_config(
                config_dir, encrypted_plaintext, config_deletion_flag)
        except Exception as ex:
            logger = get_logger()
            logger.error(f"Query plaintext by config name failed due to error: {ex}")
        return plaintext

    @staticmethod
    def add_plaintext_to_env(env_dir, full_config_dir='.key_config_path_and_encrypted_plaintext.json'):
        flags = os.O_APPEND
        mode = stat.S_IRUSR | stat.S_IWUSR
        with os.fdopen(os.open(env_dir, flags, mode), 'a') as env_f:
            full_config_dir_sha256 = os.path.join(os.path.dirname(
                full_config_dir), CryptoHub.generate_str_from_sha256(os.path.basename(full_config_dir)))
            with open(full_config_dir_sha256, 'r') as tmp_file:
                full_config_dict = json.load(tmp_file)
            for key, val in full_config_dict.items():
                encrypted_plaintext = val[CryptoHub.generate_str_from_sha256(
                    'encrypted_plaintext')]
                config_dir = val[CryptoHub.generate_str_from_sha256(
                    'key_config_dir')]
                config_deletion_flag = val[CryptoHub.generate_str_from_sha256(
                    'config_deletion_flag')]
                plaintext = ''
                if config_deletion_flag:
                    plaintext = CryptoHub.decrypt_with_config(
                        config_dir, encrypted_plaintext, config_deletion_flag)
                tmp_str = key+'='+plaintext+'\n'
                env_f.write(tmp_str)
                del tmp_str


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--in_dir", type=str, required=True, help='''Specify the directory where the initia
                        l data for encryption configuration is located.Please provide the input in a diction
                        ary format with key-value pairs, similar to {'a': 'b', 'c': 'd'}.''')
    parser.add_argument("--out_dir", type=str, required=False, help='''Specify the directory for storing re
                        cords of all ciphertexts and their corresponding key configuration file locations. ''')
    args = vars(parser.parse_args())
    arg_in_dir = args['in_dir']
    arg_out_dir = args['out_dir']
    if arg_out_dir is None:
        CryptoHub.generate_key_config_from_file(arg_in_dir)
    else:
        CryptoHub.generate_key_config_from_file(arg_in_dir, out_dir=arg_out_dir)
