from .enums import NodeTypes
from .node_factory import NodeFactory
from .dag import DAG


class DAGBuilder:

    def __init__(self, dag):
        self._dag = dag
        self._steps = None
        self._nodes = dict()

    def _build(self, node, functions_list):
        steps = node['steps']
        for k, v in steps.items():
            node_type = v['type']
            # TODO: Don't append everything for Parallels
            functions_list.append((k, v))

            if node_type == 'Parallel':
                branches = v['branches']
                for branch in branches:
                    self._build(branch, functions_list)

    def _extract_steps(self, dag):
        steps_list = []
        self._build(dag, steps_list)
        step_names = dict()

        for step_name, step in steps_list:
            step['step_name'] = step_name

            if step_name not in step_names:
                step_names[step_name] = step
            else:
                raise Exception(f"Duplicate Step Name found: {step}")

        return step_names

    def _build_dag(self, sub_dag, parent_node=None):
        start_step_name = sub_dag['start']
        nodes = dict()
        for step_name, step in sub_dag['steps'].items():
            node = self._get_node(step_name, step)

            if node.node_type == NodeTypes.PARALLEL:
                branches = step['branches']
                for branch in branches:
                    node.add_branch(self._build_dag(branch, node))

            next_step_name = step.get('next')
            if next_step_name:
                next_step = self._steps[next_step_name]
                next_node = self._get_node(next_step_name, next_step)
                node.set_next(next_node)

            nodes[node.node_name] = node

        return DAG(nodes, start_step_name, parent_node)

    def _get_node(self, step_name, step):
        if step_name in self._nodes:
            node = self._nodes[step_name]
        else:
            node = NodeFactory.create_node(step)
            self._nodes[step_name] = node

        return node

    def build_dag(self):
        self._steps = self._extract_steps(self._dag)
        dag = self._build_dag(self._dag)
        return dag
