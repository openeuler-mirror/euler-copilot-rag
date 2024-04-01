# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import json
import requests
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph
from langchain_community.graphs.graph_document import GraphDocument, Node, Relationship

from rag_service.llms.qwen import token_check
from rag_service.security.cryptohub import CryptoHub
from rag_service.config import LLM_MODEL, LLM_TEMPERATURE, MAX_TOKENS
from rag_service.exceptions import Neo4jQueryException, TokenCheckFailed
from rag_service.vectorstore.neo4j.neo4j_constants import GENERATE_CYPHER_SYSTEM_PROMPT


llm = ChatOpenAI(openai_api_key="xxx",
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


def convert_to_graph_documents() -> List[GraphDocument]:
    graph_documents = []
    with open('/root/zl/euler-copilot-rag/rag_service/vectorstore/neo4j/2309-9.json', 'r') as file:
        json_result = json.load(file)
    if 'nodes' in json_result:
        nodes = [_map_to_base_node(node) for node in json_result['nodes']]
    if 'edges' in json_result:
        rels = [_map_to_base_edge(rel) for rel in json_result['edges']]
    graph_document = GraphDocument(nodes=nodes, relationships=rels,
                                   source=Document(page_content=json.dumps(json_result)))
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
        "Authorization": CryptoHub.query_plaintext_by_config_name('OPENAI_APP_KEY')
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "stream": False,
        "max_tokens": MAX_TOKENS
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


def neo4j_search_data(question: str):
    try:
        cypher = llm_call(question=question, prompt=GENERATE_CYPHER_SYSTEM_PROMPT.replace(
            '{{schema}}', graph.schema), history=[])
        print(cypher)
        neo4j_res = graph.query(query=cypher, params={})
        res = None if neo4j_res == [] else question + ', 查询图数据库的结果为: '+json.dumps(neo4j_res, ensure_ascii=False)
        print(res)
    except Exception:
        return None
    return res


def neo4j_insert_data():
    graph_documents = convert_to_graph_documents()
    add_graph_documents_to_neo4j(graph_documents)


if __name__ == "__main__":
    neo4j_insert_data()
    # res = neo4j_search_data("你好")
    # print(res)
