# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from dagster import define_asset_job

from rag_service.dagster.assets.updated_knowledge_base_asset import update_knowledge_base_asset

UPDATE_KNOWLEDGE_BASE_ASSET_JOB_NAME = 'update_knowledge_base_asset_job'
update_knowledge_base_asset_job = define_asset_job(
    UPDATE_KNOWLEDGE_BASE_ASSET_JOB_NAME,
    [update_knowledge_base_asset]
)
