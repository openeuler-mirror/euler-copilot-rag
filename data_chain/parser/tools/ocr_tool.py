from PIL import Image, ImageEnhance
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
    # 优化 OCR 参数配置
    model = PaddleOCR(
        det_model_dir=det_model_dir,
        rec_model_dir=rec_model_dir,
        cls_model_dir=cls_model_dir,
        use_angle_cls=True,
        use_space_char=True,
        det_db_thresh=0.3,       # 降低文本检测阈值，提高敏感度
        det_db_box_thresh=0.5,   # 调整文本框阈值
    )

    @staticmethod
    async def ocr_from_image(image: np.ndarray) -> list:
        try:

            # 尝试OCR识别
            ocr_result = OcrTool.model.ocr(image)

            # 如果第一次尝试失败，尝试不同的参数配置
            if ocr_result is None or len(ocr_result) == 0 or ocr_result[0] is None:
                logging.warning("[OCRTool] 第一次OCR尝试失败，尝试降低阈值...")
                # 创建临时OCR实例，使用更低的阈值
                temp_ocr = PaddleOCR(
                    det_model_dir=OcrTool.det_model_dir,
                    rec_model_dir=OcrTool.rec_model_dir,
                    cls_model_dir=OcrTool.cls_model_dir,
                    use_angle_cls=True,
                    use_space_char=True,
                    det_db_thresh=0.2,       # 更低的检测阈值
                    det_db_box_thresh=0.4,   # 更低的文本框阈值
                )
                ocr_result = temp_ocr.ocr(image)

            # 记录OCR结果状态
            if ocr_result is None or len(ocr_result) == 0 or ocr_result[0] is None:
                logging.warning("[OCRTool] 图片无法识别文本")
                return None

            return ocr_result
        except Exception as e:
            err = f"[OCRTool] OCR识别失败: {e}"
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
