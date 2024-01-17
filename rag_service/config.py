import contextlib
import os
from pathlib import Path
from typing import Optional

import torch
from sqlmodel import Session, select

from rag_service.database import engine
from rag_service.models.database.models import ServiceConfig

DEFAULT_SERVICE_CONFIG = {
    'data_dir': str(Path(os.sep).absolute() / 'vector_data'),
    'vectorization_chunk_size': '100',
    'embedding_chunk_size': '10000',
    'remote_embedding_endpoint': 'http://localhost:8001/embedding',
    'default_top_k': '5',
    'baichuan_llm_url': 'http://localhost:8000/v1/chat/completions',
    'starchat_llm_url': 'http://123.60.114.28:32315/v1/chat/completions',
    'llm_token_check_url': 'http://localhost:8000/api/v1/token_check',
    'llm_model': 'baichuan2',
    'llm_temperature': '0.1',
    'llm_top_p': '0.95',
    'prompt_template': '''已知信息:{{ context }}
根据上述已知信息，简洁和专业的来回答用户的问题。如果无法从已知信息中得到答案，请在事先声明"没有搜索到足够的相关信息，以下是根据我的经验做出的回答"后，根据先前训练过的知识回答问题，不需要提到提供的知识片段。
示例:
问题: 你是谁
回答: 我的名字叫小智，我是openEuler社区的助手。欢迎您问我有关openEuler的任何问题，我将尽力为您解答。
请回答:{{ question }}''',

    'query_generate_prompt_template': '''你是openEuler的AI语言模型助手。你的任务是先理解原始问题，并生成三个基于原始问题的拓展版本，以体现问题的多个视角。请提供这些问题，并用换行符分隔。

原始问题: {{question}}''',

    'shell_prompt_template': '''问题: {{ question }}

你是一个shell专家，你的任务是根据问题生成shell命令并返回，不要生成与shell命令无关的信息。''',

    'classifier_prompt_template': '''问题: {{question}}

不回答具体问题，只判断一下问题是知识问答还是shell命令：

注意：
- 通用知识问答通常包含这些关键词：'定义'、'是什么'、'是多少'、'结果'、'意味着什么'、'介绍'、'怎么做'、'如何实现'、'步骤'、'原理是什么'、'背后的逻辑'、'与...的区别'、'对比'、'相比'、'优点'、'缺点'、'优势'、'劣势'、'支持'、'兼容性'、'适用于哪些'、'最新版本'、'更新记录'、'版本历史'、'发展计划'、'未来方向'、'战略规划'。
- Shell命令生成通常包含这些关键词：'Linux'、'Shell'、'实现...功能'、'执行'、'输出'、'输入'、'权限'、'目录'、'命令'、'编辑'、'创建'、'修改'、'重命名'、'备份'、'切换目录'、'列出内容'、'创建目录'、'排序'、'筛选'、'统计'、'计算'、'配置'、'安装'、'更新'、'权限设置'、'连接'、'下载'、'上传'、'同步'、'监控'、'日志分析'、'测试'、'调试'、'加密'、'解密'、'安全检查'、'恢复'、'脚本执行'、'自动化任务'、'定时任务'。
'''
}

def load_service_config(name: str) -> Optional[str]:
    with Session(engine) as session:
        with contextlib.suppress(Exception):
            return session.exec(select(ServiceConfig).where(ServiceConfig.name == name)).one().value
        return DEFAULT_SERVICE_CONFIG[name]


EMBEDDING_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DATA_DIR = load_service_config('data_dir')
VECTORIZATION_CHUNK_SIZE = int(load_service_config('vectorization_chunk_size'))
EMBEDDING_CHUNK_SIZE = int(load_service_config('embedding_chunk_size'))
REMOTE_EMBEDDING_ENDPOINT = load_service_config('remote_embedding_endpoint')
DEFAULT_TOP_K = int(load_service_config('default_top_k'))
BAICHUAN_LLM_URL = load_service_config('baichuan_llm_url')
STARCHAT_LLM_URL = load_service_config('starchat_llm_url')
LLM_MODEL = load_service_config('llm_model')
LLM_TEMPERATURE = float(load_service_config('llm_temperature'))
LLM_TOP_P = float(load_service_config('llm_top_p'))
LLM_TOKEN_CHECK_URL = load_service_config('llm_token_check_url')
PROMPT_TEMPLATE = load_service_config('prompt_template')
QUERY_GENERATE_PROMPT_TEMPLATE = load_service_config(
    'query_generate_prompt_template')
SHELL_PROMPT_TEMPLATE = load_service_config('shell_prompt_template')
CLASSIFIER_PROMPT_TEMPLATE = load_service_config('classifier_prompt_template')
