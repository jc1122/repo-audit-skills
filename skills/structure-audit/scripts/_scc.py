"""Iterative Tarjan strongly connected component search.

The structure audit uses this for import-cycle detection. The implementation is
iterative so large import graphs do not depend on Python recursion depth, while
the mutable Tarjan bookkeeping stays isolated from the finding-emission code.
"""

from __future__ import annotations


class _SccState:
    """Mutable Tarjan state shared by one graph walk."""

    def __init__(self) -> None:
        self.next_index = 0
        self.stack: list[str] = []
        self.index: dict[str, int] = {}
        self.lowlink: dict[str, int] = {}
        self.on_stack: dict[str, bool] = {}
        self.result: list[list[str]] = []

    def is_visited(self, node: str) -> bool:
        return node in self.index

    def is_open(self, node: str) -> bool:
        return bool(self.on_stack.get(node))

    def start_node(self, node: str) -> None:
        """Assign a discovery index and push *node* onto the open stack."""

        self.index[node] = self.next_index
        self.lowlink[node] = self.next_index
        self.next_index += 1
        self.stack.append(node)
        self.on_stack[node] = True

    def record_back_edge(self, node: str, target: str) -> None:
        self.lowlink[node] = min(self.lowlink[node], self.index[target])

    def update_parent(self, parent: str, node: str) -> None:
        self.lowlink[parent] = min(self.lowlink[parent], self.lowlink[node])

    def close_component(self, node: str) -> None:
        """Pop and record a component when *node* is its root."""

        if self.lowlink[node] != self.index[node]:
            return
        comp = []
        while True:
            target = self.stack.pop()
            self.on_stack[target] = False
            comp.append(target)
            if target == node:
                break
        self.result.append(sorted(comp))


def _advance_walk(work, edges, state: _SccState) -> bool:
    """Advance the explicit DFS stack; return True after descending."""

    node, position = work[-1]
    successors = edges.get(node, [])
    for index in range(position, len(successors)):
        target = successors[index]
        # Unvisited successors become the next stack frame. The parent frame is
        # saved with the next successor position so traversal resumes exactly
        # where recursive Tarjan would return.
        if not state.is_visited(target):
            work[-1] = (node, index + 1)
            work.append((target, 0))
            return True
        # A successor still on the stack forms a back edge and can lower the
        # current node's reachable discovery index. Closed successors must not
        # affect lowlink; they already belong to another component.
        if state.is_open(target):
            state.record_back_edge(node, target)
    return False


def strongly_connected_components(nodes, edges):
    """Return sorted strongly connected components for *nodes* and *edges*."""

    state = _SccState()
    for root_node in nodes:
        if state.is_visited(root_node):
            continue
        work = [(root_node, 0)]
        while work:
            node, position = work[-1]
            # Position zero means the frame has just been entered. Later visits
            # to the same frame are returns from a descendant.
            if position == 0:
                state.start_node(node)
            if _advance_walk(work, edges, state):
                continue
            state.close_component(node)
            work.pop()
            if work:
                # Propagate child lowlink to the parent after the child frame is
                # fully explored, matching the recursive Tarjan post-order step.
                state.update_parent(work[-1][0], node)
    return state.result
