from typing import Union

from networkx import Graph, DiGraph
from networkx.exception import NetworkXNoCycle
from networkx.algorithms.cycles import find_cycle
from networkx.algorithms.components import is_connected


def validate_pipeline_structure(graph: Union[Graph, DiGraph]) -> bool:
    assert is_connected(graph.to_undirected()), "The pipeline must be connected."

    try:
        find_cycle(graph)
    except NetworkXNoCycle:
        pass
    else:
        raise ValueError("The pipeline must not contain a cycle.")

    return True
