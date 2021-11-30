from .nodes import Node
from .enums import NodeTypes


class DAG:
    def __init__(self, nodes: dict, start_node_name: str, parent_step: Node = None):
        self._parent = parent_step
        self._nodes = nodes
        self._start = start_node_name
        self.__tasks = {
            node.target_name: node
            for node_name, node in nodes.items()
            if node.node_type == NodeTypes.TASK
        }

    @property
    def nodes(self):
        return self._nodes

    @property
    def tasks(self):
        return self.__tasks

    def get_node_with_task(self, task_name):
        return self.__tasks.get(task_name)

    def get_start_node(self):
        return self._nodes.get(self._start)

    def get_all_tasks(self):
        tasks = dict()
        self._get_tasks(self, tasks)
        return tasks

    def _get_tasks(self, dag, tasks):
        for node_name, node in dag.nodes.items():
            if node.node_type == NodeTypes.TASK:
                tasks[node.target_name] = node
            elif node.node_type == NodeTypes.PARALLEL:
                for branch in node.branches:
                    self._get_tasks(branch, tasks)
