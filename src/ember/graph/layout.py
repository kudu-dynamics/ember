from collections import defaultdict
from collections.abc import Iterable
import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar

import networkx
from networkx import DiGraph



@dataclass
class LayoutOptions:
    """A class to store layout options."""
    x_margin: int = 10
    y_margin: int = 5
    row_margin: int = 16
    col_margin: int = 16

DEFAULT_LAYOUT = LayoutOptions()

class Move(Enum):
    LEFT = 0
    NA = 1 # Not available, there are no moves
    RIGHT = 2

# Type aliases
EdgeIndex = int
GridElem = TypeVar('GridElem')
Grid = List[List[GridElem]]
Node = Any

@dataclass(eq=True, frozen=True)
class Edge:
    src: Node
    dst: Node

@dataclass
class Point:
    x: int
    y: int

@dataclass
class EdgeCoord:
    """A coordinate used to indicate segments of an edge
    polyline in the grid. Multiple edges may appear in
    a single grid and are ordered by an index.
    """
    col: int
    row: int
    idx: EdgeIndex

@dataclass(eq=True, frozen=True)
class GridIndex:
    col: int
    row: int

@dataclass
class NodeSize:
    width: int
    height: int

@dataclass
class SegmentedEdge:
    src: Node
    dst: Node
    start_index: Optional[EdgeIndex] = None
    # The initial value of max_start_index is not used, and 0 is the minimum value it may be assigned.
    max_start_index: EdgeIndex = 0
    end_index: Optional[EdgeIndex] = None
    max_end_index: Optional[EdgeIndex] = None
    # Three-dimensional points so that we can handle edge segments assigned to the same coordinate.
    points: List[EdgeCoord] = field(default_factory=lambda: [])
    moves: List = field(default_factory=lambda: [])
    # Scene coordinates
    coordinates: List[Point] = field(default_factory=lambda: [])

    def first_move(self) -> Move:
        return self.moves[0] if self.moves else Move.NA

    def last_move(self) -> Move:
        return self.moves[-1] if self.moves else Move.NA

    def add_coord(self, pt: Point) -> None:
        if len(self.coordinates) >= 2:
            a = self.coordinates[-2]
            b = self.coordinates[-1]
            if b.x == a.x == pt.x:
                # Vertical movement, replace last point
                self.coordinates[-1] = pt
                return
            elif b.y == a.y == pt.y:
                # Horizontal movement, replace last point
                self.coordinates[-1] = pt
                return
        self.coordinates.append(pt)

@dataclass
class LayoutResult:
    nodes: Dict[Node, Point]
    edges: Dict[Edge, List[Point]]

class EdgeLayoutState:
    def __init__(self,
                 max_col: int,
                 max_row: int,
                 node_locations: Dict[Node, GridIndex]):
        self.edge_valid: Grid[bool]
        self.vertical_edges: Grid[Dict[EdgeIndex, SegmentedEdge]]
        self.horizontal_edges: Grid[Dict[EdgeIndex, SegmentedEdge]]
        # Map nodes to a grid index
        self.node_locations: Dict[Node, GridIndex] = node_locations

        self.edge_valid = [ ]
        for col in range(max_col + 2):
            self.edge_valid.append([True] * (max_row + 1))

        # Building up 2d-array to mark where edges/dummy nodes can be added
        for gi in node_locations.values():
            # edges should not overlap with existing nodes
            self.edge_valid[gi.col][gi.row] = False
            self.edge_valid[gi.col + 1][gi.row] = False

        self.vertical_edges = []
        self.horizontal_edges = []

        # Create a 2d-array of col x row elements that hold dicts which
        # of edge indices to SegmentedEdge
        for _ in range(max_col + 2):
            v_edges = []
            h_edges = []
            for _ in range(max_row + 3):
                v_edges.append({})
                h_edges.append({})
            self.vertical_edges.append(v_edges)
            self.horizontal_edges.append(h_edges)

        self.in_edges: Dict[Any, List[SegmentedEdge]] = defaultdict(list)
        self.out_edges: Dict[Any, List[SegmentedEdge]] = defaultdict(list)

    def edge_available(self,
                       col: int,
                       start_row: int,
                       end_row: int) -> bool:
        for idx in range(start_row, end_row):
            if not self.edge_valid[col][idx]:
                return False
        return True

    def set_in_edge_indices(self):
        # Assign indices for in-edges
        for _, edges in self.in_edges.items():
            max_idx = None

            if len(edges) == 2:
                # NB: In the original code they're depending on the enum value
                #     to ensure a right-to-left sorting. Unclear if the right-to-left
                #     ordering is required. Will preserve it.
                # Sort by last horizontal move of each edge
                edges = sorted(edges, key=lambda edge: edge.last_move().value, reverse=True)

            for idx, edge in enumerate(edges):
                edge.end_index = idx
                if max_idx is None or idx > max_idx:
                    max_idx = idx
            for edge in edges:
                edge.max_end_index = max_idx

    def set_out_edge_indices(self):
        # Assign indices for out-edges
        for _, edges in self.out_edges.items():
            max_idx = None

            if len(edges) == 2:
                # NB: In the original code they're depending on the enum value
                #     to ensure a left-to-right sorting (opposite of set_in_edge_indices.
                #     Unclear if the right-to-left ordering is required. Will preserve it.
                #  Sort by last horizontal move of each edge
                edges = sorted(edges, key=lambda edge: edge.first_move().value)

            for idx, edge in enumerate(edges):
                edge.start_index = idx
                if max_idx is None or edge.start_index > max_idx:
                    max_idx = edge.start_index
            for edge in edges:
                edge.max_start_index = max_idx

