from google.cloud import storage

from .dag_builder import DAGBuilder
from .status import OrchestrationStatus, ExecutionStatus
from .events import EventsFactory
from .enums import TargetTypes, TaskStatus, NodeTypes


class DAGExecutor:
    def __init__(self, dag_definition, bucket_name):
        self._dag_definition = dag_definition
        self._bucket_name = bucket_name
        self._bucket = storage.Client().get_bucket(bucket_name)
        self._orchestration_status = OrchestrationStatus(self._bucket)
        self._exec_status = ExecutionStatus(self._bucket)

    def execute(self, data):

        task = EventsFactory.create_from_event(event_data=data)

        if task.target_type == TargetTypes.START:
            run_id = task.run_id
            self._orchestration_status.set_run_id(run_id)
        else:
            execution = self._exec_status.get_execution(task.execution_id)
            run_id = execution['run_id']

            task.set_run_id(run_id)
            self._orchestration_status.set_run_id(run_id)

            print(f"Execution: {execution}")
            print(f"Run ID: {run_id}")

        # TODO: pass the orchestration status to update the task statuses
        dag = DAGBuilder(dag=self._dag_definition, exec_status=self._exec_status,
                         orchestration_status=self._orchestration_status).build_dag()
        all_tasks = dag.all_tasks

        node = None
        next_node = None

        if task.target_type == TargetTypes.START:
            next_node = dag.start_node
            initial_status = {
                node_name: node.to_json()
                for node_name, node in dag.all_nodes.items()
            }
            self._orchestration_status.set_initial_status(initial_status)
        else:
            node = all_tasks.get(task.task_name)
            if not node:
                print(f"This task is not tracked: {task.task_name}")
                return

            node.set_status(task.status)
            self._orchestration_status.update_task_status(node)

            parent_dag = node.parent_dag

            if not parent_dag:
                print(f"Something is wrong! A Node should have a parent DAG. But none found for: {node.node_name}")
                return

            parent_node = parent_dag.parent_node
            print(f"Parent node {parent_node}")

            if node.is_end:
                print(f"This is the end: {task.task_name}")
                parent_dag = node.parent_dag
                parent_node = parent_dag.parent_node

                if not parent_node:
                    print(f"This is the real end!")
                elif parent_node.node_type == NodeTypes.PARALLEL:
                    all_done = True
                    for branch in parent_node.branches:
                        # TODO: Handle failed tasks
                        statuses = {
                            node_name: n.status == TaskStatus.COMPLETED for node_name, n in branch.nodes.items()
                        }
                        if False in statuses.values():
                            print(f"Still some tasks to get triggered of: {branch.start_node.node_name}")
                            all_done = False
                            break
                        else:
                            print(f"All steps are done in the DAG: {branch.start_node.node_name}")

                    if all_done:
                        parent_node.set_status(TaskStatus.COMPLETED)
                        next_node = parent_node.next
                    else:
                        # If this is the END of the DAG, there is nothing to do.
                        parent_node.set_status(TaskStatus.PENDING)
                        next_node = None

            else:
                next_node = node.next

        self._orchestration_status.save_orchestration_status()

        if not next_node:
            print(f"No next node found.")
            return

        print(f"Next node: {next_node.node_name}")

        next_node.execute()
        self._orchestration_status.save_orchestration_status()
