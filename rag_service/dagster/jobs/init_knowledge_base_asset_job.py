from dagster import define_asset_job

from rag_service.dagster.assets.init_knowledge_base_asset import init_knowledge_base_asset

INIT_KNOWLEDGE_BASE_ASSET_JOB_NAME = 'init_knowledge_base_asset_job'
init_knowledge_base_asset_job = define_asset_job(
    INIT_KNOWLEDGE_BASE_ASSET_JOB_NAME,
    [init_knowledge_base_asset]
)
