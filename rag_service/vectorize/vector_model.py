from langchain.embeddings import HuggingFaceEmbeddings

from rag_service.config import EMBEDDING_DEVICE
from rag_service.constants import EMBEDDING_MODEL_BASE_DIR
from rag_service.models.enums import EmbeddingModel


class VectorModel:
    def __init__(
            self,
            embedding_model: EmbeddingModel = EmbeddingModel.BGE_LARGE_ZH,
            embedding_device: str = EMBEDDING_DEVICE
    ):
        """
        初始化单例
        :param embedding_model:     模型地址
        :param embedding_device:    运行方式
        :return:
        """
        self.embeddings = HuggingFaceEmbeddings(
            model_name=str(EMBEDDING_MODEL_BASE_DIR / embedding_model.value),
            model_kwargs={'device': embedding_device},
            encode_kwargs={"show_progress_bar": False}
        )
        self.dim = self.embeddings.client[1].word_embedding_dimension
        self.embedding_function = self.embeddings.embed_documents
