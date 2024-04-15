# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import json
import requests
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph
from langchain_community.graphs.graph_document import GraphDocument, Node, Relationship

from rag_service.logger import get_logger
from rag_service.llms.qwen import token_check
from rag_service.security.cryptohub import CryptoHub
from rag_service.exceptions import Neo4jQueryException, TokenCheckFailed
from rag_service.config import LLM_MODEL, LLM_TEMPERATURE, QWEN_MAX_TOKENS
from rag_service.vectorstore.neo4j.neo4j_constants import EXTRACT_ENTITY_SYSTEM_PROMPT, NEO4J_PROPERTIES_SQL, NEO4J_RELATIONSHIP_SQL

logger = get_logger()
llm = ChatOpenAI(openai_api_key=CryptoHub.query_plaintext_by_config_name('OPENAI_APP_KEY'),
                 openai_api_base=CryptoHub.query_plaintext_by_config_name('OPENAI_API_BASE'),
                 model_name="Qwen-72B-Chat-Int4", temperature=0)

NEO4J_URL = CryptoHub.query_plaintext_by_config_name('NEO4J_URL')
NEO4J_USERNAME = CryptoHub.query_plaintext_by_config_name('NEO4J_USERNAME')
NEO4J_PASSWORD = CryptoHub.query_plaintext_by_config_name('NEO4J_PASSWORD')
graph = Neo4jGraph(url=NEO4J_URL, username=NEO4J_USERNAME, password=NEO4J_PASSWORD, database="features")


def _map_to_base_node(node: dict) -> Node:
    return Node(id=node['id'], properties=node.get('properties', []))


def _map_to_base_edge(edge: dict) -> Relationship:
    source = _map_to_base_node(edge['source'])
    target = _map_to_base_node(edge['target'])
    return Relationship(source=source, target=target, type=edge['type'], properties=edge.get('properties', []))


def convert_to_graph_documents() -> List[GraphDocument]:
    graph_documents = []
    dir = ''
    for filename in os.listdir(dir):
        if filename.endswith('.json'):
            file_path = os.path.join(dir, filename)
            with open(file_path, 'r') as file:
                json_result = json.load(file)
                if 'nodes' in json_result:
                    nodes = [_map_to_base_node(node) for node in json_result['nodes']]
                if 'edges' in json_result:
                    rels = [_map_to_base_edge(rel) for rel in json_result['edges']]
                graph_document = GraphDocument(nodes=nodes, relationships=rels,
                                               source=Document(page_content=json_result['source']))
                graph_documents.append(graph_document)
    return graph_documents


def add_graph_documents_to_neo4j(graph_documents: List[GraphDocument]):
    try:
        graph.add_graph_documents(graph_documents=graph_documents,
                                  baseEntityLabel=True,
                                  include_source=True)
    except Exception as e:
        raise Neo4jQueryException(f'Neo4j query exception') from e


def llm_call(question: str, prompt: str, history: List = None):
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": question}
    ]
    history = history or []
    if len(history) > 0:
        messages[1:1] = history
    while not token_check(messages):
        if len(messages) > 2:
            messages = messages[:1]+messages[2:]
        else:
            raise TokenCheckFailed(f'Token is too long.')
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer "+CryptoHub.query_plaintext_by_config_name('OPENAI_APP_KEY')
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "stream": False,
        "max_tokens": QWEN_MAX_TOKENS
    }
    response = requests.post(os.getenv("LLM_URL"), json=data, headers=headers, stream=False, timeout=60)
    if response.status_code == 200:
        answer_info = response.json()
        if 'choices' in answer_info and len(answer_info.get('choices')) > 0:
            final_ans = answer_info['choices'][0]['message']['content']
            return final_ans
        else:
            return ""
    else:
        return ""


def get_entity_properties(entity: str):
    cypher = NEO4J_PROPERTIES_SQL.replace('{{entity}}', entity)
    try:
        graph_res = graph.query(query=cypher, params={})
    except Exception as e:
        logger.error("Neo4j query error.")
        return None
    neo4j_content = ""
    for k, v in graph_res[0]['props'].items():
        if k != "id":
            neo4j_content += k+"是"+v+", "
    return entity+"的"+neo4j_content
    # return None


def get_entity_relationships(entity: str):
    cypher = NEO4J_RELATIONSHIP_SQL.replace('{{entity}}', entity)
    try:
        graph_res = graph.query(query=cypher, params={})
    except Exception as e:
        logger.error("Neo4j query error.")
        return None
    neo4j_content = ""
    for res in graph_res:
        neo4j_content += res['output']+' '
    return neo4j_content
    # return None


def neo4j_search_data(question: str):
    # Extract entities from question
    llm_res = llm_call(question=question, prompt=EXTRACT_ENTITY_SYSTEM_PROMPT, history=[])
    try:
        entities = json.loads(llm_res)
    except Exception as e:
        logger.error("Extract entities error.")
        return None
    if len(entities) == 0:
        logger.error("Extract entities empty.")
        return None

    # Query entity properties
    entity_properties = get_entity_properties(entity=entities[0])
    # Query entity relationships
    entity_relationships = get_entity_relationships(entity=entities[0])
    # Return more than one documents
    result = [value for value in (entity_properties, entity_relationships) if value is not None]
    return result if result else None
