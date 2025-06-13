from utils.my_tools.llm import LLM
from utils.config.config import config
import asyncio

llm = LLM(model_name=config["MODEL_NAME"],
                       openai_api_base=config["OPENAI_API_BASE"],
                       openai_api_key=config["OPENAI_API_KEY"],
                       max_tokens=config["MAX_TOKENS"],
                       request_timeout=60,
                       temperature=0.3)

async def chat_with_llm(args, losses):
    """
    对于给定的文本，通过llm按照prompt的格式
    params:
    - llm: LLm
    - text: str
    - prompt: str
    return:
    - qa_pairs: list[dict]

    """
    user_call = (f"给出模型微调参数为{args}、模型训练的过程和结果为{losses}，请问如何改进训练参数")
    prompt = (f"""当训练过程中 loss 出现以下情况时，更换数据或调整参数的方案：
Loss 不下降：

更换 train_data，增加多样性或清洗噪声数据。

调整 learning_rate，尝试更小或更大的值。

增加 epochs 或 batch_size。

Loss 波动大：

检查 train_data 质量，去除异常样本。

调整 temperature 或 warmup_ratio，稳定训练过程。

Loss 下降过快：

增加数据量或调整 train_group_size。

降低 learning_rate，避免过拟合。

Loss 为 NaN：

检查 train_data 格式，确保无异常值。

调整 gradient_checkpointing 或 deepspeed 配置。""")
    answer = await llm.nostream([], prompt, user_call)

    return answer

with open('./temp/args.txt', 'r') as file:
    args = file.read()
with open('./temp/losses.txt', 'r') as file:
    selected_losses = file.read()

print(asyncio.run(chat_with_llm(args, selected_losses)))