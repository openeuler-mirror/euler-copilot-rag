import os
import json
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.graphs.graph_document import GraphDocument, Node, Relationship

from rag_service.security.cryptohub import CryptoHub
from rag_service.exceptions import Neo4jQueryException
from rag_service.vectorstore.neo4j.neo4j_constants import EXTRACT_ENTITY_SYSTEM_PROMPT, EXTRACT_HUMAN_PROMPT, \
    GENERATE_CYPHER_SYSTEM_PROMPT


llm = ChatOpenAI(openai_api_key=CryptoHub.query_plaintext_by_config_name('OPENAI_APP_KEY'),
                 openai_api_base=os.getenv("LLM_URL"), model_name="Qwen-72B-Chat-Int4", temperature=0)

NEO4J_URL = CryptoHub.query_plaintext_by_config_name('NEO4J_URL')
NEO4J_USERNAME = CryptoHub.query_plaintext_by_config_name('NEO4J_USERNAME')
NEO4J_PASSWORD = CryptoHub.query_plaintext_by_config_name('NEO4J_PASSWORD')
graph = Neo4jGraph(url=NEO4J_URL, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)


def _map_to_base_node(node: dict) -> Node:
    return Node(id=node['id'], type=node['type'], properties=node.get('properties', []))


def _map_to_base_edge(edge: dict) -> Relationship:
    source = _map_to_base_node(edge['source'])
    target = _map_to_base_node(edge['target'])
    return Relationship(source=source, target=target, type=edge['type'], properties=edge.get('properties', []))


def convert_to_graph_documents(documents: List[Document]) -> List[GraphDocument]:
    graph_documents = []
    for doc in documents:
        print(doc.page_content.replace('\n', ' '))
        message = [
            SystemMessage(
                content=EXTRACT_ENTITY_SYSTEM_PROMPT
            ),
            HumanMessage(
                content=EXTRACT_HUMAN_PROMPT.replace('{{input}}', doc.page_content)
            )
        ]
        res = llm.invoke(message)

        try:
            json_result = json.loads(res.content)
        except Exception as e:
            print("Load llm result to json error.")
        if 'nodes' in json_result:
            nodes = [_map_to_base_node(node) for node in json_result['nodes']]
        if 'edges' in json_result:
            rels = [_map_to_base_edge(rel) for rel in json_result['edges']]
        graph_document = GraphDocument(nodes=nodes, relationships=rels, source=doc)
        graph_documents.append(graph_document)
    print("convert down")
    return graph_documents


def add_graph_documents_to_neo4j(graph_documents: List[GraphDocument]):
    try:
        graph.add_graph_documents(graph_documents=graph_documents,
                                  baseEntityLabel=True,
                                  include_source=True)
    except Exception as e:
        raise Neo4jQueryException(f'Neo4j query exception') from e
    print("added")


def neo4j_search_data(question: str):
    message = [
        SystemMessage(
            content=GENERATE_CYPHER_SYSTEM_PROMPT.replace('{{schema}}', graph.schema)
        ),
        HumanMessage(
            content=question
        )
    ]
    cypher = llm.invoke(message)
    response = graph.query(query=cypher.content, params={})
    neo4j_res = ''
    for res in response:
        for v in res.values():
            if v is not None:
                neo4j_res += v+'\n'
    return neo4j_res
