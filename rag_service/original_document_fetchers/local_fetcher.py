# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import json
import datetime
from pathlib import Path
from typing import Generator, List, Tuple

from rag_service.models.enums import AssetType
from rag_service.models.generic import OriginalDocument
from rag_service.models.database import KnowledgeBaseAsset
from rag_service.original_document_fetchers.base import BaseFetcher
from rag_service.constants import DELETE_ORIGINAL_DOCUMENT_METADATA, DELETE_ORIGINAL_DOCUMENT_METADATA_KEY


class LocalFetcher(BaseFetcher, asset_types={AssetType.UPLOADED_ASSET}):
    def fetch(self) -> Generator[OriginalDocument, None, None]:
        root_path = Path(self._asset_root_dir)

        for root, _, files in os.walk(root_path):
            for file in files:
                path = Path(root) / file
                source_str = str(path.relative_to(root_path))
                yield OriginalDocument(
                    uri=str(path),
                    source=source_str,
                    mtime=datetime.datetime.fromtimestamp(path.lstat().st_mtime)
                )

    def update_fetch(self, knowledge_base_asset: KnowledgeBaseAsset) -> Tuple[
            List[str], List[str], List[OriginalDocument]]:
        root_path = Path(self._asset_root_dir)
        uploaded_original_document_sources: List[str] = []
        uploaded_original_documents: List[OriginalDocument] = []

        for root, _, files in os.walk(root_path):
            for file in files:
                if file == DELETE_ORIGINAL_DOCUMENT_METADATA:
                    continue
                path = Path(root) / file
                uploaded_original_document_sources.append(str(path.relative_to(root_path)))
                uploaded_original_documents.append(
                    OriginalDocument(
                        uri=str(path),
                        source=str(path.relative_to(root_path)),
                        mtime=datetime.datetime.fromtimestamp(path.lstat().st_mtime)
                    )
                )
        delete_original_document_metadata_path = root_path / DELETE_ORIGINAL_DOCUMENT_METADATA
        with delete_original_document_metadata_path.open('r', encoding='utf-8') as file_content:
            delete_original_document_dict = json.load(file_content)
            delete_original_document_sources = delete_original_document_dict[DELETE_ORIGINAL_DOCUMENT_METADATA_KEY]
        return delete_original_document_sources, uploaded_original_document_sources, uploaded_original_documents
