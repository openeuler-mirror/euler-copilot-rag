import yaml
from utils.my_tools.logger import logger as logging
from paddleocr import PaddleOCR
from utils.config.config import config
from utils.parser.tools.split import split_tools


class BaseOCR:

    def __init__(self, llm=None, llm_max_tokens=None, method='general'):
        # 指定模型文件的路径
        det_model_dir = 'utils/parser/model/ocr/ch_PP-OCRv4_det_infer'
        rec_model_dir = 'utils/parser/model/ocr/ch_PP-OCRv4_rec_infer'
        cls_model_dir = 'utils/parser/model/ocr/ch_ppocr_mobile_v2.0_cls_infer'

        # 创建 PaddleOCR 实例，指定模型路径
        self.model = PaddleOCR(
            det_model_dir=det_model_dir,
            rec_model_dir=rec_model_dir,
            cls_model_dir=cls_model_dir,
            use_angle_cls=True,  # 是否使用角度分类模型
            use_space_char=True  # 是否使用空格字符
        )
        self.llm = llm
        if llm is None and method == 'enhanced':
            method = 'ocr'
        else:
            self.max_tokens = llm_max_tokens
        self.method = method

    def ocr(self, image):
        """
        ocr识别文字
        参数：
        image:图像文件
        **kwargs:可选参数，如语言、gpu
        返回：
        一个list,包含了所有识别出的文字以及对应坐标
        """
        try:
            # get my_tools
            results = self.model.ocr(image)
            logging.info(f"OCR job down {results}")
            return results
        except Exception as e:
            logging.error(f"OCR job error {e}")
            raise e

    @staticmethod
    def get_text_from_ocr_results(ocr_results):
        results = ''
        if ocr_results[0] is None:
            return ''
        try:
            for result in ocr_results[0][0]:
                results += result[1][0]
            return results
        except Exception as e:
            logging.error(f'Get text from ocr result failed with {e}')
            return ''

    @staticmethod
    def split_list(image_result, max_tokens):
        """
        分句，不超过Tokens数量
        """
        sum_tokens = 0
        result = []
        temp = []
        for sentences in image_result[0]:
            if sentences is not None and len(sentences) > 0:
                tokens = split_tools.get_tokens(sentences)
                if sum_tokens + tokens > max_tokens:
                    result.append(temp)
                    temp = [sentences]
                    sum_tokens = tokens
                else:
                    temp.append(sentences)
                    sum_tokens += tokens
        if temp:
            result.append(temp)
        return result

    @staticmethod
    def get_prompt_dict():
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            return prompt_dict
        except Exception as e:
            logging.error(f'Get prompt failed : {e}')
            raise e

    async def improve(self, image_results, text):
        """
        llm强化接口
        参数：
        - image_results:ocr识别结果,包含了文字坐标、内容、置信度
        - text：图片组对应的前后文
        """
        try:
            user_call = '请详细输出图片的总结，不要输出其他内容'
            split_images = []
            max_tokens = self.max_tokens // 2
            for image in image_results:
                split_result = self.split_list(image, max_tokens)
                split_images.append(split_result)
            front_text = text
            front_image_description = ""
            front_part_description = ""
            prompt_dict = self.get_prompt_dict()
            for image in split_images:
                for part in image:
                    prompt = prompt_dict.get('OCR_ENHANCED_PROMPT', '')
                    try:
                        prompt = prompt.format(
                            front_text=front_text,
                            front_image_description=front_image_description,
                            front_part_description=front_part_description,
                            part=part)
                        front_part_description = await self.llm.nostream([], prompt, user_call)
                    except Exception as e:
                        raise e
                front_image_description = front_part_description
            answer = front_image_description
            return answer
        except Exception as e:
            raise e

    async def run(self, image, text):
        """
        执行ocr的接口
        输入：
        image：图像文件
        """
        method = self.method
        if not isinstance(image, list):
            image = [image]

        image_results = self.process_images(image)
        results = await self.generate_results(method, image_results, text)

        return results

    def process_images(self, images):
        image_results = []
        for every_image in images:
            try:
                ocr_result = self.ocr(every_image)
                image_results.append(ocr_result)
            except Exception as e:
                # 记录异常信息，可以选择日志记录或其他方式
                logging.error(f"Error processing image: {e}")
        return image_results

    async def generate_results(self, method, image_results, text):
        if method == 'ocr':
            results = self.get_text_from_ocr_results(image_results)
            return f'{results}'
        elif method == 'enhanced':
            try:
                results = await self.improve(image_results, text)
                if len(results.strip()) == 0:
                    return self.get_text_from_ocr_results(image_results)
                return results
            except Exception as e:
                logging.error(f"LLM ERROR with: {e}")
                return self.get_text_from_ocr_results(image_results)
        else:
            return ""
