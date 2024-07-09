# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import argparse
import secrets
import os
import shutil
import json

from drop_all_table import drop_all_tables
from init_all_table import create_db_and_tables
from upload_courpus import upload_corpus
from delete_courpus import delete_corpus
from query_corpus import query_corpus
from stop_all_job import stop_embedding_job
from init_asset import init_asset
from change_doucument_to_para import change_document_to_para


def work(args):
    config_dir = './config'
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
    if os.path.exists(os.path.join(config_dir, 'pg_info.json')):
        with open(os.path.join(config_dir, 'pg_info.json'), 'r') as f:
            pg_info = json.load(f)
        pg_host = pg_info.get('pg_host', '')
        pg_port = pg_info.get('pg_port', '')
        pg_user = pg_info.get('pg_user', '')
        pg_pwd = pg_info.get('pg_pwd', '')
    choice = args['method']
    pg_host = args['pg_host']
    pg_port = args['pg_port']
    pg_user = args['pg_user']
    pg_pwd = args['pg_pwd']
    ssl_enable = args['ssl_enable']
    rag_host = args['rag_host']
    rag_port = args['rag_port']
    kb_name = args['kb_name']
    kb_asset_name = args['kb_asset_name']
    corpus_dir = args['corpus_dir']
    corpus_chunk = args['corpus_chunk']
    corpus_name = args['corpus_name']
    up_chunk = args['up_chunk']
    embedding_model = args['embedding_model']
    if choice == 'init_pg_info':
        pg_info = {}
        pg_info['pg_host'] = pg_host
        pg_info['pg_port'] = pg_port
        pg_info['pg_user'] = pg_user
        pg_info['pg_pwd'] = pg_pwd
        with open(os.path.join(config_dir, 'pg_info.json'), 'w') as f:
            json.dump(pg_info, f)
    elif choice == "init_pg":
        try:
            create_db_and_tables(pg_host, pg_port, pg_user, pg_pwd)
            print("数据库和表格已初始化")
        except Exception as e:
            print(f'数据库初始化失败：{e}')
    elif choice == "init_corpus_asset":
        try:
            init_asset(pg_host, pg_port, pg_user, pg_pwd, kb_name, kb_asset_name, embedding_model)
            print("资产已初始化")
        except Exception as e:
            print(f'资产始化失败：{e}')
    elif choice == "clear_pg":
        while 1:
            choose = input("确认清除数据库：[Y/N]")
            if choose == 'Y':
                try:
                    drop_all_tables(pg_host, pg_port, pg_user, pg_pwd)
                    print("数据库内容已清空")
                except Exception as e:
                    print(f'数据库内容清除失败：{e}')
                break
            elif choose == 'N':
                print("取消清除数据库")
                break
    elif choice == "up_corpus":
        para_dir = os.path.join('./', secrets.token_hex(16))
        if os.path.exists(para_dir):
            if os.path.islink(para_dir):
                os.unlink(para_dir)
            shutil.rmtree(para_dir)
        os.mkdir(para_dir)
        corpus_name_list = change_document_to_para(corpus_dir, para_dir, corpus_chunk)
        try:
            for corpus_name in corpus_name_list:
                delete_corpus(pg_host, pg_port, pg_user, pg_pwd, kb_name, kb_asset_name, corpus_name)
        except:
            pass
        try:
            for corpus_name in corpus_name_list:
                delete_corpus(pg_host, pg_port, pg_user, pg_pwd, kb_name, kb_asset_name, corpus_name)
            upload_corpus(pg_host, pg_port, pg_user, pg_pwd, ssl_enable,
                          rag_host, rag_port, kb_name, kb_asset_name, para_dir, up_chunk)
            print("语料已上传")
        except Exception as e:
            for corpus_name in corpus_name_list:
                delete_corpus(pg_host, pg_port, pg_user, pg_pwd, kb_name, kb_asset_name, corpus_name)
            print(f'语料上传失败:{e}')
        finally:
            if os.path.islink(para_dir):
                os.unlink(para_dir)
            shutil.rmtree(para_dir)
    elif choice == "del_corpus":
        if corpus_name is None:
            print('请提供要删除的语料名')
            exit(1)
        while 1:
            choose = input("确认删除：[Y/N]")
            if choose == 'Y':
                try:
                    del_flag = delete_corpus(pg_host, pg_port, pg_user, pg_pwd, kb_name, kb_asset_name, corpus_name)
                    if del_flag:
                        print("语料已删除")
                    else:
                        print("语料删除失败，未查询到相关语料")
                except Exception as e:
                    print(f'语料删除失败:{e}')
                break
            elif choose == 'N':
                print("取消删除")
                break
            else:
                continue
    elif choice == "query_corpus":
        corpus_name_list = []
        try:
            corpus_name_list = query_corpus(pg_host, pg_port, pg_user, pg_pwd, kb_name, kb_asset_name, corpus_name)
        except Exception as e:
            print(f"语料查询失败：{e}")
        if len(corpus_name_list) == 0:
            print("未查询到语料")
        else:
            print("查询到以下语料名：")
        for corpus_name, time in corpus_name_list:
            print('语料名 ', corpus_name, ' 上传时间 ', time)

    elif choice == "stop_embdding_jobs":
        try:
            stop_embedding_job(pg_host, pg_port, pg_user, pg_pwd)
            print("所有向量化任务已停止")
        except Exception as e:
            print(f"向量化任务停止失败：{e}")
    else:
        print("无效的选择")
        exit(1)


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", type=str, required=True,
                        choices=['init_pg_info', 'init_pg', 'init_corpus_asset', 'clear_pg', 'up_corpus', 'del_corpus',
                                 'query_corpus', 'stop_embdding_jobs'],
                        help='''
                                                                     脚本使用模式，有初始化数据库配置、初始化数据库、初始化语料资产、
                                                                     清除数据库所有内容、上传语料(当前支持txt、html、pdf、docx和md格式)、删除语料、查询语
                                                                     料和停止当前上传任务''')
    parser.add_argument("--pg_host", default='127.0.0.1', type=str, required=False, help="语料库所在postres的ip")
    parser.add_argument("--pg_port", default='5432', type=str, required=False, help="语料库所在postres的端口")
    parser.add_argument("--pg_user", default='postgres', type=str, required=False, help="语料库所在postres的用户")
    parser.add_argument("--pg_pwd", default='123456', type=str, required=False, help="语料库所在postres的密码")
    parser.add_argument("--rag_host", type=str, default='127.0.0.1', required=False, help="rag服务的ip")
    parser.add_argument("--rag_port", type=str, default='8005', required=False, help="rag服务的port")
    parser.add_argument("--kb_name", type=str, default='default_test', required=False, help="资产名称")
    parser.add_argument("--kb_asset_name", type=str, default='default_test_asset', required=False, help="资产库名称")
    parser.add_argument("--corpus_dir", type=str, default='./docs', required=False, help="待上传语料所在路径")
    parser.add_argument("--corpus_chunk", type=int, default=1024, required=False, help="语料切割尺寸")
    parser.add_argument("--corpus_name", default="", type=str, required=False, help="待查询或者待删除语料名")
    parser.add_argument("--up_chunk", type=int, default=512, required=False, help="语料单次上传个数")
    parser.add_argument("--ssl_enable", type=bool, default=False, required=False, help="rag是否为https模式启动")
    parser.add_argument(
        "--embedding_model", type=str, default='BGE_MIXED_MODEL', required=False,
        choices=['TEXT2VEC_BASE_CHINESE_PARAPHRASE', 'BGE_LARGE_ZH', 'BGE_MIXED_MODEL'],
        help="初始化资产时决定使用的嵌入模型")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = init_args()
    work(vars(args))