def layout(dg: DiGraph,
           node_sizes: Dict[Node, NodeSize],
           node_compare_key,
           layout_options=DEFAULT_LAYOUT) -> LayoutResult:
    """This function provides an implementation of the Sugiyama layout algorithm. This implementation is based off the implementation in angr management. There has been some refactoring into a more functional style.

    There are two important coordinate systems to understand. The first is the grid coordinate system which is used to calculate an abstract layout for the graph. The second is the scene coordinate system which is used to define the nodes and edges in the actual graphics scene that will be rendered. Additionally, grid cells can contain multiple edges, and the absolute position of the edges within the cell are determined by an index value. This is reflected in the `EdgeCoord` datalcass which includes a grid coordinate (column and row), as well as an index field.

    The grid is defined so that every row and column may have a different height and width, respectively.
    +------+-----------+
    |      |           |
    +----+-+---+-------+
    |    |     |       |
    |    |     |       |
    |    |     |       |
    +----+-----+-------+
    """
    # Order nodes
    ordered_nodes = quasi_topological_sort(dg)

    # Get an acyclic version of the graph
    dag = to_acyclic_graph(dg, ordered_nodes)

    # Assign grid locations
    max_rows, max_row = calculate_max_row(dag, ordered_nodes)
    rows, row_to_nodes = assign_rows(ordered_nodes, max_rows, node_compare_key)
    cols, locations, max_col = assign_columns(dag, row_to_nodes, node_compare_key)

    # TODO: Maybe can just provide the horizontal_lines and vertical_lines and don't need to return
    #       the EdgeLayoutState.
    # Route edges. Provides the edges as connected vertical and horizontal line segments
    edge_layout_state, edges = route_edges(dg, locations, max_col, max_row)

    # Find max edge index for all horizontal and vertical edge segments
    max_vertical_edge_indices: Dict[GridIndex, EdgeIndex]
    max_vertical_edge_indices = calculate_max_edge_indices(edge_layout_state.vertical_edges)
    max_horizontal_edge_indices: Dict[GridIndex, EdgeIndex]
    max_horizontal_edge_indices = calculate_max_edge_indices(edge_layout_state.horizontal_edges)

    # Determine the 2d grid/block sizes
    row_heights, col_widths = make_grids(max_row,
                                         max_col,
                                         max_vertical_edge_indices,
                                         max_horizontal_edge_indices,
                                         dg.nodes(),
                                         locations,
                                         node_sizes,
                                         layout_options.x_margin,
                                         layout_options.y_margin)

    # Calculate node coordinates
    layout_result = calculate_coordinates(max_row,
                                          max_col,
                                          row_heights,
                                          col_widths,
                                          locations,
                                          max_vertical_edge_indices,
                                          max_horizontal_edge_indices,
                                          layout_options.row_margin,
                                          layout_options.col_margin,
                                          layout_options.x_margin,
                                          layout_options.y_margin,
                                          dg.nodes(),
                                          node_sizes,
                                          edges)

    return layout_result, edges

