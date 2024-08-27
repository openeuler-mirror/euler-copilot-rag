# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import argparse
import secrets
import os
import shutil
import json

from scripts.model.table_manager import TableManager
from scripts.kb.kb_manager import KbManager
from scripts.kb_asset.kb_asset_manager import KbAssetManager
from scripts.corpus.handler.corpus_handler import CorpusHandler
from scripts.corpus.manager.corpus_manager import CorpusManager
from logger import get_logger

logger = get_logger()


def work(args):
    config_dir = './scripts/config'
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
    choice = args['method']
    database_url = args['database_url']
    vector_agent_name = args['vector_agent_name']
    parser_agent_name = args['parser_agent_name']
    rag_url = args['rag_url']
    kb_name = args['kb_name']
    kb_asset_name = args['kb_asset_name']
    corpus_dir = args['corpus_dir']
    corpus_chunk = args['corpus_chunk']
    corpus_name = args['corpus_name']
    up_chunk = args['up_chunk']
    embedding_model = args['embedding_model']
    vector_dim = args['vector_dim']
    num_cores = args['num_cores']
    if int(up_chunk)<=0 or int(up_chunk)>8096:
        print('文件切割尺寸负数或者过大')
        logger.error('文件切割尺寸负数或者过大')
        return
    if int(corpus_chunk )<=0 or int(corpus_chunk )>8096:
        print('文件单次上传个数为负数或者过大')
        logger.error('文件单次上传个数为负数或者过大')
        return
    if int(num_cores)<=0:
        print('线程核数不能为负数')
        logger.error('线程核数不能为负数')
        return
    if choice != 'init_database_info' and choice != 'init_rag_info':
        if os.path.exists(os.path.join(config_dir, 'database_info.json')):
            with open(os.path.join(config_dir, 'database_info.json'), 'r', encoding='utf-8') as f:
                pg_info = json.load(f)
            database_url = pg_info.get('database_url', '')
        else:
            print('请配置数据库信息')
            exit()
        if os.path.exists(os.path.join(config_dir, 'rag_info.json')):
            with open(os.path.join(config_dir, 'rag_info.json'), 'r', encoding='utf-8') as f:
                rag_info = json.load(f)
            rag_url = rag_info.get('rag_url', '')
        else:
            print('请配置rag信息')
            exit()

    if choice == 'init_database_info':
        logger.info('用户初始化postgres配置')
        pg_info = {}
        pg_info['database_url'] = database_url
        with open(os.path.join(config_dir, 'database_info.json'), 'w', encoding='utf-8') as f:
            json.dump(pg_info, f)
    elif choice == "init_rag_info":
        logger.info('用户初始化rag配置')
        rag_info = {}
        rag_info['rag_url'] = rag_url
        with open(os.path.join(config_dir, 'rag_info.json'), 'w', encoding='utf-8') as f:
            json.dump(rag_info, f)
    elif choice == "init_database":
        try:
            TableManager.create_db_and_tables(database_url, vector_agent_name, parser_agent_name)
        except Exception as e:
            exit()
    elif choice == "clear_database":
        while 1:
            choose = input("确认清除数据库：[Y/N]")
            if choose == 'Y':
                try:
                    TableManager.drop_all_tables(database_url)
                except Exception as e:
                    exit()
                break
            elif choose == 'N':
                print("取消清除数据库")
                break
    elif choice == "create_kb":
        try:
            KbManager.create_kb(database_url, kb_name)
        except:
            exit()
    elif choice == "del_kb":
        try:
            KbManager.del_kb(database_url, kb_name)
        except:
            exit()
    elif choice == "query_kb":
        try:
            kb_list = KbManager.query_kb(database_url)
        except:
            exit()
        if len(kb_list) == 0:
            print('为查询到任何资产')
        else:
            print('资产名 创建时间')
            for kb_name, create_time in kb_list:
                print(kb_name, ' ', create_time)
    elif choice == "create_kb_asset":
        try:
            KbAssetManager.create_kb_asset(database_url, kb_name, kb_asset_name, embedding_model, vector_dim)
        except Exception as e:
            exit()
    elif choice == "del_kb_asset":
        try:
            KbAssetManager.del_kb_asset(database_url, kb_name, kb_asset_name)
        except:
            return
    elif choice == "query_kb_asset":
        try:
            kb_asset_list = KbAssetManager.query_kb_asset(database_url, 'default_test')
        except:
            exit()
        if len(kb_asset_list) != 0:
            print(f'资产名：{kb_name}')
            print('资产库名称', ' ', '创建时间')
            for kb_asset_name, create_time in kb_asset_list:
                print(kb_asset_name, ' ', str(create_time))
        else:
            print(f'未在资产{kb_name}下查询到任何资产库')
    elif choice == "up_corpus":
        para_dir = os.path.join('./', secrets.token_hex(16))
        if os.path.exists(para_dir):
            if os.path.islink(para_dir):
                os.unlink(para_dir)
            shutil.rmtree(para_dir)
        os.mkdir(para_dir)
        file_to_para_dict = CorpusHandler.change_document_to_para(corpus_dir, para_dir, corpus_chunk, num_cores)
        try:
            print('尝试删除重名语料')
            for corpus_name in file_to_para_dict.keys():
                CorpusManager.delete_corpus(database_url, kb_name, kb_asset_name, corpus_name)
        except:
            pass
        try:
            CorpusManager.upload_corpus(database_url, rag_url, kb_name, kb_asset_name, para_dir, up_chunk)
            print("语料已上传")
        except Exception as e:
            for corpus_name in file_to_para_dict.keys():
                CorpusManager.delete_corpus(database_url, kb_name, kb_asset_name, corpus_name)
            print(f'语料上传失败:{e}')
        for corpus_dir, para_list in file_to_para_dict.items():
            para_name_list = []
            for i in range(len(para_list)):
                para_name_list.append(os.path.splitext(os.path.basename(str(corpus_dir)))[0]+'_片段'+str(i)+'.docx')
            cnt = CorpusManager.get_uploading_para_cnt(database_url, kb_name, kb_asset_name, para_name_list)
            logger.info(f'文件{corpus_dir}产生{str(len(para_name_list))}个片段，成功上传{cnt}个片段')
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
                    CorpusManager.delete_corpus(database_url, kb_name, kb_asset_name, corpus_name)
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
            corpus_name_list = CorpusManager.query_corpus(database_url, kb_name, kb_asset_name, corpus_name)
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
            CorpusManager.stop_corpus_uploading_job(database_url)
        except Exception as e:
            exit()
    else:
        print("无效的选择")
        exit(1)


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--method", type=str, required=True,
        choices=['init_database_info', 'init_rag_info', 'init_database', 'clear_database', 'create_kb', 'del_kb',
                 'query_kb', 'create_kb_asset', 'del_kb_asset', 'query_kb_asset', 'up_corpus', 'del_corpus',
                 'query_corpus', 'stop_corpus_uploading_job'],
        help=''' 
        脚本使用模式，有init_database_info(初始化数据库配置)、init_database(初始化数据库)、clear_database（清除数据库）、create_kb(创建资产)、
        del_kb(删除资产)、query_kb(查询资产)、create_kb_asset(创建资产库)、del_kb_asset(删除资产库)、query_kb_asset(查询
        资产库)、up_corpus(上传语料,当前支持txt、html、pdf、docx和md格式)、del_corpus(删除语料)、query_corpus(查询语料)和
        stop_corpus_uploading_job(上传语料失败后，停止当前上传任务)''')
    parser.add_argument("--database_url", default=None, required=False, help="语料资产所在数据库的url")
    parser.add_argument("--vector_agent_name", default='vector', required=False, help="向量化插件名称")
    parser.add_argument("--parser_agent_name", default='zhparser', required=False, help="分词插件名称")
    parser.add_argument("--rag_url", default=None, required=False, help="rag服务的url")
    parser.add_argument("--kb_name", type=str, default='default_test', required=False, help="资产名称")
    parser.add_argument("--kb_asset_name", type=str, default='default_test_asset', required=False, help="资产库名称")
    parser.add_argument("--corpus_dir", type=str, default='./scripts/docs', required=False, help="待上传语料所在路径")
    parser.add_argument("--corpus_chunk", type=int, default=1024, required=False, help="语料切割尺寸")
    parser.add_argument("--corpus_name", default="", type=str, required=False, help="待查询或者待删除语料名")
    parser.add_argument("--up_chunk", type=int, default=512, required=False, help="语料单次上传个数")
    parser.add_argument(
        "--embedding_model", type=str, default='BGE_MIXED_MODEL', required=False,
        choices=['TEXT2VEC_BASE_CHINESE_PARAPHRASE', 'BGE_LARGE_ZH', 'BGE_MIXED_MODEL'],
        help="初始化资产时决定使用的嵌入模型")
    parser.add_argument("--vector_dim", type=int, default=1024, required=False, help="向量化维度")
    parser.add_argument("--num_cores", type=int, default=8, required=False, help="语料处理使用核数")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = init_args()
    work(vars(args))
