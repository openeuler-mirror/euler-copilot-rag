import shutil
import os
import traceback
from data_chain.logger.logger import logger as logging
from data_chain.apps.service.embedding_service import Vectorize
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.model_manager import ModelManager
from data_chain.models.constant import OssConstant, embedding_model_out_dimensions
from data_chain.parser.handler.docx_parser import DocxService
from data_chain.parser.handler.html_parser import HtmlService
from data_chain.parser.handler.xlsx_parser import XlsxService
from data_chain.parser.handler.txt_parser import TxtService
from data_chain.parser.handler.pdf_parser import PdfService
from data_chain.parser.handler.md_parser import MdService
from data_chain.parser.handler.doc_parser import DocService
from data_chain.stores.postgres.postgres import DocumentEntity, ChunkEntity, ChunkLinkEntity, PostgresDB, ImageEntity
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.chunk_manager import ChunkManager, ChunkLinkManager
from data_chain.manager.image_manager import ImageManager
from data_chain.stores.minio.minio import MinIO
from data_chain.manager.vector_items_manager import VectorItemsManager


class ParserService:
    # TODO:把user_id和doc_id提取到这层
    def __init__(self):
        self.doc = None

    async def parser(self, doc_id, file_path):
        model_map = {
            ".docx": DocxService,
            ".doc": DocService,
            ".txt": TxtService,
            ".pdf": PdfService,
            ".xlsx": XlsxService,
            ".md": MdService,
            ".html": HtmlService,
        }
        self.doc = await DocumentManager.select_by_id(doc_id)
        file_extension = self.doc.extension
        try:
            if file_extension in model_map:
                model = model_map[file_extension]()  # 判断文件类型
                llm_entity = await ModelManager.select_by_user_id(self.doc.user_id)
                await model.init_service(llm_entity=llm_entity,
                                         tokens=self.doc.chunk_size,
                                         parser_method=self.doc.parser_method)
                chunk_list, chunk_link_list, image_chunks = await model.parser(file_path)
                for chunk in chunk_list:
                    chunk['doc_id'] = doc_id
                    chunk['user_id'] = self.doc.user_id
                    chunk['kb_id'] = self.doc.kb_id
                for image_chunk in image_chunks:
                    image_chunk['doc_id'] = doc_id
                    image_chunk['user_id'] = self.doc.user_id
            else:
                logging.error(f"No service available for file type: {file_extension}")
                return {"chunk_list": [], "chunk_link_list": [], "image_chunks": []}
        except Exception as e:
            logging.error(f'Fail with exception:{e}')
            logging.error(f'Fail with exception traceback:{traceback.format_exc()}')
            raise e
        return {"chunk_list": chunk_list, "chunk_link_list": chunk_link_list, "image_chunks": image_chunks}

    @staticmethod
    async def upload_chunks_to_pg(chunks):
        if len(chunks)==0:
            return
        try:
            image_entity_list=await ImageManager.query_image_by_doc_id(chunks[0]['doc_id'])
            for image_entity in image_entity_list:
                MinIO.delete_object(OssConstant.MINIO_BUCKET_PICTURE, str(image_entity.id))
            await ChunkManager.delete_by_document_ids([chunks[0]['doc_id']])
        except Exception as e:
            logging.error(f"Failed to delete chunk: {e}")
            raise e
        try:
            for chunk in chunks:
                chunk_entity = ChunkEntity(
                    id=chunk['id'],
                    kb_id=chunk['kb_id'],
                    user_id=chunk['user_id'],
                    document_id=chunk['doc_id'],
                    text=chunk['text'],
                    tokens=chunk['tokens'],
                    type=chunk['type'],
                    global_offset=chunk['global_offset'],
                    local_offset=chunk['local_offset'],
                    enabled=chunk['enabled'],
                    status=chunk['status']
                )
                try:
                    await ChunkManager.insert_chunk(chunk_entity)
                except Exception as e:
                    logging.error(f"Failed to upload chunk: {e}")
                    raise e
        except Exception as e:
            logging.error(f"Failed to upload chunk: {e}")

    @staticmethod
    async def upload_chunk_links_to_pg(chunk_links: dict):
        try:
            for chunk_link in chunk_links:
                chunk_link_entity = ChunkLinkEntity(
                    id=chunk_link['id'],
                    chunk_a_id=chunk_link['chunk_a'],
                    chunk_b_id=chunk_link['chunk_b'],
                    type=chunk_link['type'],
                )
                try:
                    # 插入数据库
                    await ChunkLinkManager.insert_chunk_link(chunk_link_entity)
                except Exception as e:
                    logging.error(f"Failed to upload chunk: {e}")
                    raise e
        except Exception as e:
            logging.error(f"Failed to upload chunk: {e}")

    @staticmethod
    async def upload_images_to_minio(images):
        output_dir = None
        try:
            for image in images:
                output_dir = os.path.join(OssConstant.PARSER_SAVE_FOLDER, str(image['id']))
                output_path = os.path.join(output_dir, str(image['id'])+'.'+image['extension'])
                await MinIO.put_object(OssConstant.MINIO_BUCKET_PICTURE, str(image['id']), output_path)
        except Exception as e:
            logging.error(f"Failed to upload image: {e}")
        finally:
            if output_dir and os.path.exists(output_dir):
                shutil.rmtree(output_dir)

    @staticmethod
    async def upload_images_to_pg(images):
        try:
            for image in images:
                image_entity = ImageEntity(id=image['id'],
                                           chunk_id=image['chunk_id'],
                                           document_id=image['doc_id'],
                                           user_id=image['user_id'],
                                           )
                try:
                    await ImageManager.add_image(image_entity)
                except Exception as e:
                    logging.error(f"Failed to upload image: {e}")
                    raise e
        except Exception as e:
            logging.error(f"Failed to upload image: {e}")

    @staticmethod
    async def embedding_chunks(chunks):
        try:
            vectors = []
            for chunk in chunks:
                vectors.append({'chunk_id': chunk['id'],
                                'doc_id': chunk['doc_id'],
                                'kb_id': chunk['kb_id'],
                                'user_id': chunk['user_id'],
                                'vector': await Vectorize.vectorize_embedding(chunk['text']),
                                'enabled': chunk['enabled'],
                                })
            return vectors
        except Exception as e:
            logging.error(f"Failed to embedding chunk: {e}")
            raise e

    @staticmethod
    async def insert_vectors_to_pg(vectors):
        if len(vectors)==0:
            return
        try:
            # if True:
            doc = await DocumentManager.select_by_id(vectors[0]['doc_id'])
            kb = await KnowledgeBaseManager.select_by_id(doc.kb_id)
            vector_items_table = await PostgresDB.get_dynamic_vector_items_table(
                str(kb.vector_items_id),
                embedding_model_out_dimensions[kb.embedding_model]
            )
            await PostgresDB.create_table(vector_items_table)
            for vect in vectors:
                await VectorItemsManager.add(vector_items_table, vect)
        except Exception as e:
            logging.error(f"Failed to upload chunk: {e}")
            raise e