def quasi_topological_sort(dg: DiGraph) -> List:
    """
    Sort nodes from a graph based on the following rules:

    # - if A -> B and not B -> A, then we have A < B
    # - if A -> B and B -> A, then the ordering is undefined

    Following the above rules gives us a quasi-topological sorting of nodes in the graph. It also works for cyclic
    graphs.

    This function and its supporting functions are based off a similarly named function from the angr framework.

    :param networkx.DiGraph dg: A directed graph, it may contain cycles.
    :return: A list of ordered nodes.
    :rtype: list
    """

    # fast path for single node graphs
    if dg.number_of_nodes() == 1:
        return dg.nodes()

    # make a copy to the graph since we are going to modify it
    dg_copy = networkx.DiGraph()

    # TODO: This code from angr was originally supporting control- and data-flow graphs
    # Why check for SCCs in a CFG or DFG? Seems like it makes this function more general,
    # keeping it for now.

    # find all strongly connected components in the graph
    sccs = [scc for scc in networkx.strongly_connected_components(dg) if len(scc) > 1]

    # Assign indices to SCCs and then map nodes to their respective SCC indices
    indexed_sccs = {scc: idx for (idx, scc) in enumerate(sccs)}
    node_scc_index = {n: indexed_sccs[scc] for scc in sccs for n in scc}

    # collapse all strongly connected components
    for src, dst in dg.edges():
        scc_index = node_scc_index.get(src)
        if scc_index is not None:
            src = SCCPlaceholder(scc_index)
        scc_index = node_scc_index.get(dst)
        if scc_index is not None:
            dst = SCCPlaceholder(scc_index)

        if isinstance(src, SCCPlaceholder) and isinstance(dst, SCCPlaceholder) and src == dst:
            continue
        if src == dst:
            continue

        dg_copy.add_edge(src, dst)

    # add loners
    out_degree_zero_nodes = [node for (node, degree) in dg.out_degree() if degree == 0]
    for node in out_degree_zero_nodes:
        if dg.in_degree(node) == 0:
            dg_copy.add_node(node)

    # topological sort on acyclic graph `dg_copy`
    tmp_nodes = networkx.topological_sort(dg_copy)

    ordered_nodes = [ ]
    for n in tmp_nodes:
        if isinstance(n, SCCPlaceholder):
            _append_scc(dg, ordered_nodes, sccs[n.scc_id])
        else:
            ordered_nodes.append(n)

    return ordered_nodes

def _append_scc(graph, ordered_nodes, scc):
    """
    Append all nodes from a strongly connected component to a list of ordered nodes and ensure the topological
    order.

    :param networkx.DiGraph graph: The graph where all nodes belong to.
    :param list ordered_nodes:     Ordered nodes.
    :param iterable scc:           A set of nodes that forms a strongly connected component in the graph.
    :return:                       None
    """

    # find the first node in the strongly connected component that is the successor to any node in ordered_nodes
    loop_head = None
    for parent_node in reversed(ordered_nodes):
        for n in scc:
            if n in graph[parent_node]:
                loop_head = n
                break

        if loop_head is not None:
            break

    if loop_head is None:
        # randomly pick one
        loop_head = next(iter(scc))

    subgraph: DiGraph = graph.subgraph(scc).copy()
    for src, _ in list(subgraph.in_edges(loop_head)):
        subgraph.remove_edge(src, loop_head)

    ordered_nodes.extend(quasi_topological_sort(subgraph))

class SCCPlaceholder:
    __slots__ = ['scc_id']

    def __init__(self, scc_id):
        self.scc_id = scc_id

    def __eq__(self, other):
        return isinstance(other, SCCPlaceholder) and other.scc_id == self.scc_id

    def __hash__(self):
        return hash('scc_placeholder_%d' % self.scc_id)

def to_acyclic_graph(dg: DiGraph, ordered_nodes=None):
    """
    Convert a given DiGraph into an acyclic directed graph.

    :param networkx.DiGraph graph: The graph to convert.
    :param list ordered_nodes:     A list of nodes sorted in a topological order.
    :return:                       The converted directed acyclic graph.
    """

    if ordered_nodes is None:
        # take the quasi-topological order of the graph
        ordered_nodes = quasi_topological_sort(dg)

    dag = networkx.DiGraph()

    # add each node and its edge into the graph
    visited = set()
    for node in ordered_nodes:
        visited.add(node)
        dag.add_node(node)
        for successor in dg.successors(node):
            if successor not in visited:
                dag.add_edge(node, successor)

    return dag

