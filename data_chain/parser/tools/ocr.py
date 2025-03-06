import yaml
from paddleocr import PaddleOCR

from data_chain.logger.logger import logger as logging
from data_chain.config.config import config
from data_chain.parser.tools.split import split_tools


class BaseOCR:

    def __init__(self, llm=None, method='general'):
        # 指定模型文件的路径
        det_model_dir = 'data_chain/parser/model/ocr/ch_PP-OCRv4_det_infer'
        rec_model_dir = 'data_chain/parser/model/ocr/ch_PP-OCRv4_rec_infer'
        cls_model_dir = 'data_chain/parser/model/ocr/ch_ppocr_mobile_v2.0_cls_infer'

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
            self.max_tokens = 1024
        self.method = method

    async def ocr_from_image(self, image):
        """
        图片ocr接口
        参数：
        image图片
        """
        try:
            ocr_result = self.model.ocr(image)
            if ocr_result is None or ocr_result[0] is None:
                return None
            return ocr_result
        except Exception as e:
            logging.error(f"Ocr from image failed due to: {e}")
            return None

    async def merge_text_from_ocr_result(self, ocr_result):
        """
        ocr结果文字内容合并接口
        参数：
        ocr_result:ocr识别结果,包含了文字坐标、内容、置信度
        """
        text = ''
        try:
            for _ in ocr_result[0]:
                text += str(_[1][0])
            return text
        except Exception as e:
            logging.error(f'Get text from ocr result failed due to: {e}')
            return ''

    async def cut_ocr_result_in_part(self, ocr_result, max_tokens=1024):
        """
        ocr结果切割接口
        参数：
        ocr_result:ocr识别结果,包含了文字坐标、内容、置信度
        max_tokens:最大token数
        """
        tokens = 0
        ocr_result_part = None
        ocr_result_parts = []
        for _ in ocr_result[0]:
            if _ is not None and len(_) > 0:
                sub_tokens = split_tools.get_tokens(str(_))
                if tokens + sub_tokens > max_tokens:
                    ocr_result_parts.append(ocr_result_part)
                    ocr_result_part = [_]
                    tokens += sub_tokens
                else:
                    ocr_result_parts.append(_)
                    tokens += sub_tokens
        if len(ocr_result_parts) > 0:
            ocr_result_parts.append(ocr_result_part)
        return ocr_result_parts

    async def enhance_ocr_result(self, ocr_result, image_related_text):
        """
        ocr结果强化接口
        参数：
        ocr_result:ocr识别结果,包含了文字坐标、内容、置信度
        image_related_text：图片组对应的前后文
        """
        try:
            try:
                with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                    prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
                    prompt_template = prompt_dict.get('OCR_ENHANCED_PROMPT', '')
            except Exception as e:
                logging.error(f'Get prompt template failed due to :{e}')
                return ''
            pre_part_description = ""
            ocr_result_parts = await self.cut_ocr_result_in_part(ocr_result, self.max_tokens // 5*2)
            user_call = '请详细输出图片的摘要，不要输出其他内容'
            for part in ocr_result_parts:
                pre_part_description_cp = pre_part_description
                try:
                    prompt = prompt_template.format(
                        image_related_text=image_related_text,
                        pre_part_description=pre_part_description,
                        part=part)
                    pre_part_description = await self.llm.nostream([], prompt, user_call)
                except Exception as e:
                    logging.error(f"OCR result part enhance failed due to: {e}")
                    pre_part_description = pre_part_description_cp
            return pre_part_description
        except Exception as e:
            logging.error(f'OCR result enhance failed due to: {e}')
            return ""

    async def get_text_from_image(self, ocr_result, image_related_text):
        """
        从image中提取文字的接口
        输入：
        ocr_result: ocr结果
        image_related_text: 图片相关文字
        """
        if self.method == 'ocr':
            text = await self.merge_text_from_ocr_result(ocr_result)
            return text
        elif self.method == 'enhanced':
            try:
                text = await self.enhance_ocr_result(ocr_result, image_related_text)
                if len(text) == 0:
                    text = await self.merge_text_from_ocr_result(ocr_result)
            except Exception as e:
                logging.error(f"LLM ERROR with: {e}")
                text = await self.merge_text_from_ocr_result(ocr_result)
            return text
        else:
            return ""

    async def image_to_text(self, image, image_related_text=''):
        """
        执行ocr的接口
        输入：
        image：图像文件
        image_related_text：图像相关的文本
        """
        ocr_result = await self.ocr_from_image(image)
        if ocr_result is None:
            return ""
        text = await self.get_text_from_image(ocr_result, image_related_text)
        return text
