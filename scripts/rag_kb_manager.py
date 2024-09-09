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
    language = args['language']
    kb_asset_use_language = args['kb_asset_use_language']
    if choice != 'switch_language':
        if os.path.exists(os.path.join(config_dir, 'language_info.json')):
            with open(os.path.join(config_dir, 'language_info.json'), 'r', encoding='utf-8') as f:
                language_info = json.load(f)
            language = language_info.get('language', language)
    if int(up_chunk) <= 0 or int(up_chunk) > 8096:
        if language == 'zh':
            print('文件切割尺寸负数或者过大')
            logger.error('文件切割尺寸负数或者过大')
        else:
            print('File cutting size negative or too large')
            logger.error('File cutting size negative or too large')
        return
    if int(corpus_chunk) <= 0 or int(corpus_chunk) > 8096:
        if language == 'zh':
            print('文件单次上传个数为负数或者过大')
            logger.error('文件单次上传个数为负数或者过大')
        else:
            print('The number of files uploaded at a time is negative or too large')
            logger.error('The number of files uploaded at a time is negative or too large')
        return
    if int(num_cores) <= 0:
        if language == 'zh':
            print('线程核数不能为负数')
            logger.error('线程核数不能为负数')
        else:
            print('The number of thread cores cannot be negative')
            logger.error('The number of thread cores cannot be negative')
        return
    if choice != 'init_database_info' and choice != 'init_rag_info':
        if os.path.exists(os.path.join(config_dir, 'database_info.json')):
            with open(os.path.join(config_dir, 'database_info.json'), 'r', encoding='utf-8') as f:
                database_info = json.load(f)
            database_url = database_info.get('database_url', '')
        else:
            if language == 'zh':
                print('请配置数据库信息')
            else:
                print('Please configure database information')
            exit()
        if os.path.exists(os.path.join(config_dir, 'rag_info.json')):
            with open(os.path.join(config_dir, 'rag_info.json'), 'r', encoding='utf-8') as f:
                rag_info = json.load(f)
            rag_url = rag_info.get('rag_url', '')
        else:
            if language == 'zh':
                print('请配置rag信息')
            else:
                print('Please configure rag information')
            exit()

    if choice == 'switch_language':
        if language == 'zh':
            logger.info('用户选择语言种类')
        else:
            logger.info('User selected language type')
        language_info = {}
        language_info['language'] = language
        with open(os.path.join(config_dir, 'language_info.json'), 'w', encoding='utf-8') as f:
            json.dump(language_info, f)
    elif choice == 'init_database_info':
        if language == 'zh':
            logger.info('用户初始化数据库配置')
        else:
            logger.info('User initializes database configuration')
        database_info = {}
        database_info['database_url'] = database_url
        with open(os.path.join(config_dir, 'database_info.json'), 'w', encoding='utf-8') as f:
            json.dump(database_info, f)
    elif choice == "init_rag_info":
        if language == 'zh':
            logger.info('用户初始化rag配置')
        else:
            logger.info('User initializes Rag configuration')
        rag_info = {}
        rag_info['rag_url'] = rag_url
        with open(os.path.join(config_dir, 'rag_info.json'), 'w', encoding='utf-8') as f:
            json.dump(rag_info, f)
    elif choice == "init_database":
        try:
            TableManager.create_db_and_tables(language, database_url, vector_agent_name, parser_agent_name)
        except Exception as e:
            exit()
    elif choice == "clear_database":
        while 1:
            if language == 'zh':
                choose = input("确认清除数据库：[Y/N]")
            else:
                choose = input("Confirm clearing database: [Y/N]")
            if choose == 'Y':
                try:
                    TableManager.drop_all_tables(language,database_url)
                except Exception as e:
                    exit()
                break
            elif choose == 'N':
                if language == 'zh':
                    print("取消清除数据库")
                else:
                    print("Cancel clearing database")
                break
    elif choice == "create_kb":
        try:
            KbManager.create_kb(language,database_url, kb_name)
        except:
            exit()
    elif choice == "del_kb":
        try:
            KbManager.del_kb(language,database_url, kb_name)
        except:
            exit()
    elif choice == "query_kb":
        try:
            kb_list = KbManager.query_kb(language,database_url)
        except:
            exit()
        if len(kb_list) == 0:
            if language == 'zh':
                print('未查询到任何资产')
            else:
                print('No knowledge base found')
        else:
            if language == 'zh':
                print('资产名 创建时间')
            else:
                print('KnowledgeBaseName CreateTime')
            for kb_name, create_time in kb_list:
                print(kb_name, ' ', create_time)
    elif choice == "create_kb_asset":
        try:
            KbAssetManager.create_kb_asset(language,database_url, kb_name, kb_asset_name, embedding_model,kb_asset_use_language, vector_dim)
        except Exception as e:
            exit()
    elif choice == "del_kb_asset":
        try:
            KbAssetManager.del_kb_asset(language,database_url, kb_name, kb_asset_name)
        except:
            return
    elif choice == "query_kb_asset":
        try:
            kb_asset_list = KbAssetManager.query_kb_asset(language,database_url, kb_name)
        except:
            exit()
        if len(kb_asset_list) != 0:
            if language == 'zh':
                print(f'资产名：{kb_name}')
                print('资产库名称', ' ', '创建时间')
            else:
                print(f'Knowledge base name：{kb_name}')
                print('KnowledgeBaseAssetName', ' ', 'CreateTime')
            for kb_asset_name, create_time in kb_asset_list:
                print(kb_asset_name, ' ', str(create_time))
        else:
            if language == 'zh':
                print(f'No knowledge base asset  found under konwledge base{kb_name}')
            else:
                pass
    elif choice == "up_corpus":
        para_dir = os.path.join('./', secrets.token_hex(16))
        if os.path.exists(para_dir):
            if os.path.islink(para_dir):
                os.unlink(para_dir)
            shutil.rmtree(para_dir)
        os.mkdir(para_dir)
        file_to_para_dict = CorpusHandler.change_document_to_para(language,corpus_dir, para_dir, corpus_chunk, num_cores)
        try:
            if language == 'zh':
                print('尝试删除重名语料')
            else:
                print('Attempt to delete duplicate named corpus')
            for corpus_name in file_to_para_dict.keys():
                CorpusManager.delete_corpus(language,database_url, kb_name, kb_asset_name, corpus_name)
        except:
            pass
        try:
            CorpusManager.upload_corpus(language,database_url, rag_url, kb_name, kb_asset_name, para_dir, up_chunk)
            if language == 'zh':
                print("语料已上传")
            else:
                print("The corpus has been uploaded")
        except Exception as e:
            for corpus_name in file_to_para_dict.keys():
                CorpusManager.delete_corpus(language,database_url, kb_name, kb_asset_name, corpus_name)
            if language == 'zh':
                print(f'语料上传失败:{e}')
            else:
                print(f'Corpus upload failed:{e}')
        for corpus_dir, para_list in file_to_para_dict.items():
            para_name_list = []
            for i in range(len(para_list)):
                para_name_list.append(os.path.splitext(os.path.basename(str(corpus_dir)))
                                      [0]+'_paragraph'+str(i)+'.docx')
            cnt = CorpusManager.get_uploading_para_cnt(language,database_url, kb_name, kb_asset_name, para_name_list)
            if language == 'zh':
                logger.info(f'文件{corpus_dir}产生{str(len(para_name_list))}个片段，成功上传{cnt}个片段')
            else:
                logger.info(f'The file {corpus_dir} generated {str(len(para_name_list))} fragments and successfully uploaded {cnt} fragments')
        if os.path.islink(para_dir):
            os.unlink(para_dir)
        shutil.rmtree(para_dir)
    elif choice == "del_corpus":
        if corpus_name is None:
            if language == 'zh':
                print('请提供要删除的语料名')
            else:
                print('Please provide the name of the corpus to be deleted')
            exit(1)
        while 1:
            if language == 'zh':
                choose = input("确认删除：[Y/N]")
            else:
                choose = input("Confirm deletio:[Y/N]")
            if choose == 'Y':
                try:
                    CorpusManager.delete_corpus(language,database_url, kb_name, kb_asset_name, corpus_name)
                except Exception as e:
                    exit()
                break
            elif choose == 'N':
                if language == 'zh':
                    print("取消删除")
                else:
                    print("undelete")
                break
            else:
                continue
    elif choice == "query_corpus":
        corpus_name_list = []
        try:
            corpus_name_list = CorpusManager.query_corpus(language,database_url, kb_name, kb_asset_name, corpus_name)
        except Exception as e:
            exit()
        if language == 'zh':
            if len(corpus_name_list) == 0:
                print("未查询到语料")
            else:
                print("查询到以下语料名：")
            for corpus_name, time in corpus_name_list:
                print('语料名 ', corpus_name, ' 上传时间 ', time)
        else:
            if len(corpus_name_list) == 0:
                print("No corpus found")
            else:
                print("The following corpus names were found:")
            for corpus_name, time in corpus_name_list:
                print('CorpusName', corpus_name, ' UpdateTime ', time)

    elif choice == "stop_corpus_uploading_job":
        try:
            CorpusManager.stop_corpus_uploading_job(database_url)
        except Exception as e:
            exit()
    else:
        if language == 'zh':
            print("无效的选择")
        else:
            print("Invalid selection")
        exit(1)


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--method", type=str, required=True,
        choices=['switch_language', 'init_database_info', 'init_rag_info', 'init_database', 'clear_database',
                 'create_kb', 'del_kb', 'query_kb', 'create_kb_asset', 'del_kb_asset', 'query_kb_asset', 'up_corpus',
                 'del_corpus', 'query_corpus', 'stop_corpus_uploading_job'],
        help="""
        脚本使用模式，有switch_language（切换语言）、init_database_info(初始化数据库配置)、init_database(初始化数据库)、clear_database（清除数据库）、
create_kb(创建资产)、del_kb(删除资产)、query_kb(查询资产)、create_kb_asset(创建资产库)、del_kb_asset(删除资产库)、query_kb_asset(查询资产库)、
up_corpus(上传语料,当前支持txt、html、pdf、docx和md格式)、del_corpus(删除语料)、query_corpus(查询语料)和stop_corpus_uploading_job(上传语料失
败后，停止当前上传任务)|||Script usage patterns include switch_language（switch language）, init_database_info (initializing database 
configuration), init_database (initializing database), clear_database (clearing database), and create_kb (creating knowledge base)
del_kb (delete knowledge base), query_kb (query knowledge base), creat_kb_asset (create knowledge base aseet), del_kb_asset (delete 
knowledge base aseet), query_kb_asset (query knowledge base aseet), up_corpus (uploading corpus, currently supports txt, html, pdf, 
docx, and md formats), del_corpus (deleting corpus), query_compus (querying corpus), and Stop_compus_uploading_job (Stop the current
upload task after failing to upload corpus)""")
    parser.add_argument("--database_url", default=None, required=False,
                        help="语料资产所在数据库的url|||URL of the database where the corpus asset is located")
    parser.add_argument("--vector_agent_name", default='vector', required=False, help='向量化插件名称|||Vector agent name')
    parser.add_argument("--parser_agent_name", default='zhparser', required=False, help="分词插件名称|||Parser agent name")
    parser.add_argument("--rag_url", default=None, required=False, help="rag服务的url|||URL of Rag service")
    parser.add_argument("--kb_name", type=str, default='default_test', required=False, help="资产名称|||Knowledge base name")
    parser.add_argument("--kb_asset_name", type=str, default='default_test_asset',
                        required=False, help="资产库名称|||Knowledge base asset name")
    parser.add_argument("--corpus_dir", type=str, default='./scripts/docs', required=False,
                        help="待上传语料所在路径|||The path where the corpus to be uploaded is located")
    parser.add_argument("--corpus_chunk", type=int, default=1024, required=False, help="语料切割尺寸|||Corpus cutting size")
    parser.add_argument("--corpus_name", default="", type=str, required=False,
                        help="待查询或者待删除语料名|||Pending query or deletion of corpus names")
    parser.add_argument("--up_chunk", type=int, default=512, required=False,
                        help="语料单次上传个数|||Number of single uploads of corpus")
    parser.add_argument(
        "--embedding_model", type=str, default='BGE_MIXED_MODEL', required=False,
        choices=['TEXT2VEC_BASE_CHINESE_PARAPHRASE', 'BGE_LARGE_ZH', 'BGE_MIXED_MODEL'],
        help="初始化资产时决定使用的嵌入模型|||Determine the embedding model to be used when initializing assets")
    parser.add_argument("--vector_dim", type=int, default=1024, required=False, help="向量化维度|||Vectorization dimension")
    parser.add_argument("--num_cores", type=int, default=8, required=False,
                        help="语料处理使用核数|||Corpus processing uses kernels")
    parser.add_argument(
        "--language", type=str, default='zh', choices=['zh', 'en'],
        help="脚本支持的语言模式|||The supported language mode for the script")
    parser.add_argument(
        "--kb_asset_use_language", type=str, default='zh', choices=['zh', 'en'],
        help="创建资产库时选择的语言类型|||The language type selected when creating the knowledge base asset")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = init_args()
    work(vars(args))
