# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
__all__ = ['routers']

import glob
import importlib
from typing import List
from pathlib import Path

from fastapi import APIRouter


routers: List[APIRouter] = []

for f in [f for f in glob.glob(f'{Path(__file__).parent}/*.py') if not f.endswith('__init__.py')]:
    module = importlib.import_module(f'{__package__}.{Path(f).stem}')
    if isinstance(module.router, APIRouter):
        routers.append(module.router)
