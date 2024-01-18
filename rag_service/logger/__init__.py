import logging
from enum import Enum, auto
from pathlib import Path
from typing import Dict

from concurrent_log_handler import ConcurrentTimedRotatingFileHandler

from rag_service.env import EnvEnum
from rag_service.env_config import RAG_ENV


class Module(Enum):
    APP = auto()
    DAGSTER = auto()
    LLM_RESULT = auto()
    VECTORIZATION = auto()


if RAG_ENV == EnvEnum.DEV.name:
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
else:
    LOG_DIR = Path.home().absolute() / 'rag_logs'
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers = {
        'default': {
            'formatter': 'default',
            'class': 'concurrent_log_handler.ConcurrentTimedRotatingFileHandler',
            'filename': str(LOG_DIR / 'uvicorn.log'),
            'backupCount': 30,
            'when': 'MIDNIGHT'
        }
    }
    _module_to_log_file: Dict[Module, Path] = {
        Module.APP: LOG_DIR / 'app.log',
        Module.LLM_RESULT: LOG_DIR / 'llm_result.log',
        Module.VECTORIZATION: LOG_DIR / 'vectorization.log'
    }

LOG_FORMAT = '[{asctime}][{levelname}][{name}][P{process}][T{thread}][{message}][{funcName}({filename}:{lineno})]'
UVICORN_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            '()': 'logging.Formatter',
            'fmt': LOG_FORMAT,
            'style': '{'
        }
    },
    "handlers": handlers,
    'loggers': {
        'uvicorn': {'handlers': ['default'], 'level': 'INFO', 'propagate': False},
        'uvicorn.error': {'handlers': ['default'], 'level': 'INFO', 'propagate': False},
        'uvicorn.access': {'handlers': ['default'], 'level': 'INFO', 'propagate': False},
    },
}

_name_to_level: Dict[str, int] = {
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
    'ERROR': logging.ERROR,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET,
}


def get_logger(log_level: str = 'INFO', module: Module = Module.APP) -> logging.Logger:
    logger = logging.getLogger(module.name)
    if not logger.handlers:
        logger.setLevel(_name_to_level.get(log_level.upper(), logging.INFO))
        if RAG_ENV != EnvEnum.DEV.name:
            _set_handler(logger, str(_module_to_log_file[module]))
    return logger


def _set_handler(logger: logging.Logger, log_file_path: str) -> None:
    rotate_handler = ConcurrentTimedRotatingFileHandler(filename=log_file_path, when='MIDNIGHT', backupCount=30)
    formatter = logging.Formatter(fmt=LOG_FORMAT, style='{')
    rotate_handler.setFormatter(formatter)
    logger.addHandler(rotate_handler)
