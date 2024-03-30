# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import argparse
import json
import os
import stat

from rag_service.security.security import Security
from rag_service.security.cryptohub import CryptoHub


def generate_key_config(plaintext):
    encrypted_plaintext, encryption_config = Security.encrypt(plaintext)

    tmp_config = {}
    for key, val in encryption_config.items():
        key_hash_256 = CryptoHub.generate_str_from_sha256(key)
        tmp_config[key_hash_256] = val
    del encryption_config
    return encrypted_plaintext, tmp_config


def generate_key_config_from_file(in_file, out_file='encrypted_config.json'):
    result_dict = dict()
    with open(in_file, 'r') as f:
        tmp_dict = json.load(f)
        for key, val in tmp_dict.items():
            if val['ignore']:
                continue
            config_name = str(key)
            config_name_sha256 = CryptoHub.generate_str_from_sha256(
                config_name)
            plaintext = val['plaintext']
            encrypted_plaintext, encrypted_config = generate_key_config(plaintext)
            result_dict[config_name_sha256] = list()
            result_dict[config_name_sha256].append(encrypted_plaintext)
            result_dict[config_name_sha256].append(encrypted_config)
    flags = os.O_WRONLY | os.O_CREAT
    mode = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(os.path.join(out_file), flags, mode), 'w') as result_f:
        json.dump(result_dict, result_f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--in_file", type=str, required=True, help='''Specify the directory where the
                            initial data for encryption configuration is located.''')
    parser.add_argument("--out_file", type=str, required=False, help='''Specify the directory for storing
                            records of all ciphertexts and their corresponding key configuration file locations. ''')
    args = vars(parser.parse_args())
    arg_in_file = args['in_file']
    arg_out_file = args['out_file']
    if arg_out_file is None:
        generate_key_config_from_file(arg_in_file)
    else:
        generate_key_config_from_file(arg_in_file, arg_out_file)
