from . import files
from typing import Any, Optional

class Dot(files.File):
    name: Any = ...
    comment: Any = ...
    graph_attr: Any = ...
    node_attr: Any = ...
    edge_attr: Any = ...
    body: Any = ...
    strict: Any = ...
    def __init__(self, name: Optional[Any] = ..., comment: Optional[Any] = ..., filename: Optional[Any] = ..., directory: Optional[Any] = ..., format: Optional[Any] = ..., engine: Optional[Any] = ..., encoding: Any = ..., graph_attr: Optional[Any] = ..., node_attr: Optional[Any] = ..., edge_attr: Optional[Any] = ..., body: Optional[Any] = ..., strict: bool = ...) -> None: ...
    def clear(self, keep_attrs: bool = ...) -> None: ...
    def __iter__(self, subgraph: bool = ...) -> Any: ...
    @property
    def source(self): ...
    def node(self, name: str, label: Optional[str] = ..., _attributes: Optional[object] = ..., **attrs: object) -> None: ...
    def edge(self, tail_name: str, head_name: str, label: Optional[str] = ..., _attributes: Optional[Any] = ..., **attrs: Any) -> None: ...
    def edges(self, tail_head_iter: Any) -> None: ...
    def attr(self, kw: Optional[Any] = ..., _attributes: Optional[Any] = ..., **attrs: Any) -> None: ...
    def subgraph(self, graph: Optional[Any] = ..., name: Optional[Any] = ..., comment: Optional[Any] = ..., graph_attr: Optional[Any] = ..., node_attr: Optional[Any] = ..., edge_attr: Optional[Any] = ..., body: Optional[Any] = ...): ...

class SubgraphContext:
    parent: Any = ...
    graph: Any = ...
    def __init__(self, parent: Any, kwargs: Any) -> None: ...
    def __enter__(self): ...
    def __exit__(self, type_: Any, value: Any, traceback: Any) -> None: ...

class Graph(Dot):
    @property
    def directed(self): ...

class Digraph(Dot):
    @property
    def directed(self): ...