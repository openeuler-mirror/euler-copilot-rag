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
def save_yaml_file(yaml_data,file_path):
    with open('prompt.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(yaml_data, file, allow_unicode=True, default_flow_style=False)
# 示例：加载YAML文件
file_path = 'prompt.yaml'
yaml_data = load_yaml_file(file_path)
if yaml_data:
    print(yaml_data)
# yaml_data['LLM_PROMPT_TEMPLATE']=''
# yaml_data['INTENT_DETECT_PROMPT_TEMPLATE']=''
# yaml_data['OCR_ENHANCED_PROMPT']=''
# yaml_data['DETERMINE_ANSWER_AND_QUESTION']=''
save_yaml_file(yaml_data,file_path)