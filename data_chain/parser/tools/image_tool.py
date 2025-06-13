from data_chain.logger.logger import logger as logging


class ImageTool:
    @staticmethod
    def get_image_type(b):
        hex_str = bytes.hex(b).upper()
        if "FFD8FF" in hex_str:
            return "jpg"
        elif "89504E47" in hex_str:
            return "png"
        elif "47494638" in hex_str:
            return "gif"
        elif "424D" in hex_str:
            return "bmp"
        return "jpeg"
