EXTRACT_ENTITY_SYSTEM_PROMPT = """
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

EXTRACT_HUMAN_PROMPT = """
Tip: Make sure to answer in the correct format and do not include any explanations. Use the given format to extract information from the following input: {{input}}

Format: 
{
    "nodes":[{"id": "openEuler","type":"operation_system"},{"id":"Linux_Kernel_5.10","type":"kernel"}],
    "edges":[{"source":{"id": "openEuler","type":"operation_system"},"target":{"id":"Linux_Kernel_5.10","type":"kernel"},"type":"based_on"}]
}
"""

GENERATE_CYPHER_SYSTEM_PROMPT = """
Based on the Neo4j graph schema below, write a Cypher query that would answer the user's question.
Return only Cypher statement, no backticks, nothing else.
{{schema}}
"""
