from .enums import NodeTypes, TaskStatus
from .node_factory import NodeFactory
from .dag import DAG


class DAGBuilder:

    def __init__(self, dag, exec_status, orchestration_status):
        self._dag = dag
        self._steps = None
        self._nodes = dict()
        self._exec_status = exec_status
        self._orchestration_status = orchestration_status

    def _build(self, node, functions_list):
        # This function recursively builds the DAG and the child DAGs.
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
        # This function recursively creates DAGs according to the DAG definition.
        start_step_name = sub_dag['start']
        nodes = dict()
        dag = DAG(nodes, start_step_name, parent_node, self._exec_status, self._orchestration_status)
        for step_name, step in sub_dag['steps'].items():
            node = self._get_node(step_name, step, dag)

            if node.node_type == NodeTypes.PARALLEL:
                branches = step['branches']
                for branch in branches:
                    # Create a new DAG for each branch
                    node.add_branch(self._build_dag(branch, node))

            # Set the next Node for the current Node
            next_step_name = step.get('next')
            if next_step_name:
                next_step = self._steps[next_step_name]
                next_node = self._get_node(next_step_name, next_step, dag)
                node.set_next(next_node)

            nodes[node.node_name] = node

        # We need to explicitly call the init() of the DAG.
        dag.init()
        return dag

    def _get_node(self, step_name, step, parent_dag):
        # This function acts as a cache for Nodes, and returns the already created Node if there is,
        # else creates a new one.
        if step_name in self._nodes:
            node = self._nodes[step_name]
        else:
            node = NodeFactory.create_node(step, parent_dag)
            self._nodes[step_name] = node

            # Set the Task status extracted from the Orchestration Status file.
            orchestration_node = self._orchestration_status.get_task_status(step_name)
            if orchestration_node and 'status' in orchestration_node:
                node.set_status(TaskStatus(orchestration_node['status']))

        return node

    def build_dag(self):
        # We need to extract the steps separately to ensure we have all the nodes before building the DAG.
        self._steps = self._extract_steps(self._dag)
        dag = self._build_dag(self._dag)
        return dag
