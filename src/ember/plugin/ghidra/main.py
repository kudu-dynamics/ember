from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget
import grpc
import ember.plugin.ghidra.location_pb2 as location_pb2
import ember.plugin.ghidra.location_pb2_grpc as location_pb2_grpc
from ember.ui.widgets.graph import FlowGraphWidget, FlowGraphNode
import ember.ui.widgets.graph as graph 
from networkx import DiGraph


def setLocation(offset: int):
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    print("Will try to greet world ...")
    with grpc.insecure_channel('localhost:50058') as channel:
        stub = location_pb2_grpc.LocationSyncStub(channel)

        # create a proto message 
        location = location_pb2.Location(offset=offset)

        # send request using created stub 
        response = stub.setLocation(location)
    print("Greeter client received: " + response.message)


class BasicBlock:
    
    def __init__(self,
                 start_addr: int,
                 data: str):

        self.start_addr = start_addr
        self.data = data

    def __lt__(self, other):
        return self.start_addr < other.start_addr

    def __gt__(self, other):
        return self.start_addr > other.start_addr

    def __le__(self, other):
        return self.start_addr <= other.start_addr

    def __ge__(self, other):
        return self.start_addr >= other.start_addr

    def __eq__(self, other):
        return self.start_addr == other.start_addr
    
    def __hash__(self):
        return id(self)
    # hash(self.start_addr)

    def __str__(self):
        return f'{hex(self.start_addr)}\n{self.data}'

class BasicBlockNode(FlowGraphNode):
    def __init__(self,
                 data: BasicBlock,
                 ):
        super().__init__(data)
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        setLocation(self.data.start_addr)
        super().mousePressEvent(event)
        print(self.data)
    

class DemoGraph(FlowGraphWidget):    

    def __init__(self, parent: QWidget = None):
        g = DiGraph()
        a = BasicBlock(0x010115e, 'a')
        b = BasicBlock(0x0101301, 'b')
        c = BasicBlock(0x01012e8, 'c')
        d = BasicBlock(0x01013d1, 'd')
        e = BasicBlock(0x01013fb, 'e')
        f = BasicBlock(0x010129d, 'f')

        g.add_edge(a, b)
        g.add_edge(a, c)
        g.add_edge(b, d)
        g.add_edge(c, d)
        g.add_edge(d, e)
        g.add_edge(b, e)
        # g.add_edge(e, e)
        # g.add_edge(e, c)
        # g.add_edge(c, e)
        g.add_edge(e, f)
        g.add_edge(d, f)

        super().__init__(graph=g, parent=parent, node_ctor=lambda n: BasicBlockNode(n), sort_node_on=lambda n: n.data)
