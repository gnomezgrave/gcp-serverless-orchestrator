from .enums import NodeTypes, TargetTypes
from .nodes import Function, CloudFunctionTask, DataflowJob, Parallel


class NodeFactory:

    def __init__(self, steps_map):
        self._steps_map = steps_map

    @staticmethod
    def create_node(step, parent_dag):
        # Should have only one of them, but not both!
        if bool('end' in step) == bool('next' in step):
            raise Exception(f"Only one of 'end' and 'next' should be defined for the same Step! step_name={step}")

        node = None

        if step['type'] == NodeTypes.TASK.value:
            # Select the correct TASK class.
            # TODO: Separate the Node creation
            targets = {
                TargetTypes.FUNCTION.value: Function,
                TargetTypes.CLOUD_FUNCTION.value: CloudFunctionTask,
                TargetTypes.DATAFLOW_JOB.value: DataflowJob
            }
            target_type = step['target_type']
            target_class = targets.get(target_type)
            if target_class:
                node = target_class(node_name=step['step_name'], target_name=step['target_name'],
                                    function=step.get('function'), parameters=step.get('parameters'),
                                    project_id=step.get('project_id'),
                                    parent_dag=parent_dag,
                                    container_gcs_path=step.get('container_gcs_path'), region=step.get('region'))
            else:
                raise Exception(f"Unsupported Task type: {target_type}")

        elif step['type'] == NodeTypes.PARALLEL.value:
            node = Parallel(node_name=step['step_name'], parent_dag=parent_dag)

        if step.get('end', False):
            node.set_as_end()

        return node
