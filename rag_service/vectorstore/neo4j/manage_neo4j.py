# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import json
import time
import traceback
from typing import List

from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph
from langchain_community.graphs.graph_document import GraphDocument, Node, Relationship

from rag_service.logger import get_logger
from rag_service.llms.llm import select_llm
from rag_service.security.config import config
from rag_service.models.api import QueryRequest
from rag_service.exceptions import Neo4jQueryException
from rag_service.vectorstore.neo4j.neo4j_constants import EXTRACT_ENTITY_SYSTEM_PROMPT, NEO4J_EDGE_SQL, \
    NEO4J_ENTITY_SQL, NEO4J_RELATIONSHIP_SQL

logger = get_logger()

if config["GRAPH_RAG_ENABLE"]:
    NEO4J_URL = config['NEO4J_URL']
    NEO4J_USERNAME = config['NEO4J_USERNAME']
    NEO4J_PASSWORD = config['NEO4J_PASSWORD']
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
            print(f"start json: {file_path}")
            with open(file_path, 'r') as file:
                json_result = json.load(file)
                if 'nodes' in json_result:
                    nodes = [_map_to_base_node(node) for node in json_result['nodes']]
                if 'edges' in json_result:
                    rels = [_map_to_base_edge(rel) for rel in json_result['edges']]
                graph_document = GraphDocument(nodes=nodes, relationships=rels,
                                               source=Document(page_content=json_result['source']))
                graph_documents.append(graph_document)
                print(f"end json: {file_path}")
    return graph_documents


def add_graph_documents_to_neo4j(graph_documents: List[GraphDocument]):
    try:
        graph.add_graph_documents(graph_documents=graph_documents,
                                  baseEntityLabel=True,
                                  include_source=True)
    except Exception as e:
        raise Neo4jQueryException(f'Neo4j query exception') from e


def get_entity_properties(entity: str):
    cypher = NEO4J_ENTITY_SQL.replace('{{entity}}', entity)
    try:
        graph_res = graph.query(query=cypher, params={})
        neo4j_content = ""
        for k, v in graph_res[0]['props'].items():
            if k != "id":
                neo4j_content += k + "是" + v + "; "
    except Exception:
        return None
    return neo4j_content if neo4j_content != "" else None


def get_edge_properties(entity: str):
    cypher = NEO4J_EDGE_SQL.replace('{{entity}}', entity)
    try:
        graph_res = graph.query(query=cypher, params={})
        neo4j_content = ""
        for res in graph_res:
            for value in res.values():
                neo4j_content += value + "; "
    except Exception:
        return None
    return neo4j_content if neo4j_content != "" else None


def get_entity_relationships(entity: str):
    cypher = NEO4J_RELATIONSHIP_SQL.replace('{{entity}}', entity)
    try:
        graph_res = graph.query(query=cypher, params={})
        neo4j_content = ""
        for res in graph_res:
            neo4j_content += res['output'] + '; '
    except Exception:
        return None
    return neo4j_content if neo4j_content != "" else None


def neo4j_search_data(req: QueryRequest):
    # Extract entities from question
    try:
        st = time.time()
        llm_res = select_llm(req).nonstream(req=req, prompt=EXTRACT_ENTITY_SYSTEM_PROMPT)
        et = time.time()
        logger.info(f"neo4j entity extract: {et - st}")
        raw_entities = json.loads(llm_res)
        filter_entities = []
        logger.info(f"获取到的实体词: {raw_entities}")
        for entity in raw_entities:
            if str.lower(entity) == "openeuler":
                continue
            filter_entities.append(entity)
        logger.info(f"过滤后的实体词: {filter_entities}")
    except Exception:
        logger.error(u"Extract entities error. {}".format(traceback.format_exc()))
        return None
    if len(filter_entities) == 0:
        logger.info("Extract entities empty.")
        return None
    st = time.time()
    entity_properties_content = ""
    edge_content = ""
    entity_relationships_content = ""
    for entity in filter_entities:
        # Query entity properties
        entity_properties = get_entity_properties(entity=entity)
        if entity_properties is not None:
            entity_properties_content += entity_properties + "; "
        # Query edge
        edge = get_edge_properties(entity=entity)
        if edge is not None:
            edge_content += edge + "; "
        # Query entity relationships
        entity_relationships = get_entity_relationships(entity=entity)
        if entity_relationships is not None:
            entity_relationships_content += entity_relationships + "; "
    et = time.time()
    logger.info(f"neo4j search: {et - st}")
    if entity_properties_content == "" and edge_content == "" and entity_relationships_content == "":
        return None
    return f"查询结果为: {entity_properties_content}, {edge_content}, {entity_relationships_content}", "neo4j query result"