def calculate_max_row(dag: DiGraph, ordered_nodes: Iterable) -> Tuple[Dict[Node, int], int]:
    """Calculate the maximum row ID using DFS.
    """
    max_row = 0
    max_rows = {}

    for node in ordered_nodes:
        if node not in max_rows:
            max_rows[node] = 0
        row = max_rows[node]
        max_row = max(max_row, row)
        for succ in dag.successors(node):
            if succ not in max_rows or max_rows[succ] < row + 1:
                max_rows[succ] = row + 1
                max_row = max(max_row, row + 1)

    return max_rows, max_row

def assign_rows(ordered_nodes: List[Node],
                max_rows: Dict[Node, int],
                node_compare_key) -> Tuple[Dict[Node, int], Dict[int, List]]:
    """Assign nodes to rows and provide a mapping to lookup all nodes given a
    row index.
    """

    # TODO: Isn't this rows Dict just a copy of max_rows?
    rows: Dict[Node, int] = {}
    row_to_nodes: Dict[int, List[Node]] = defaultdict(list)

    for node in ordered_nodes:
        # Push each node as far up as possible, unless it is the terminal node
        row = max_rows[node]
        rows[node] = row
        row_to_nodes[row].append(node)

    # Sort the nodes within a row
    row_to_nodes = {row: sorted(nodes, key=node_compare_key)
                    for row, nodes in row_to_nodes.items()}

    return rows, row_to_nodes

def assign_columns(dag: DiGraph,
                   row_to_nodes: Dict[int, List],
                   node_compare_key) -> Tuple[Dict[Node, int], Dict[Node, GridIndex], int]:
    """Assign nodes to columns and provide a mapping of nodes to a grid location, including
    the index within the grid cell.
    """
    cols: Dict[Node, int] = {}
    locations: Dict[Node, GridIndex] = {}
    global_max_col = 0

    # Assign initial column ID fromm bottom-up.
    # I.e., starting at the bottom rows.
    for row_idx in reversed(list(row_to_nodes.keys())):
        row_nodes = sorted(row_to_nodes[row_idx], key=node_compare_key)

        next_min_col = 1
        next_max_col = 2

        for node_idx, node in enumerate(row_nodes):
            succs = dag.successors(node)
            min_col = None
            max_col = None

            for succ in succs:
                if succ in cols:
                    succ_col = cols[succ]
                    if min_col is None or succ_col < min_col:
                        min_col = succ_col
                    if max_col is None or succ_col > max_col:
                        max_col = succ_col + 1

            if min_col is None and max_col is None:
                min_col = next_min_col
                max_col = next_max_col
            else:
                assert(min_col is not None)
                assert(max_col is not None)
                if min_col < next_min_col:
                    min_col = next_min_col
                # TODO: Should this be next_max_col?
                if max_col < next_min_col:
                    max_col = next_min_col + 1

            # Assign a column ID to current node
            col = (min_col + max_col) // 2
            cols[node] = col
            locations[node] = GridIndex(col, row_idx)
            global_max_col = max(global_max_col, col)

            # Update min_col and max_col for next iteration
            if min_col == max_col:
                next_min_col = max_col + 2
            else:
                next_min_col = max_col + 1
            next_max_col = next_min_col + 1

    # Adjust columns by top-down
    for row_idx, row_nodes in row_to_nodes.items():
        next_min_col = None
        next_max_col = None

        for idx, node in enumerate(row_nodes):
            preds = list(dag.predecessors(node))
            if len(preds) < 2:
                # Not enough predecessors to process
                col = cols[node]
                next_min_col = max(next_min_col if next_min_col is not None else 0, col + 2)
                next_max_col = max(next_max_col if next_max_col is not None else 0, col + 3)
                continue

            min_col = next_min_col
            max_col = next_max_col

            for pred in preds:
                if pred in cols:
                    pred_col = cols[pred]
                    if min_col is None or min_col > pred_col:
                        min_col = pred_col
                    if max_col is None or max_col < pred_col:
                        max_col = pred_col + 1

            # Try to align this node with predecessors and prevent overlaps
            # The min_col and max_col are defined by the predecessors
            assert(min_col is not None)
            assert(max_col is not None)
            col = (min_col + max_col) // 2
            has_overlap, col = detect_overlap(node, cols, col, row_nodes, min_col)

            # Assign a column ID to the current node
            cols[node] = col
            locations[node] = GridIndex(col, row_idx)

            next_min_col = max_col + 1
            next_max_col = next_min_col + 1

            global_max_col = max(global_max_col, col)

    return cols, locations, global_max_col + 1

