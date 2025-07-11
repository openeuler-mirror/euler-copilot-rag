from data_chain.parser.tools.token_tool import TokenTool
import json
import asyncio
from data_chain.config.config import config
from data_chain.llm.llm import LLM
import yaml


def load_yaml_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # 使用yaml.safe_load()方法加载YAML文件内容
            data = yaml.safe_load(file)
            return data
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到。")
    except yaml.YAMLError as e:
        print(f"解析YAML文件时出错: {e}")


def save_yaml_file(yaml_data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        yaml.dump(yaml_data, file, allow_unicode=True, default_flow_style=False)


# 示例：加载YAML文件
file_path = './data_chain/common/prompt.yaml'
yaml_data = load_yaml_file(file_path)
if yaml_data:
    print(yaml_data)
# yaml_data['LLM_PROMPT_TEMPLATE']=''
# yaml_data['INTENT_DETECT_PROMPT_TEMPLATE']=''
# yaml_data['OCR_ENHANCED_PROMPT']=''
# yaml_data['DETERMINE_ANSWER_AND_QUESTION']=''
# save_yaml_file(yaml_data,file_path)
# llm = LLM(
#     model_name=config['MODEL_NAME'],
#     openai_api_base=config['OPENAI_API_BASE'],
#     openai_api_key=config['OPENAI_API_KEY'],
#     request_timeout=config['REQUEST_TIMEOUT'],
#     max_tokens=config['MAX_TOKENS'],
#     temperature=config['TEMPERATURE'],
# )
# prompt_template = yaml_data['CONTENT_TO_ABSTRACT_PROMPT']
# content = '''在那遥远的山谷之中，有一片神秘而又美丽的森林。阳光透过茂密的枝叶，洒下一片片金色的光斑，仿佛是大自然精心编织的梦幻画卷。森林里，鸟儿欢快地歌唱，那清脆的歌声在林间回荡，传递着生机与活力。松鼠们在树枝间跳跃，敏捷的身影如同灵动的音符，谱写着森林的乐章。
# 沿着蜿蜒的小径前行，脚下的落叶发出沙沙的声响，仿佛在诉说着岁月的故事。路边的野花竞相开放，红的、黄的、紫的，五彩斑斓，散发着阵阵芬芳。蝴蝶在花丛中翩翩起舞，它们那绚丽的翅膀，如同绚丽的丝绸，在微风中轻轻摇曳。
# 不远处，一条清澈的小溪潺潺流淌。溪水从山间缓缓流下，清澈见底，能看到鱼儿在水中自由自在地游弋。溪水撞击着石头，发出叮叮咚咚的声音，宛如一首美妙的乐曲。溪边的石头上，长满了青苔，仿佛是大自然赋予的绿色绒毯。
# 在森林的深处，隐藏着一座古老的城堡。城堡的墙壁上爬满了藤蔓，仿佛是岁月留下的痕迹。城堡的大门紧闭，似乎隐藏着无数的秘密。传说中，这座城堡里住着一位美丽的公主，她被邪恶的巫师困在了这里，等待着勇敢的骑士前来解救。
# 有一天，一位年轻的骑士听闻了这个传说，决定踏上寻找公主的冒险之旅。他骑着一匹矫健的白马，手持长剑，穿过茂密的森林，越过湍急的河流，历经千辛万苦，终于来到了城堡的门前。
# 骑士用力地敲打着城堡的大门，然而，大门却纹丝不动。就在他感到绝望的时候，一只小精灵出现在他的面前。小精灵告诉他，要打开城堡的大门，必须找到三把神奇的钥匙。这三把钥匙分别隐藏在森林的三个不同的地方，只有集齐了这三把钥匙，才能打开城堡的大门。
# 骑士听了小精灵的话，毫不犹豫地踏上了寻找钥匙的旅程。他在森林里四处寻找，遇到了各种各样的困难和挑战。有时候，他会迷失在森林的深处，找不到方向；有时候，他会遇到凶猛的野兽，不得不与之搏斗。但是，骑士始终没有放弃，他坚信自己一定能够找到钥匙，救出公主。
# 终于，经过一番艰苦的努力，骑士找到了三把神奇的钥匙。他拿着钥匙，来到城堡的门前，将钥匙插入锁孔。随着一阵清脆的响声，城堡的大门缓缓打开。骑士走进城堡，沿着昏暗的走廊前行，终于在一间房间里找到了公主。
# 公主看到骑士，眼中闪烁着希望的光芒。她告诉骑士，自己被巫师困在这里已经很久了，一直在等待着有人来救她。骑士将公主带出城堡，骑着白马，离开了这片神秘的森林。
# 从此以后，骑士和公主过上了幸福的生活。他们的故事在这片土地上流传开来，成为了人们心中的一段佳话。
# 在这个世界上，还有许多未知的领域等待着我们去探索。也许，在那遥远的地方，还有更多神秘的故事等待着我们去发现。无论是茂密的森林，还是古老的城堡，都充满了无限的魅力。它们吸引着我们不断地前行，去追寻那未知的美好。
# 当夜幕降临，天空中繁星闪烁。那璀璨的星光，仿佛是大自然赋予我们的最美的礼物。在这宁静的夜晚，我们可以静静地聆听大自然的声音，感受它的神奇与美妙。
# 有时候，我们会在生活中遇到各种各样的困难和挫折。但是，只要我们像那位勇敢的骑士一样，坚持不懈，勇往直前，就一定能够克服困难，实现自己的梦想。生活就像一场冒险，充满了未知和挑战。我们要勇敢地面对生活中的一切，用自己的智慧和勇气去创造美好的未来。
# 在这个充满变化的世界里，我们要学会珍惜身边的一切。无论是亲人、朋友，还是那美丽的大自然，都是我们生活中不可或缺的一部分。我们要用心去感受他们的存在，用爱去呵护他们。
# 随着时间的推移，那片神秘的森林依然静静地矗立在那里。它见证了无数的故事，承载了无数的回忆。而那座古老的城堡，也依然默默地守护着那些神秘的传说。它们就像历史的见证者，诉说着过去的辉煌与沧桑。
# 我们生活在一个充满希望和梦想的时代。每一个人都有自己的追求和目标，都在为了实现自己的梦想而努力奋斗。无论是科学家、艺术家，还是普通的劳动者，都在各自的岗位上发光发热，为社会的发展做出自己的贡献。
# 在科技飞速发展的今天，我们的生活发生了翻天覆地的变化。互联网的普及，让我们的信息传播更加迅速和便捷。我们可以通过网络了解到世界各地的新闻和文化，与远方的朋友进行交流和沟通。科技的进步，也让我们的生活更加舒适和便利。我们有了更加先进的交通工具、更加便捷的通讯设备，以及更加高效的生活方式。
# 然而，科技的发展也带来了一些问题。比如，环境污染、能源危机等。这些问题不仅影响着我们的生活质量，也威胁着我们的未来。因此，我们在享受科技带来的便利的同时，也要关注环境保护和可持续发展。我们要努力寻找更加绿色、环保的生活方式，减少对自然资源的消耗和对环境的破坏。
# 除了科技的发展，文化的传承和创新也是我们生活中重要的一部分。每一个国家和民族都有自己独特的文化传统，这些文化传统是我们的精神财富，也是我们民族的灵魂。我们要传承和弘扬自己的文化传统，让它们在新的时代焕发出新的活力。同时，我们也要积极吸收和借鉴其他国家和民族的优秀文化成果，促进文化的交流和融合。
# 在教育方面，我们要注重培养学生的创新精神和实践能力。我们要让学生在学习知识的同时，学会思考、学会创新、学会实践。只有这样，我们才能培养出适应时代发展需要的高素质人才。
# 在人际交往中，我们要学会尊重他人、理解他人、关心他人。我们要建立良好的人际关系，与他人和谐相处。只有这样，我们才能在生活中感受到温暖和快乐。
# 总之，我们的生活是丰富多彩的，充满了无限的可能。我们要珍惜生活中的每一个瞬间，用积极的态度去面对生活中的一切。无论是成功还是失败，无论是欢笑还是泪水，都是我们生活中的宝贵财富。让我们一起努力，创造一个更加美好的未来！'''
# abstract = ''
# for i in range(10):
#     part = TokenTool.get_k_tokens_words_from_content(content, 100)
#     content = content[len(part):]
#     sys_call = prompt_template.format(content=part, abstract=abstract)
#     user_call = '请详细输出内容的摘要，不要输出其他内容'
#     abstract = asyncio.run(llm.nostream([], sys_call, user_call))
#     print(abstract)
