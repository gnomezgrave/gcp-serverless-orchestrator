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

        if not task:
            print(f"The event is not recognized: {data}")
            return

        # First, we need to initialize the Execution Status and Orchestration Status objects with the run_id.
        if task.target_type == TargetTypes.START:
            # If it's the start event, get the run_id from the Start event.
            run_id = task.run_id
            self._orchestration_status.set_run_id(run_id)
        else:
            # If it's an intermediate task/event, retrieve the run_id from the saved execution.
            execution = self._exec_status.get_execution(task.execution_id)
            run_id = execution['run_id']

            task.set_run_id(run_id)
            self._orchestration_status.set_run_id(run_id)

            print(f"Execution: {execution}")

        print(f"Run ID: {run_id}")

        dag = DAGBuilder(dag=self._dag_definition, exec_status=self._exec_status,
                         orchestration_status=self._orchestration_status).build_dag()
        all_tasks = dag.all_tasks

        # This defines the next node that should be triggered.
        next_node = None

        if task.target_type == TargetTypes.START:
            # Save all the Nodes if this is the first execution of the orchestration.
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
            # Update the current status of the completed Task,
            # so we can determine the overall status of the orchestration.
            self._orchestration_status.update_task_status(node)

            parent_dag = node.parent_dag

            # Every Node MUST have a parent DAG. This is just a safety check.
            if not parent_dag:
                print(f"Something is wrong! A Node should have a parent DAG. But none found for: {node.node_name}")
                return

            parent_node = parent_dag.parent_node
            print(f"Parent node {parent_node}")

            if node.is_end:
                print(f"This is the end: {task.task_name}")
                parent_dag = node.parent_dag
                parent_node = parent_dag.parent_node

                # If the immediate parent DAG of current Node doesn't have a parent node, that means it belongs to the
                # root DAG (the most outer DAG). In this case, we don't need to trigger anything. Maybe we can decide to
                # save some information or update the overall status of the orchestration here.
                if not parent_node:
                    print(f"This is the real end!")
                elif parent_node.node_type == NodeTypes.PARALLEL:
                    # If there is a parent Node for the current DAG, it means the Node that just finished is a
                    # part of a child DAG (i.e. a branch of a Parallel node).
                    # Then we need to check the statuses of the other branches to decide the next node.
                    all_done = True
                    for branch in parent_node.branches:
                        # TODO: Handle failed tasks
                        statuses = {
                            node_name: n.status == TaskStatus.COMPLETED for node_name, n in branch.nodes.items()
                        }
                        if False in statuses.values():
                            # If branches have at least one incomplete Task, we don't need to do anything,
                            # as the next can be determined eventually when those Tasks are completed.
                            print(f"Still some tasks to get triggered of: {branch.start_node.node_name}")
                            all_done = False
                            break
                        else:
                            print(f"All steps are done in the DAG: {branch.start_node.node_name}")

                    # If all the Tasks are completed in all the branches, we need to pick the next Node as the next of
                    # the parent Node (which is defined as the next of the Parallel Node in this case).
                    # Else, we don't need to do anything at the moment.
                    if all_done:
                        parent_node.set_status(TaskStatus.COMPLETED)
                        next_node = parent_node.next
                    else:
                        parent_node.set_status(TaskStatus.PENDING)
                        next_node = None
                else:
                    # The type of the parent Node is not implemented yet! This is just a fail-safe for now.
                    print(f"Not implemented! :{parent_node.to_json()}")
            else:
                # If this Node was not the end node of the DAG, we can directly pick the next task to be executed.
                next_node = node.next

        # Now we should save the current state of the orchestration.
        # We have this statement here, in case there is no next node, but we still will save the status.
        self._orchestration_status.save_orchestration_status()

        if not next_node:
            print(f"No next node found.")
            return

        print(f"Next node: {next_node.node_name}")

        # Now we execute the selected next Node.
        next_node.execute()

        # Then we save the orchestration status again with the new state of the executed Task.
        self._orchestration_status.save_orchestration_status()
