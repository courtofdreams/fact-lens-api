from rdflib import Graph
from pyshacl import validate

# Load RDF data (from Neo4j or toy example)
data_graph = Graph()
data_graph.parse("data.ttl", format="turtle")

# Load SHACL shapes
shacl_graph = Graph()
shacl_graph.parse("shapes.ttl", format="turtle")

conforms, results_graph, results_text = validate(
    data_graph,
    shacl_graph=shacl_graph,
    inference="rdfs",
    abort_on_first=False,
    advanced=True,  
)

print("Conforms:", conforms)
print(results_text.decode() if isinstance(results_text, bytes) else results_text)
