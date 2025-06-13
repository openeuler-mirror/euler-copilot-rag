import os

import numpy as np
import subprocess
class EmbeddingTraining:

    @staticmethod
    def parser(args):
        # 定义要执行的命令
        command = [
            "torchrun",
            "--nproc_per_node", str(args.gpu_num),
            "-m", "FlagEmbedding.finetune.embedder.encoder_only.base",
            "--model_name_or_path", str(args.model_name_or_path),
            "--cache_dir", "./cache/model",
            "--train_data", str(args.train_data),
            "--cache_path", "./cache/data",
            "--train_group_size", "8",
            "--query_max_len", str(args.tokens),
            "--passage_max_len", str(args.tokens),
            "--pad_to_multiple_of", "8",
            "--query_instruction_for_retrieval", "\"Represent this sentence for searching relevant passages: \"",
            "--query_instruction_format", "{}{}",
            "--knowledge_distillation", "False",
            "--output_dir", str(args.output_path),
            "--overwrite_output_dir",
            "--learning_rate", str(args.learning_rate),
            "--num_train_epochs", str(args.epochs),
            "--per_device_train_batch_size", str(args.batch_size),
            "--dataloader_drop_last", "True",
            "--warmup_ratio", str(args.warmup),
            "--gradient_checkpointing",
            "--deepspeed", str(args.deepspeed),
            "--logging_steps", str(args.logging_steps),
            "--save_steps", str(args.save_steps),
            "--negatives_cross_device",
            "--temperature", str(args.temperature),
            "--sentence_pooling_method", "cls",
            "--normalize_embeddings", "True",
            "--kd_loss_type", "kl_div",
            "--ddp_find_unused_parameters=False",
            '>', './logs/embedding/temp.log'  # 将输出重定向到 temp.log
        ]
        return command

    # 执行 torchrun 命令
    @staticmethod
    def run_command(command):
        try:
            # 使用 subprocess 执行命令并捕获输出
            print("running...")
            result = subprocess.run(' '.join(command), shell=True, check=True)
            print("running successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error occurred during running: {e}")
            return False
        return True

    # 执行 get_reports.py 脚本
    def run(self, args):
        if not os.path.exists("./logs"):
            os.mkdir("./logs")
        if not os.path.exists("./logs/embedding"):
            os.mkdir("./logs/embedding")
        if not self.run_command(self.parser(args)):
            return
        if not self.run_command(["python", "utils/my_tools/bge_finetune/eval.py", "--encoder", f"{args.model_name_or_path}",
                                 "--test_data", f"{args.test_data}", '>', './logs/embedding/base.log']):
            return
        if not self.run_command(["python", "utils/my_tools/bge_finetune/eval.py", "--encoder", f"{args.output_path}",
                                 "--test_data", f"{args.test_data}", '>', './logs/embedding/final.log']):
            return
        if not os.path.exists('./temp'):
            os.mkdir('./temp')
        with open('./temp/args.txt','w') as file:
            file.write(f'{args}')
        if not self.run_command(["python", "utils/my_tools/bge_finetune/get_report.py"]):
            return
        if not self.run_command(["python", "utils/my_tools/bge_finetune/how_to_better.py"]):
            return
        print("Embedding fine tuning down")



if __name__ == '__main__':
    EmbeddingTraining.run()