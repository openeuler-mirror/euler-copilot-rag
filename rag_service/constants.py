# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from pathlib import Path

EMBEDDING_MODEL_BASE_DIR = Path(__file__).parent.parent / 'embedding_models'
DELETE_ORIGINAL_DOCUMENT_METADATA = 'delete_original_document_metadata.json'
DELETE_ORIGINAL_DOCUMENT_METADATA_KEY = 'user_uploaded_deleted_documents'

DEFAULT_UPDATE_TIME_INTERVAL_SECOND = 7 * 24 * 3600