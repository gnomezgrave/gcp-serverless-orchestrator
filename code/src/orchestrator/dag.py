from .nodes import Node
from .enums import NodeTypes


class DAG:
    def __init__(self, nodes: dict, start_node_name: str, parent_step: Node, exec_status, orchestration_status):
        self._nodes = nodes
        self._start = start_node_name
        self._parent = parent_step
        self._exec_status = exec_status
        self._orchestration_status = orchestration_status
        self._tasks = None
        self._all_nodes = None
        self._all_tasks = None

    def init(self):
        # We need to explicitly call this function to initialize the DAG.
        # This was done because we should already know all the nodes in the DAG
        # to create the two attributes _all_nodes and _all_tasks.
        self._tasks = {
            node.target_name: node
            for node_name, node in self.nodes.items()
            if node.node_type == NodeTypes.TASK
        }
        self._all_nodes, self._all_tasks = self._get_all_nodes()

    @property
    def parent_node(self):
        return self._parent

    @property
    def exec_status(self):
        return self._exec_status

    @property
    def orchestration_status(self):
        return self._orchestration_status

    @property
    def nodes(self):
        return self._nodes

    @property
    def tasks(self):
        return self._tasks

    @property
    def all_tasks(self):
        return self._all_tasks

    @property
    def all_nodes(self):
        return self._all_nodes

    @property
    def start_node(self):
        return self._nodes.get(self._start)

    def get_node_with_task(self, task_name):
        return self._tasks.get(task_name)

    def _get_all_nodes(self):
        nodes = {}
        tasks = {}
        self._traverse_all_nodes(self, nodes, tasks)
        return nodes, tasks

    def _traverse_all_nodes(self, dag, nodes, tasks):
        for node_name, node in dag.nodes.items():
            nodes[node.node_name] = node

            if node.node_type == NodeTypes.TASK:
                tasks[node.target_name] = node

            if node.node_type == NodeTypes.PARALLEL:
                for branch in node.branches:
                    self._traverse_all_nodes(branch, nodes, tasks)
