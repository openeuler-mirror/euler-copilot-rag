import argparse
import glob
import logging
import os
import time
from datetime import datetime

import pandas as pd
import yaml

from utils.my_tools.llm import LLM
from utils.config.config import config
from utils.parser.service.parser_service import EasyParser
from utils.service.embedding_training import EmbeddingTraining
from utils.service.qa_generate import QAgenerator
from utils.service.document_governance import DocumentGovernance


class CLIService:
    def __init__(self):
        self.prompt_dict = self.get_prompt_dict()
        self.args = self.parse_arguments()
        self.llm = LLM(model_name=config['MODEL_NAME'],
                       openai_api_base=config['OPENAI_API_BASE'],
                       openai_api_key=config['OPENAI_API_KEY'],
                       max_tokens=config['MAX_TOKENS'],
                       request_timeout=60,
                       temperature=0.3)

    @staticmethod
    def get_prompt_dict():
        """
        获取prompt表
        """
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            return prompt_dict
        except Exception as e:
            logging.error(f'Get prompt failed : {e}')
            raise e

    async def parser_file(self, file_path):
        model = EasyParser()
        answer = await model.parser(file_path, self.llm)
        return answer['chunk_list']

    import os
    import glob

    async def get_all_file(self):
        path_list = []

        # 获取文件路径
        if os.path.isfile(self.args.path):
            # 如果是单个文件，直接添加到路径列表
            path_list.append(self.args.path)
        elif os.path.isdir(self.args.path):
            # 如果是目录，遍历目录下的所有文件
            for root, _, files in os.walk(self.args.path):
                for file in files:
                    path_list.append(os.path.join(root, file))
        else:
            # 如果是通配符路径或多个文件路径，使用 glob 匹配文件
            for path in self.args.path:
                if os.path.isfile(path):
                    path_list.append(path)
                elif os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        for file in files:
                            path_list.append(os.path.join(root, file))
                else:
                    for matched_path in glob.glob(path):
                        if os.path.isfile(matched_path):
                            path_list.append(matched_path)

        return path_list

    async def solve(self):
        """
        处理
        """
        times = []
        start_time = time.time()
        if self.args.mode == 'embedding_training':
            await self.embedding_training()
            times.append({'file': 'embedding_training', "time": time.time() - start_time})
        else:
            path_list = await self.get_all_file()
            print(f"文件列表: {path_list}")
            print(f"文件总数:", len(path_list))
            sum_qa = 0
            ret_count = 0
            sum_chunks = 0
            for file in path_list:
                temp_start_time = time.time()
                chunks = []
                if self.args.mode in ['qa_generate', 'document_governance']:
                    try:
                        chunks = await self.parser_file(file)
                        new_chunks = []
                        for chunk in chunks:
                            new_chunk = {
                                'text': chunk['text'],
                                'type': chunk['type'].split('.')[1],
                            }
                            new_chunks.append(new_chunk)
                        chunks = new_chunks
                    except Exception as e:
                        print(f'parser {file} error:', e)
                        continue
                try:
                    if self.args.mode == 'qa_generate':
                        qa_count = self.args.qa_count + ret_count
                        results, ans = await self.qa_generate(chunks, file, qa_count)
                        if ans < qa_count:
                            ret_count = qa_count - ans
                        else:
                            ret_count = 0
                        sum_qa = sum_qa + ans
                    elif self.args.mode == 'document_governance':
                        chunks = await self.document_governance(chunks, file)
                        sum_chunks = sum_chunks + len(chunks)
                except Exception as e:
                    print(f'solve {file} error:', e)
                    continue

                print(f"文件 {file} 完成，用时：{time.time() - temp_start_time}")
                times.append({'file': file, "time": time.time() - temp_start_time,
                              "count": ans if self.args.mode == 'qa_generate' else len(chunks)})
                # logging.info(f"文件 {file} 完成，用时：{time.time() - temp_start_time}")
            if self.args.mode == 'qa_generate':
                print(f"问答对总数：{sum_qa}")
                # logging.info(f"问答对总数：{sum_qa}")
            if self.args.mode == 'document_governance':
                print(f"文档治理完成，共处理 {sum_chunks} 个文本块")
                # logging.info(f"问答对总数：{sum_chunks}")

        print(f"处理完成，耗时：{time.time() - start_time}")
        # logging.info(f"处理完成，耗时：{time.time() - start_time}")
        # 输出times到path_time.xlsx
        df = pd.DataFrame(times)
        os.makedirs("logs", exist_ok=True)
        df.to_excel(f"logs/{self.args.mode}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx", index=False)
        print(f'Excel结果已输出到logs/{self.args.mode}_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx')

    async def qa_generate(self, chunks, file, qa_count):
        model = QAgenerator()
        prompt = self.prompt_dict.get('GENERATE_QA')
        file = file.split('/')[-1].split('.')[:-1]
        file = ''.join(file)
        sum_qa = 0
        results, ans = await model.qa_generate(chunks, file, qa_count, prompt, self.llm, self.args.enhance)
        sum_qa = sum_qa + ans
        await model.output_results(results, file, self.args.output_path, self.args.output_format)
        return results, sum_qa

    async def document_governance(self, chunks, file):
        """
        文档治理
        """
        model = DocumentGovernance()
        if self.args.format:
            if self.args.format_mode == 'develop':
                prompt = self.prompt_dict.get('FORMAT_DOCUMENT_DEVELOP')
            elif self.args.format_mode == 'OPS':
                prompt = self.prompt_dict.get('FORMAT_DOCUMENT_OPS')
            else:
                prompt = self.prompt_dict.get('FORMAT_DOCUMENT_GENERAL')
            chunks = await model.format(chunks, prompt, self.llm, file)
        if self.args.standardize:
            chunks = await model.standardize(chunks)
        if self.args.unique:
            chunks = await model.unique(chunks)
        # print(chunks)
        # for chunk in chunks:
        #     print(chunk['text'])
        file = file.split('/')[-1].split('.')[0]
        model.output_chunks_to_file(self.args.output_path, chunks, file, self.args.output_format)
        # print(json.dumps(chunks, indent=4, ensure_ascii=False))
        return chunks

    async def embedding_training(self):
        model = EmbeddingTraining()
        model.run(self.args)
        return True

    def parse_arguments(self):
        """
        解析命令行参数，根据功能模式区分并解析其他参数。
        """
        # 创建参数解析器
        parser = argparse.ArgumentParser(description="文档处理工具：问答对生成、文档优化和embedding模型微调")

        # 创建子解析器
        subparsers = parser.add_subparsers(dest="mode", required=True,
                                           help="功能模式：qa_generate（问答对生成）、document_governance（文档优化）、embedding_training（embedding模型微调）")

        # 子解析器：qa_generate
        qa_parser = subparsers.add_parser("qa_generate", help="问答对生成")
        qa_parser.add_argument("--path", type=str, required=True,
                               help="待处理文件或目录路径（默认值：templetes）")
        qa_parser.add_argument("--output_path", type=str, required=True,
                               help="结果存放目录（默认值：output）")
        qa_parser.add_argument("--output_format", type=str, choices=["json", "yaml", "xlsx"],
                               default="json",
                               help="答案输出支持导出的格式（默认值：json）")
        qa_parser.add_argument("--enhance", action="store_true",
                               help="是否启用生成强化策略（默认值：False）")
        qa_parser.add_argument("--qa_count", type=int, default=1,
                               help="每片段问答对数量目标（默认值：1）")

        # 子解析器：document_governance
        doc_parser = subparsers.add_parser("document_governance", help="文档优化")
        doc_parser.add_argument("--path", type=str, required=True,
                                help="待处理文件或目录路径（默认值：templetes）")
        doc_parser.add_argument("--output_path", type=str, required=True,
                                help="结果存放目录（默认值：output）")
        doc_parser.add_argument("--unique", action="store_true",
                                help="是否启用去重策略（默认值：False）")
        doc_parser.add_argument("--standardize", action="store_true",
                                help="是否启用标准化策略（默认值：False）")
        doc_parser.add_argument("--format", action="store_true",
                                help="是否启用格式化策略（默认值：False）")
        doc_parser.add_argument("--output_format", type=str, choices=["md", "docx"],
                                default="json",
                                help="答案输出支持导出的格式（默认值：md）")
        doc_parser.add_argument("--format_mode", type=str, choices=["develop", "OPS", "general"], default="general",
                                help="格式化模式（默认值：general）")

        # 子解析器：embedding_training
        embedding_parser = subparsers.add_parser("embedding_training", help="embedding模型微调")
        embedding_parser.add_argument("--train_data", type=str, required=True,
                                      help="训练数据集路径")
        embedding_parser.add_argument("--test_data", type=str, required=True,
                                      help="测试数据集路径")
        embedding_parser.add_argument("--output_path", type=str, required=True,
                                      help="模型微调结果存放目录")
        embedding_parser.add_argument("--batch_size", type=int, default=32,
                                      help="每次迭代中使用的样本数量（默认值：32）")
        embedding_parser.add_argument("--learning_rate", type=float, default=5e-5,
                                      help="控制模型学习的速度（默认值：5e-5）")
        embedding_parser.add_argument("--deepspeed", type=str, default="utils/bge_finetune/ds_stage0.json",
                                      help="DeepSpeed 配置文件的路径（默认值：utils/bge_finetune/ds_stage0.json）")
        embedding_parser.add_argument("--epochs", type=int, default=10,
                                      help="整个训练过程中遍历数据集的次数（默认值：10）")
        embedding_parser.add_argument("--save_steps", type=int, default=1000,
                                      help="指定每多少个步骤保存一次模型检查点（默认值：1000）")
        embedding_parser.add_argument("--logging_steps", type=int, default=100,
                                      help="指定每多少个步骤输出一次日志信息（默认值：100）")
        embedding_parser.add_argument("--gpu_num", type=int, default=2,
                                      help="每个节点上使用的GPU数量（默认值：2）")
        embedding_parser.add_argument("--model_name_or_path", type=str, default="None",
                                      help="预训练模型的路径或名称")
        embedding_parser.add_argument("--temperature", type=float, default=0.02,
                                      help="对比学习中的温度参数（默认值：0.02）")
        embedding_parser.add_argument("--warmup", type=float, default=0.1,
                                      help="学习率预热的比例（默认值：0.1）")
        embedding_parser.add_argument("--tokens", type=int, default=512,
                                      help="每个样本的问答对token上限（默认值：512）")

        return parser.parse_args()


import asyncio

if __name__ == "__main__":
    asyncio.run(CLIService().solve())
