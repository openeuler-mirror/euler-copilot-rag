from dagster import load_assets_from_package_module, Definitions

from rag_service.dagster import assets
from rag_service.dagster.jobs.init_knowledge_base_asset_job import init_knowledge_base_asset_job
from rag_service.dagster.jobs.delete_knowledge_base_asset_job import delete_knowledge_base_asset_job
from rag_service.dagster.jobs.update_knowledge_base_asset_job import update_knowledge_base_asset_job
from rag_service.dagster.sensors.init_knowledge_base_asset_sensor import init_knowledge_base_asset_sensor
from rag_service.dagster.sensors.update_knowledge_base_asset_sensor import update_knowledge_base_asset_sensor
from rag_service.dagster.sensors.delete_knowledge_base_asset_sensor import delete_knowledge_base_asset_sensor

knowledge_base_assets = load_assets_from_package_module(
    assets,
    group_name="knowledge_base_assets",
)

defs = Definitions(
    assets=knowledge_base_assets,
    jobs=[init_knowledge_base_asset_job, delete_knowledge_base_asset_job, update_knowledge_base_asset_job],
    sensors=[init_knowledge_base_asset_sensor,
             update_knowledge_base_asset_sensor, delete_knowledge_base_asset_sensor]
)
