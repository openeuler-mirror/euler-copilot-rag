from pathlib import Path
from typing import Tuple

from rag_service.config import DATA_DIR
from rag_service.models.database.models import KnowledgeBaseAsset


def get_knowledge_base_asset_root_dir(knowledge_base_serial_number: str, asset_name: str) -> Path:
    return Path(DATA_DIR) / knowledge_base_serial_number / asset_name


def generate_asset_partition_key(knowledge_base_asset: KnowledgeBaseAsset) -> str:
    return f'{knowledge_base_asset.knowledge_base.sn}-{knowledge_base_asset.name}'


def parse_asset_partition_key(partition_key: str) -> Tuple[str, str]:
    knowledge_base_serial_number, knowledge_base_asset_name = partition_key.rsplit('-', 1)
    return knowledge_base_serial_number, knowledge_base_asset_name
