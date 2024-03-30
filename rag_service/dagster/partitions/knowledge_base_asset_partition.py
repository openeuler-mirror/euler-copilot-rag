# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from dagster import DynamicPartitionsDefinition, partitioned_config

knowledge_base_asset_partitions_def = DynamicPartitionsDefinition(name="knowledge_base_asset")


@partitioned_config(partitions_def=knowledge_base_asset_partitions_def)
def knowledge_base_asset_partitions_def_config(partition_key):
    from rag_service.dagster.jobs.delete_knowledge_base_asset_job import delete_knowledge_base_asset_partition

    return {
        "ops": {
            delete_knowledge_base_asset_partition.name: {
                "config": partition_key
            }
        }
    }
