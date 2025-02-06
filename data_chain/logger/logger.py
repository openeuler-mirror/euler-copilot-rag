import logging
from data_chain.config.config import config

class LoggerSingleton:
    _instance = None

    @staticmethod
    def get_logger():
        if LoggerSingleton._instance is None:
            LoggerSingleton._instance = LoggerSingleton._initialize_logger()
        return LoggerSingleton._instance

    @staticmethod
    def _initialize_logger():
        # 创建一个 logger 对象
        logger = logging.getLogger('my_logger')
        logger.setLevel(logging.INFO)

        # 禁用父级 logger 的传播
        logger.propagate = False

        # 创建一个 formatter 对象
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s')

        # 根据配置选择添加不同的 handler
        if config['LOG_METHOD'] != 'stdout':
            # 添加 FileHandler 到 logger
            file_handler = logging.FileHandler('app.log')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        else:
            # 添加 StreamHandler 到 logger
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        return logger

# 使用单例模式获取 logger
logger = LoggerSingleton.get_logger()