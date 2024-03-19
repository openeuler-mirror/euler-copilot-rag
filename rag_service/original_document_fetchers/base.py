from abc import ABC, abstractmethod
from typing import Any, Generator, Set

from rag_service.models.enums import AssetType
from rag_service.models.generic.models import OriginalDocument


class BaseFetcher(ABC):
    def __init_subclass__(cls, asset_types: Set[AssetType], **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        from rag_service.original_document_fetchers import _FETCHER_REGISTRY

        for asset_type in asset_types:
            _FETCHER_REGISTRY[asset_type] = cls

    def __init__(self, asset_uri: str, asset_root_dir: str, asset_type: AssetType) -> None:
        self._asset_uri = asset_uri
        self._asset_root_dir = asset_root_dir
        self._asset_type = asset_type

    @abstractmethod
    def fetch(self) -> Generator[OriginalDocument, None, None]:
        raise NotImplementedError
