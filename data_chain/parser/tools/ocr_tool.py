from PIL import Image
import asyncio
import yaml
from paddleocr import PaddleOCR
import numpy as np
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.logger.logger import logger as logging
from data_chain.config.config import config
from data_chain.llm.llm import LLM


class OcrTool:
    det_model_dir = 'data_chain/parser/model/ocr/ch_PP-OCRv4_det_infer'
    rec_model_dir = 'data_chain/parser/model/ocr/ch_PP-OCRv4_rec_infer'
    cls_model_dir = 'data_chain/parser/model/ocr/ch_ppocr_mobile_v2.0_cls_infer'
    model = PaddleOCR(
        det_model_dir=det_model_dir,
        rec_model_dir=rec_model_dir,
        cls_model_dir=cls_model_dir,
        use_angle_cls=True,  # 是否使用角度分类模型
        use_space_char=True  # 是否使用空格字符
    )

    @staticmethod
    async def ocr_from_image(image: np.ndarray) -> list:
        try:
            ocr_result = OcrTool.model.ocr(image)
            if ocr_result is None or ocr_result[0] is None:
                return None
            return ocr_result
        except Exception as e:
            err = f"[OCRTool] OCR识别失败 {e}"
            logging.exception(err)
            return None

    @staticmethod
    async def merge_text_from_ocr_result(ocr_result: list) -> str:
        text = ''
        try:
            for _ in ocr_result[0]:
                text += str(_[1][0])
            return text
        except Exception as e:
            err = f"[OCRTool] OCR结果合并失败 {e}"
            logging.exception(err)
            return ''

    @staticmethod
    async def enhance_ocr_result(ocr_result, image_related_text='', llm: LLM = None) -> str:
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
                prompt_template = prompt_dict.get('OCR_ENHANCED_PROMPT', '')
            pre_part_description = ""
            token_limit = llm.max_tokens//2
            image_related_text = TokenTool.get_k_tokens_words_from_content(image_related_text, token_limit)
            ocr_result_parts = TokenTool.split_str_with_slide_window(str(ocr_result), token_limit)
            user_call = '请详细输出图片的摘要，不要输出其他内容'
            for part in ocr_result_parts:
                pre_part_description_cp = pre_part_description
                try:
                    prompt = prompt_template.format(
                        image_related_text=image_related_text,
                        pre_part_description=pre_part_description,
                        part=part)
                    pre_part_description = await llm.nostream([], prompt, user_call)
                except Exception as e:
                    err = f"[OCRTool] OCR增强失败 {e}"
                    logging.exception(err)
                    pre_part_description = pre_part_description_cp
            return pre_part_description
        except Exception as e:
            err = f"[OCRTool] OCR增强失败 {e}"
            logging.exception(err)
            return OcrTool.merge_text_from_ocr_result(ocr_result)

    @staticmethod
    async def image_to_text(image: np.ndarray, image_related_text: str = '', llm: LLM = None) -> str:
        try:
            ocr_result = await OcrTool.ocr_from_image(image)
            if ocr_result is None:
                return ''
            if llm is None:
                text = await OcrTool.merge_text_from_ocr_result(ocr_result)
            else:
                text = await OcrTool.enhance_ocr_result(ocr_result, image_related_text, llm)
            return text
        except Exception as e:
            err = f"[OCRTool] 图片转文本失败 {e}"
            logging.exception(err)
            return ''
