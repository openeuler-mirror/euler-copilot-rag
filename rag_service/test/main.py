import json
from typing import List

from py2neo import Graph
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.document_loaders.markdown import UnstructuredMarkdownLoader
from langchain_community.graphs.graph_document import GraphDocument, Node, Relationship

from rag_service.test.chinese_text_splitter import ChineseTextSplitter


system_prompt = """
# Knowledge Graph Instructions

## 1. Overview
You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph.
Try to capture as much information from the text as possible without sacrifing accuracy. Do not add any information that is not explicitly mentioned in the text.
- **Nodes** represent entities and concepts.
- The aim is to achieve simplicity and clarity in the knowledge graph, making it accessible for a vast audience.

## 2. Labeling Nodes
- **Consistency**: Ensure you use available types for node labels.
Ensure you use basic or elementary types for node labels.
- For example, when you identify an entity representing a person, always label it as **'person'**. Avoid using more specific terms like 'mathematician' or 'scientist'
- **Node IDs**: Never utilize integers as node IDs. Node IDs should be names or human-readable identifiers found in the text.
- **Relationships** represent connections between entities or concepts.
Ensure consistency and generality in relationship types when constructing knowledge graphs. Instead of using specific and momentary types such as 'BECAME_PROFESSOR', use more general and timeless relationship types "like 'PROFESSOR'. Make sure to use general and timeless relationship types!

## 3. Coreference Resolution
- **Maintain Entity Consistency**: When extracting entities, it's vital to ensure consistency.

If an entity, such as "John Doe", is mentioned multiple times in the text but is referred to by different names or pronouns (e.g., "Joe", "he"), always use the most complete identifier for that entity throughout the knowledge graph.
In this example, use "John Doe" as the entity ID.

Remember, the knowledge graph should be coherent and easily understandable, so maintaining consistency in entity references is crucial.

## 4. Strict Compliance
Adhere to the rules strictly. Non-compliance will result in termination.
"""

human_prompt = """
Tip: Make sure to answer in the correct format and do not include any explanations. Use the given format to extract information from the following input: {{input}}

Format: 
{
    "nodes":[{"id": "openEuler","type":"operation_system"},{"id":"Linux_Kernel_5.10","type":"kernel"}],
    "edges":[{"source":{"id": "openEuler","type":"operation_system"},"target":{"id":"Linux_Kernel_5.10","type":"kernel"},"type":"based_on"}]
}
"""


def test_neo4j():
    NEO4J_URI = "bolt://127.0.0.1:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "12345678"
    graph_db = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    cypher_sql = """
match (o:OS)-[r:KERNAL]->(k:Kernal) return o,k
"""
    datas = graph_db.run(cypher_sql).data()
    for data in datas:
        os_node = data['o']
        kernal_node = data['k']
        print(f"name: {os_node['name']}, version: {os_node['version']}, kernal: {kernal_node['version']}")


def add_graph_documents_to_neo4j(graph_documents: List[GraphDocument]):
    NEO4J_URL = "bolt://127.0.0.1:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "12345678"
    # graph_db = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    graph = Neo4jGraph(url=NEO4J_URL, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
    try:
        graph.add_graph_documents(graph_documents=graph_documents,
                                  baseEntityLabel=True,
                                  include_source=True)
    except Exception as e:
        print("add graph document to neo4j error.")
    print("added")


def map_to_base_node(node: dict) -> Node:
    return Node(id=node['id'], type=node['type'])


def map_to_base_edge(edge: dict) -> Relationship:
    source = map_to_base_node(edge['source'])
    target = map_to_base_node(edge['target'])
    return Relationship(source=source, target=target, type=edge['type'])


def convert_to_graph_documents(documents: List[Document]) -> List[GraphDocument]:
    llm = ChatOpenAI(api_key="", base_url="http://123.60.114.28:32315/v1", model="Qwen-72B-Chat-Int4", temperature=0)
    graph_documents = []

    for doc in documents:
        message = [
            SystemMessage(
                content=system_prompt
            ),
            HumanMessage(
                content=human_prompt.replace('{{input}}', doc.page_content)
            )
        ]
        res = llm.invoke(message)

        try:
            json_result = json.loads(res.content)
        except KeyError as e:
            print("Load llm result to json error.")
        if 'nodes' in json_result:
            nodes = [map_to_base_node(node) for node in json_result['nodes']]
        if 'edges' in json_result:
            rels = [map_to_base_edge(rel) for rel in json_result['edges']]
        graph_document = GraphDocument(nodes=nodes, relationships=rels, source=doc)
        graph_documents.append(graph_document)
        break
    return graph_documents


def load_documents():
    test_file_path = "/root/zl/euler-copilot-rag/rag_service/test/test.md"
    loader = UnstructuredMarkdownLoader(file_path=test_file_path)
    raw_documents = loader.load()

    text_splitter = ChineseTextSplitter(pdf=False, sentence_size=256)
    documents = []
    for raw_document in raw_documents:
        for doc in text_splitter.split_text(raw_document.page_content):
            documents.append(doc)

    sequence_documents = []
    for document in documents:
        metadata = {'source': '/root/zl/euler-copilot-rag/rag_service/test/test.md'}
        sequence_documents.append(Document(page_content=document, metadata=metadata))
    return sequence_documents


if __name__ == "__main__":
    documents = load_documents()
    graph_documents = convert_to_graph_documents(documents=documents)
    add_graph_documents_to_neo4j(graph_documents=graph_documents)