def detect_overlap(node,
                   cols: Dict[Node, int],
                   ideal_col: int,
                   row_nodes: List[Node],
                   min_col: int) -> Tuple[bool, int]:
    overlap_detected = False
    suggested_col = min_col

    # Check for overlap
    for row_node in sorted(row_nodes, key=lambda n: cols[n]):
        if row_node is node:
            continue
        row_node_col = cols[row_node]
        if row_node_col - 1 <= ideal_col <= row_node_col + 1:
            # Detected collision
            overlap_detected = True
        if row_node_col - 1 <= suggested_col <= row_node_col + 1:
            # Adjust suggestion
            suggested_col = row_node_col + 2
        if overlap_detected and suggested_col < row_node_col - 1:
            # Have a working suggestion
            break

    if overlap_detected:
        return True, suggested_col
    else:
        return False, ideal_col

def route_edges(dg: DiGraph,
                node_locations: Dict[Node, GridIndex],
                max_col: int,
                max_row: int) -> Tuple[EdgeLayoutState, List[SegmentedEdge]]:

    # Initialize routing state
    state = EdgeLayoutState(max_col, max_row, node_locations)

    # Create edge objects
    edges = []
    for src, dst in dg.edges():
        edge, state = route_edge(state, src, dst)
        edges.append(edge)

    # Set in-edge indices
    state.set_in_edge_indices()

    # Set out-edge indices
    state.set_out_edge_indices()

    return state, edges

def route_edge(state: EdgeLayoutState,
               src: Node,
               dst: Node) -> Tuple[SegmentedEdge, EdgeLayoutState]:
    edge = SegmentedEdge(src, dst)

    start_gi = state.node_locations[src]
    start_col = start_gi.col
    start_row = start_gi.row
    end_gi = state.node_locations[dst]
    end_col = end_gi.col
    end_row = end_gi.row

    # Start from middle of the block (?)
    start_col += 1
    end_col += 1

    # Start from next row
    start_row += 1

    # Add (start?) of a vertical segment for 'edge'
    start_idx = assign_vertical_edge(state.vertical_edges,
                                     edge,
                                     start_col,
                                     start_row,
                                     0)
    edge.points.append(EdgeCoord(start_col, start_row, start_idx))

    if start_row < end_row:
        min_row = start_row
        max_row = end_row
    else:
        max_row = start_row
        min_row = end_row

    # Find a vertical column to route edge to target node
    col = start_col
    if not state.edge_available(col, min_row, max_row):
        offset = 1
        while True:
            if state.edge_available(col + offset, min_row, max_row):
                col = col + offset
                break
            if state.edge_available(col - offset, min_row, max_row):
                col = col - offset
                break
            offset += 1

    # If column changed, we need a horizontal line to connect them
    if col != start_col:
        if start_col < col:
            min_col = start_col
            max_col = col
            move = Move.RIGHT
        else:
            max_col = start_col
            min_col = col
            move = Move.LEFT

        edge_idx = assign_horizontal_edge(state.horizontal_edges,
                                          edge,
                                          min_col,
                                          start_row,
                                          max_col - min_col)
        edge.points.append(EdgeCoord(col, start_row, edge_idx))
        edge.moves.append(move)
    else:
        # We will also have a horizontal edge here just in case the two blocks don't align
        assign_horizontal_edge(state.horizontal_edges,
                               edge,
                               start_col,
                               start_row,
                               1)
        # Do not need to add point to the edge in this case

    if start_row != end_row:
        vert_row = min(start_row + 1, end_row)
        edge_idx = assign_vertical_edge(state.vertical_edges,
                                        edge,
                                        col,
                                        vert_row,
                                        abs(end_row - start_row) + 1)
        edge.points.append(EdgeCoord(col, end_row, edge_idx))

    if col != end_col:
        # Generate a line to move to target column
        if col < end_col:
            min_col = col
            max_col = end_col
            move = Move.RIGHT
        else:
            max_col = col
            min_col = end_col
            move = Move.LEFT
        edge_idx = assign_horizontal_edge(state.horizontal_edges,
                                          edge,
                                          min_col,
                                          end_row,
                                          max_col - min_col)
        edge.points.append(EdgeCoord(end_col, end_row, edge_idx))
        edge.moves.append(move)

        # Move downwards
        # In a new grid cell, need a new edge index
        edge_idx = assign_vertical_edge(state.vertical_edges,
                                        edge,
                                        end_col,
                                        end_row,
                                        0)
        edge.points.append(EdgeCoord(end_col, end_row, edge_idx))

    state.out_edges[edge.src].append(edge)
    state.in_edges[edge.dst].append(edge)

    return edge, state

