import os
from pydoc import doc

from requests import session
from typing import Dict, Any, List
from langchain_community.graphs import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI
from enum import Enum
import spacy
from settings import settings

nlp = spacy.load("en_core_web_sm")
ruler = nlp.add_pipe("entity_ruler", before="ner")

patterns = [
    ## Example patterns:
    {"label": "PERSON", "pattern": "Elon Musk"},
    # add more frequent entities if you want:
    # {"label": "ORG", "pattern": "OpenAI"},
]

ruler.add_patterns(patterns)


class Graph(Enum):
    COMMUNITY = "community"
    
class KnowledgeGraphService:
        def __init__(self, temperature=0, model_name="gpt-4-turbo"):   
            OPENAI_API_KEY = settings.OPENAI_API_KEY
            if OPENAI_API_KEY is None:
                raise ValueError("OPENAI_API_KEY environment variable not set.")
            
            self.llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY,temperature=temperature, model_name=model_name)
            
            self.graph_community = Neo4jGraph(
                database=Graph.COMMUNITY.value,
                url=settings.NEO4J_URI,
                username=settings.NEO4J_USERNAME,
                password=settings.NEO4J_PASSWORD
            )
            
            self.llm_transformer = LLMGraphTransformer(
                llm=self.llm
            )          
        
        def build_graph(self, text, config: Graph):
            documents = [Document(page_content=text)]
            graph_documents = self.llm_transformer.convert_to_graph_documents(documents)
            print(f"Nodes:{graph_documents[0].nodes}")
            print(f"Relationships:{graph_documents[0].relationships}")
            if config == Graph.COMMUNITY:
                self.graph_community.add_graph_documents(graph_documents)
            elif config == Graph.POLITIFACT:
                self.graph_politifact.add_graph_documents(graph_documents)
            else:
                raise ValueError("Invalid config. Choose 'community' or 'politifact'.")   
        
        def build_multiple_graphs(self, data: list, config: Graph):
            combined_text = '\n'.join([doc['note'] for doc in data])
            documents = [Document(page_content=combined_text)]
            graph_documents = self.llm_transformer.convert_to_graph_documents(documents)
            self.graph_community.add_graph_documents(graph_documents)
            
        def reset_database(self):
            with self.graph_community.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                print("Database reset successfully!")  
        
        def search(self, query: str):
            with self.graph_community.session() as session:
                result = session.run(query)
            return [record.data() for record in result]
        
        def get_graph(self):
            return self.graph_community
            
        def get_context(self, query: str):
            entities = self.extract_names(query)
            
            if not entities:
                return {"answer": "No entities found."}


            for ent in entities:
                text = ent["text"]
                label = ent["label"]         # PERSON / ORG / DATE / etc

                neo4j_label = self.neo4j_label_for_ner(label)
                if not neo4j_label:
                    # ignore DATE, MONEY, TIME, etc.
                    continue

                context = self.build_entity_context(text, neo4j_label)
                combined_context = " ".join([x for x in context])
            
            ## TODO: Add reasoning here to combine multiple contexts if needed

            return combined_context
        
        
        
        def extract_names(self, text: str) -> list:
            doc = nlp(text)
            result = []
            for ent in doc.ents:
                person = {"text": ent.text, "label": ent.label_}
                result.append(person)
            return result

        def fetch_entity_subgraph(self, name: str, label: str) -> Dict[str, Any]:
            # label should be something like "Person" or "Organization"
            if label not in {"Person", "Organization"}:
                raise ValueError(f"Unsupported label: {label}")

            cypher = f"""
            MATCH (e:{label} {{name: $name}})
            OPTIONAL MATCH path = (e)-[r*1..2]-(n)
            WITH e, collect(DISTINCT n) AS neighbors, collect(DISTINCT path) AS paths
            WITH e, neighbors,
                reduce(allRels = [], pth IN paths | allRels + relationships(pth)) AS rels
            RETURN e AS entity,
                neighbors,
                [rel IN rels | {{
                    type: type(rel),
                    startId: id(startNode(rel)),
                    endId: id(endNode(rel)),
                    properties: properties(rel)
                }}] AS relationships
            """

            result = self.graph_community.run(cypher, name=name).data()
            return result[0] if result else {}

               
        def neo4j_label_for_ner(self, ner_label: str) -> str | None:
            if ner_label == "PERSON":
                return "Person"
            if ner_label == "ORG":
                return "Organization"
            return None  # ignore DATE, etc.
         
        
        def build_entity_context(self, name: str, neo4j_label: str) -> str:
            cypher = f"""
                MATCH (e:{neo4j_label} {{id: $id}})-[r]-(n)
                RETURN type(r) AS relation,
                    n.id AS target
            """
            
            rows = self.graph_community.query(cypher, {"id": name})

            if not rows:
                return f"No information found for {name}."

            fragments = []
            for row in rows:
                rel = row["relation"].replace("_", " ").lower()
                target = row["target"]
                fragments.append(f"{name} {rel} {target}")

            return "; ".join(fragments) + "."

        
        def close(self):
            self.graphDB.close()
            print("Connection closed")  


            