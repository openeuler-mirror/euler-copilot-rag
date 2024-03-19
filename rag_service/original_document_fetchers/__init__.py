import importlib
from pathlib import Path
from typing import Dict, TypeVar

from rag_service.models.enums import AssetType
from rag_service.original_document_fetchers.base import BaseFetcher

Fetcher = TypeVar('Fetcher', bound=BaseFetcher)

_FETCHER_REGISTRY: Dict[AssetType, Fetcher] = {}

for path in sorted(Path(__file__).parent.glob('[!_]*')):
    module = f'{__package__}.{path.stem}'
    importlib.import_module(module)


def select_fetcher(asset_type: AssetType) -> Fetcher:
    return _FETCHER_REGISTRY[asset_type]
