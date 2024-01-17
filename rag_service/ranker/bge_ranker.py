from __future__ import annotations
from typing import Optional, Sequence
from langchain.schema import Document
from langchain.pydantic_v1 import Extra

from langchain.callbacks.manager import Callbacks
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor

from sentence_transformers import CrossEncoder
# from config import bge_reranker_large


class BgeRerank(BaseDocumentCompressor):
    model_name: str = '/root/zl/vectorize-agent/embedding_models/bge-reranker-large'
    """Model name to use for reranking."""
    top_n: int = 5
    """Number of documents to return."""
    model: CrossEncoder = CrossEncoder(model_name, device="cpu")
    """CrossEncoder instance to use for reranking."""

    def bge_rerank(self, query, docs):
        model_inputs = [[query, doc] for doc in docs]
        scores = self.model.predict(model_inputs)
        results = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        # return results[:self.top_n]
        return results

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid
        arbitrary_types_allowed = True

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        Compress documents using BAAI/bge-reranker models.

        Args:
            documents: A sequence of documents to compress.
            query: The query to use for compressing the documents.
            callbacks: Callbacks to run during the compression process.

        Returns:
            A sequence of compressed documents.
        """
        if len(documents) == 0:  # to avoid empty api call
            return []
        # doc_list = list(documents)
        _docs = [d[1] for d in documents]
        results = self.bge_rerank(query, _docs)
        final_results = []
        for r in results:
            doc = documents[r[0]]
            # doc.metadata["relevance_score"] = r[1]
            final_results.append(doc)
        final_results.sort(key=lambda x: x[0], reverse=True)
        return final_results
