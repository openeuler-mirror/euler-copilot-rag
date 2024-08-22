# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import argparse
import secrets
import os
import shutil
import json

from scripts.model.table_manager import TbaleManager
from scripts.kb.kb_manager import KbManager
from scripts.kb_asset.kb_asset_manager import KbAssetManager
from scripts.corpus.handler.corpus_handler import CorpusHandler
from scripts.corpus.manager.corpus_manager import CorpusManager
from logger import get_logger

logger = get_logger()


def work(args):
    config_dir = './config'
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
    choice = args['method']
    pg_host = args['pg_host']
    pg_port = args['pg_port']
    pg_user = args['pg_user']
    pg_pwd = args['pg_pwd']
    pg_database = args['pg_database']
    ssl_enable = args['ssl_enable']
    rag_host = args['rag_host']
    rag_port = str(args['rag_port'])
    kb_name = args['kb_name']
    kb_asset_name = args['kb_asset_name']
    corpus_dir = args['corpus_dir']
    corpus_chunk = args['corpus_chunk']
    corpus_name = args['corpus_name']
    up_chunk = args['up_chunk']
    embedding_model = args['embedding_model']
    vector_dim = args['vector_dim']
    if choice != 'init_pg_info' or choice != 'init_rag_info':
        if os.path.exists(os.path.join(config_dir, 'pg_info.json')):
            with open(os.path.join(config_dir, 'pg_info.json'), 'r', encoding='utf-8') as f:
                pg_info = json.load(f)
            pg_host = pg_info.get('pg_host', '')+':'+pg_info.get('pg_port', '')
            pg_user = pg_info.get('pg_user', '')
            pg_pwd = pg_info.get('pg_pwd', '')
            pg_database = pg_info.get('pg_database', '')
            pg_url = f'postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_host}/{pg_database}'
        else:
            print('请配置postgres信息')
            exit()
        if os.path.exists(os.path.join(config_dir, 'rag_info.json')):
            with open(os.path.join(config_dir, 'rag_info.json'), 'r', encoding='utf-8') as f:
                rag_info = json.load(f)
            rag_url = rag_info.get('rag_host', '')+':'+rag_info.get('rag_port', '')
            if ssl_enable:
                rag_url = 'https://'+rag_url
        else:
            print('请配置rag信息')
            exit()

    if choice == 'init_pg_info':
        logger.info('用户初始化postgres配置')
        pg_info = {}
        pg_info['pg_host'] = pg_host
        pg_info['pg_port'] = pg_port
        pg_info['pg_user'] = pg_user
        pg_info['pg_pwd'] = pg_pwd
        pg_info['pg_database'] = pg_database
        with open(os.path.join(config_dir, 'pg_info.json'), 'w', encoding='utf-8') as f:
            json.dump(pg_info, f)
    elif choice == "init_rag_info":
        logger.info('用户初始化rag配置')
        rag_info = {}
        rag_info['rag_host'] = rag_host
        rag_info['rag_port'] = rag_port
        with open(os.path.join(config_dir, 'rag_info.json'), 'w', encoding='utf-8') as f:
            json.dump(rag_info, f)
    elif choice == "init_pg":
        try:
            TbaleManager.create_db_and_tables(pg_url)
        except Exception as e:
            exit()
    elif choice == "clear_pg":
        while 1:
            choose = input("确认清除数据库：[Y/N]")
            if choose == 'Y':
                try:
                    TbaleManager.drop_all_tables(pg_url)
                except Exception as e:
                    exit()
                break
            elif choose == 'N':
                print("取消清除数据库")
                break
    elif choice == "create_kb":
        try:
            KbManager.create_kb(pg_url, kb_name)
        except Exception as e:
            exit()
    elif choice == "del_kb":
        pass
    elif choice == "query_kb":
        pass
    elif choice == "create_kb_asset":
        try:
            KbAssetManager.create_kb_asset(pg_url, kb_name, kb_asset_name, embedding_model, vector_dim)
        except Exception as e:
            exit()
    elif choice == "del_kb_asset":
        pass
    elif choice == "query_kb_asset":
        pass
    elif choice == "up_corpus":
        para_dir = os.path.join('./', secrets.token_hex(16))
        if os.path.exists(para_dir):
            if os.path.islink(para_dir):
                os.unlink(para_dir)
            shutil.rmtree(para_dir)
        os.mkdir(para_dir)
        corpus_name_list = CorpusHandler.change_document_to_para(corpus_dir, para_dir, corpus_chunk)
        try:
            for corpus_name in corpus_name_list:
                CorpusManager.delete_corpus(pg_url, kb_name, kb_asset_name, corpus_name)
        except:
            pass
        try:
            CorpusManager.upload_corpus(pg_url, rag_url, kb_name, kb_asset_name, para_dir, up_chunk)
            print("语料已上传")
        except Exception as e:
            for corpus_name in corpus_name_list:
                CorpusManager.delete_corpus(pg_url, kb_name, kb_asset_name, corpus_name)
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
                    CorpusManager.delete_corpus(pg_url, kb_name, kb_asset_name, corpus_name)
                except Exception as e:
                    exit()
                break
            elif choose == 'N':
                print("取消删除")
                break
            else:
                continue
    elif choice == "query_corpus":
        corpus_name_list = []
        try:
            corpus_name_list = CorpusManager.query_corpus(pg_url, kb_name, kb_asset_name, corpus_name)
        except Exception as e:
            exit()
        if len(corpus_name_list) == 0:
            print("未查询到语料")
        else:
            print("查询到以下语料名：")
        for corpus_name, time in corpus_name_list:
            print('语料名 ', corpus_name, ' 上传时间 ', time)

    elif choice == "stop_corpus_uploading_job":
        try:
            CorpusManager.stop_corpus_uploading_job(pg_url)
        except Exception as e:
            exit()
    else:
        print("无效的选择")
        exit(1)


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--method", type=str, required=True,
        choices=['init_pg_info', 'init_rag_info', 'init_pg', 'clear_pg', 'create_kb', 'del_kb', 'query_kb',
                 'create_kb_asset', 'del_kb_asset', 'query_kb_asset', 'up_corpus', 'del_corpus', 'query_corpus',
                 'stop_corpus_uploading_job'],
        help=''' 
        脚本使用模式，有init_pg_inf(初始化数据库配置)、init_pg(初始化数据库)、clear_pg（清除数据库）、create_kb(创建资产)、
        del_kb(删除资产)、query_kb(查询资产)、create_kb_asset(创建资产库)、del_kb_asset(删除资产库)、query_kb_asset(查询
        资产库)、up_corpus(上传语料,当前支持txt、html、pdf、docx和md格式)、del_corpus(删除语料)、query_corpus(查询语料)和
        stop_corpus_uploading_job(上传语料失败后，停止当前上传任务)''')
    parser.add_argument("--pg_host", default=None, required=False, help="语料资产所在postres的ip")
    parser.add_argument("--pg_port", default=None, required=False, help="语料资产所在postres的端口")
    parser.add_argument("--pg_user", default=None, required=False, help="语料资产所在postres的用户")
    parser.add_argument("--pg_pwd", default=None, required=False, help="语料资产所在postres的密码")
    parser.add_argument("--pg_database", default=None, required=False, help="语料资产所在postres的数据库")
    parser.add_argument("--rag_host", default=None, required=False, help="rag服务的ip")
    parser.add_argument("--rag_port", default=None, required=False, help="rag服务的port")
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
    parser.add_argument("--vector_dim", type=int, default=1024, required=False, help="向量化维度")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = init_args()
    work(vars(args))