def first_unused_index(indices: Set[int]) -> int:
    sorted_indices = sorted(indices)

    # Find first unused index
    if not sorted_indices:
        # No used indices
        return 0
    elif len(sorted_indices) == 1:
        # One used index
        # It should be the case that a lone index is always 0
        # TODO: Is that true?
        assert(sorted_indices[0] == 0)
        return 1
    else:
        # TODO: Gaps could come in because of minimizing edge overlap?
        # Check for gaps
        for prev_idx, next_idx in zip(sorted_indices[:-1], sorted_indices[1:]):
            if prev_idx + 1 != next_idx:
                # Gap found
                return prev_idx + 1
    # If we make it here, append a new index to the end
    return sorted_indices[-1] + 1

def assign_vertical_edge(vertical_edges: Grid[Dict[EdgeIndex, SegmentedEdge]],
                         edge: SegmentedEdge,
                         col: int,
                         row: int,
                         num_blocks: int) -> EdgeIndex:

    # Find available index
    indices: Set[EdgeIndex] = set()
    start_row = row
    end_row = row + num_blocks
    for r in range(start_row, end_row + 1):
        if vertical_edges[col][r]:
            indices.update(vertical_edges[col][r].keys())
    edge_index = first_unused_index(indices)

    for r in range(start_row, end_row + 1):
        vertical_edges[col][r][edge_index] = edge

    return edge_index

def assign_horizontal_edge(horizontal_edges: Grid[Dict[EdgeIndex, SegmentedEdge]],
                           edge: SegmentedEdge,
                           col: int,
                           row: int,
                           num_blocks: int) -> EdgeIndex:

    # Find available index
    indices: Set[EdgeIndex] = set()
    start_col = col
    end_col = col + num_blocks
    for c in range(start_col, end_col + 1):
        if horizontal_edges[c][row]:
            indices.update(horizontal_edges[c][row].keys())
    edge_index = first_unused_index(indices)

    for c in range(start_col, end_col + 1):
        horizontal_edges[c][row][edge_index] = edge

    return edge_index

def calculate_max_edge_indices(edges: Grid[Dict[EdgeIndex, SegmentedEdge]]) -> Dict[GridIndex, EdgeIndex]:
    """Find the largest edge index used for each grid cell.
    """

    result: Dict[GridIndex, EdgeIndex] = {}

    for col, row_edges in enumerate(edges):
        for row, edge_segments in enumerate(row_edges):
            if not edge_segments:
                continue
            grid_index = GridIndex(col, row)
            result[grid_index] = max(edge_segments.keys())

    return result


def make_grids(max_row: int,
               max_col: int,
               max_vedge_indices: Dict[GridIndex, EdgeIndex],
               max_hedge_indices: Dict[GridIndex, EdgeIndex],
               nodes: Iterable,
               locations: Dict[Node, GridIndex],
               sizes: Dict[Node, NodeSize],
               x_margin: int,
               y_margin: int) -> Tuple[List[int], List[int]]:
    """Calculate the width of each column and height of each row.
    """
    border_min_width = 20
    row_heights = [0] * (max_row + 2)
    col_widths = [0] * (max_col + 2)

    # Update grid sizes based on nodes
    for node in nodes:
        loc = locations[node]
        size = sizes[node]

        if row_heights[loc.row] < size.height:
            row_heights[loc.row] = size.height

        if col_widths[loc.col] < size.width // 2:
            col_widths[loc.col] = size.width // 2
        next_col = loc.col + 1
        if (next_col < len(col_widths) and
            col_widths[next_col] < size.width // 2):
            col_widths[next_col] = size.width // 2

    # Update grid sizes based on edges
    for col in range(len(col_widths)):
        for row in range(len(row_heights)):
            grid_idx = GridIndex(col, row)
            if grid_idx in max_vedge_indices:
                col_width = (max_vedge_indices[grid_idx] + 2) * x_margin
                if col_widths[col] < col_width:
                    col_widths[col] = col_width
            if grid_idx in max_hedge_indices:
                row_height = (max_hedge_indices[grid_idx] + 2) * y_margin
                if row_heights[row] < row_height:
                    row_heights[row] = row_height

    # The left-most and right-most columns do not have nodes assigned.
    # But they may have edges assigned. Ensure a minimum width.
    col_widths[0] = max(border_min_width, col_widths[0])
    col_widths[-1] = max(border_min_width, col_widths[-1])

    return row_heights, col_widths

def find_nonintersecting_y(grid_coords: Dict[GridIndex, Point],
                           row_heights: List[int],
                           row: int,
                           starting_col: int,
                           next_col: int,
                           default_y: int) -> int:
    """
    Find the y-coordinate for a point on an edge that will not lead to the edge segment
    intersecting with any nodes betweeng `starting_col` and `ending_col`.
    """
    max_y = None

    if starting_col <= next_col:
        min_col = starting_col
        max_col = next_col
    else:
        min_col = next_col
        max_col = starting_col

    # Find all grids in range and use to push to a larger y-coordinate (move down in the scene)
    for col in range(min_col, max_col + 1):
        key = GridIndex(col, row)
        if key not in grid_coords:
            continue
        pt = grid_coords[key]
        new_y = pt.y + row_heights[row]
        if max_y is None or new_y > max_y:
            max_y = new_y

    return max_y if max_y is not None else default_y

def calculate_coordinates(max_row: int,
                          max_col: int,
                          row_heights: List[int],
                          col_widths: List[int],
                          locations: Dict[Node, GridIndex],
                          max_vedge_indices: Dict[GridIndex, EdgeIndex],
                          max_hedge_indices: Dict[GridIndex, EdgeIndex],
                          row_margin: int,
                          col_margin: int,
                          # x_margin and y_margin are edge margins?
                          x_margin: int,
                          y_margin: int,
                          nodes: List[Node],
                          node_sizes: Dict[Node, NodeSize],
                          edges: List[SegmentedEdge]) -> LayoutResult:
    row_max_idxs: Dict[int, EdgeIndex] = {}
    grid_coords: Dict[GridIndex, Point] = {}
    node_coords: Dict[Node, Point] = {}

    # Find the max edge indices for each of the rows
    for loc, loc_max_idx in max_hedge_indices.items():
        row_max_idxs[loc.row] = max(loc_max_idx, row_max_idxs[loc.row]) \
            if loc.row in row_max_idxs else loc_max_idx

    # Calculate the top margin based on number of horzontal edges above
    top_margin = row_margin * 2
    if 0 in row_max_idxs:
        # TODO: Why the +2 Is this something like there should always be at least the equivalent of
        #       two edges for computing margins?
        top_margin += y_margin * (row_max_idxs[0] + 2)
    y = top_margin

    # Calculate the grid scene coordinates
    for row in range(-1, max_row + 2):
        x = 0
        for col in range(-1, max_col + 2):
            grid_coords[GridIndex(col, row)] = Point(x, y)
            x += col_widths[col] + col_margin
        # TODO: Should row_heights be a defaultdict(0)?
        if row_heights[row] is None:
            row_heights[row] = 0

        # Calculate the bottom margin based on the number of horizontal edges below
        bottom_margin = row_margin * 2
        if (row + 1) in row_max_idxs:
            bottom_margin += y_margin * (row_max_idxs[row + 1] + 2)
        y += row_heights[row] + bottom_margin

    # Use grid coordinates to calculate node scene coordinates
    for node in nodes:
        grid_loc = locations[node]
        grid_coord = grid_coords[grid_loc]
        grid_a_width = col_widths[grid_loc.col]
        grid_b_width = col_widths[grid_loc.col + 1]
        grid_height = row_heights[grid_loc.row]
        node_size = node_sizes[node]

        # Place the "center" of the node in the center of the grid cell.
        # NB: This horizontal position is based on the width of two columns.
        node_coords[node] = Point(grid_coord.x + ((grid_a_width + grid_b_width) // 2 - node_size.width // 2),
                                  grid_coord.y + (grid_height // 2 - node_size.height // 2))

    # Use grid coordinates to calculate edge scene coordinates
    for edge in edges:
        src_loc = node_coords[edge.src]
        src_size = node_sizes[edge.src]
        dst_loc = node_coords[edge.dst]
        dst_size = node_sizes[edge.dst]

        start_x_index = edge.points[0].idx
        start_point_x_base = src_loc.x + src_size.width // 2 - (x_margin * (edge.max_start_index + 1) // 2)
        start_point_x = start_point_x_base + (start_x_index * x_margin)
        start_point = Point(start_point_x, src_loc.y + src_size.height)
        edge.coordinates.append(start_point)

        prev_grid_coord: GridIndex = locations[edge.src]
        prev_grid_coord = GridIndex(prev_grid_coord.col + 1,
                               prev_grid_coord.row + 1)

        if len(edge.points) > 1:
            next_point = edge.points[1]
            next_col = next_point.col
            next_idx = next_point.idx
            starting_grid_coord: GridIndex = locations[edge.src]
            starting_row = starting_grid_coord.row
            starting_col = starting_grid_coord.col
            y_base = find_nonintersecting_y(grid_coords,
                                            row_heights,
                                            starting_row,
                                            starting_col,
                                            next_col,
                                            start_point.y) + row_margin
            y = y_base + (next_idx * y_margin)
        else:
            y = start_point.y

        # Add vertical segment, moving downward
        edge.add_coord(Point(start_point.x, y))

        prev_scene_pt = Point(start_point.x, y)
        curr_scene_pt = Point(0, 0)
        # For each point on the edge's line segments
        for pt_idx, pt_edge_coord in enumerate(edge.points[1:-1]):
            if pt_edge_coord.col == prev_grid_coord.col:
                assert pt_edge_coord.row != prev_grid_coord.row
                # Vertical
                curr_scene_pt.x = prev_scene_pt.x

                prev_row = pt_edge_coord.row-1
                base_y = (grid_coords[GridIndex(pt_edge_coord.col, prev_row)].y +
                          row_heights[prev_row] +
                          row_margin)

                # If this is the penultimate point
                if pt_idx + 1 == len(edge.points) - 2:
                    curr_scene_pt.y = base_y
                else:
                    # We add (+1) to fix the off-by-one index,
                    # and another (+1) to get the next point's grid coordinates
                    next_coord = edge.points[pt_idx + 1 + 1]
                    curr_scene_pt.y = base_y + (next_coord.idx + y_margin)
            elif pt_edge_coord.row == prev_grid_coord.row:
                assert pt_edge_coord.col != prev_grid_coord.col
                # Horizonal
                # If this is the penultimate point
                if pt_idx + 1 == len(edge.points) - 2:
                    base_x = dst_loc.x + dst_size.width // 2
                    assert edge.end_index is not None
                    curr_scene_pt.x = base_x + (edge.end_index * x_margin)
                else:
                    # We add (+1) to fix the off-by-one index,
                    # and another (+1) to get the next point's grid coordinates
                    next_coord = edge.points[pt_idx + 1 + 1]
                    base_x = grid_coords[GridIndex(pt_edge_coord.col, pt_edge_coord.row)].x
                    curr_scene_pt.x = base_x + (next_coord.idx * x_margin)

                curr_scene_pt.y = prev_scene_pt.y
            else:
                # Verify we didn't reach an unexpected case
                assert False

            edge.add_coord(curr_scene_pt)

            # Update the previous point grid coordinates and scene coordinates
            prev_grid_coord = GridIndex(pt_edge_coord.col, pt_edge_coord.row)
            prev_scene_pt = dataclasses.replace(curr_scene_pt)

        # Handle the last point. It will always be at the top of the destination node.
        assert edge.max_end_index is not None
        base_x = dst_loc.x + dst_size.width // 2 - (x_margin * (edge.max_end_index + 1) // 2)
        end_edge_coord = edge.points[-1]
        x = base_x + (end_edge_coord.idx * x_margin)
        if x != prev_scene_pt.x:
            # Move horizontally if needed
            edge.add_coord(Point(x, prev_scene_pt.y))
        end_point = Point(x, dst_loc.y - y_margin)
        edge.add_coord(end_point)

    edge_coords: Dict[Edge, List[Point]] = {Edge(e.src, e.dst): e.coordinates for e in edges}

    return LayoutResult(node_coords, edge_coords)
