import os
import json
import base64
import logging

from orchestrator import DAGBuilder, OrchestrationStatus, ExecutionStatus
from orchestrator import EventsFactory
from orchestrator import TargetTypes, TaskStatus, NodeTypes

from orchestration_dag_definition import OrchestrationDagDefinition

logging.getLogger().setLevel(logging.DEBUG)


def on_pub_sub_event(event, context):
    """Triggered by a cloud scheduler daily. Triggers a Dataflow job to process image data.
    Args:
        event: Event from the trigger
        context (google.cloud.functions.Context): Metadata for the event.
    """

    data = base64.b64decode(event['data']).decode('utf-8')
    print(f"JSON data: {data}")
    data = json.loads(data)

    status_bucket_name = os.environ.get('STATUS_BUCKET', 'orchestration-status-bucket-edge-default')

    task = EventsFactory.create_from_event(event_data=data)

    dag_definition = OrchestrationDagDefinition.get_dag()
    # TODO: pass the orchestration status to update the task statuses
    dag = DAGBuilder(dag=dag_definition).build_dag()
    all_tasks = dag.all_tasks
    exec_status = ExecutionStatus(status_bucket_name)

    node = None
    next_node = None

    orchestration_status = OrchestrationStatus(bucket_name=status_bucket_name)

    if task.target_type == TargetTypes.START:
        next_node = dag.start_node
        run_id = task.run_id
        orchestration_status.set_run_id(run_id)
        initial_status = {
            node_name: node.to_json()
            for node_name, node in dag.all_nodes.items()
        }
        orchestration_status.set_initial_status(initial_status)
    else:
        execution = exec_status.get_execution(task.execution_id)
        run_id = execution['run_id']
        print("Execution", execution)
        print("Run ID", run_id)

        task.set_run_id(run_id)
        orchestration_status.set_run_id(run_id)

        node = all_tasks.get(task.task_name)
        if not node:
            print(f"This task is not tracked: {task.task_name}")
            return

        node.set_status(task.status)
        orchestration_status.update_task_status(node)

        parent_dag = node.parent_dag

        if not parent_dag:
            print(f"Something is wrong! A Node should have a parent DAG. But none found for: {node.node_name}")
            return

        parent_node = parent_dag.parent_node
        print("Parent node", parent_node)

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
                        node_name: node.status == TaskStatus.COMPLETED for node_name, node in branch.nodes.items()
                    }
                    if False in statuses.values():
                        print("Still some tasks to get triggered.")
                        all_done = all_done and False
                        break
                    else:
                        print("All steps are done in the DAG!")
                        all_done = all_done and True

                if all_done:
                    parent_node.set_status(TaskStatus.COMPLETED)
                    next_node = parent_node.next
                else:
                    # If this is the END of the DAG, there is nothing to do.
                    parent_node.set_status(TaskStatus.RUNNING)
                    next_node = None

        else:
            next_node = node.next

    if not next_node:
        print(f"No next node found.")
        return

    print("Next node", next_node.node_name)

    # TODO: Fix saving the executions
    executions = next_node.execute()

    if not executions:
        print("Something went wrong!")
        return

    for execution in executions:
        exec_obj = execution[0]
        node = execution[1]
        exec_obj['run_id'] = run_id
        exec_status.save_execution(exec_obj)
        if node.node_type == NodeTypes.TASK:
            orchestration_status.update_task_status(node)

    orchestration_status.save_orchestration_status()


if __name__ == '__main__':
    event = {
        "textPayload": "Function execution started",
        "insertId": "000000-610275f2-c2dd-40bc-b8d3-1e80b1906830",
        "resource": {
            "type": "cloud_function",
            "labels": {
                "project_id": "trv-hs-src-consolidation-test",
                "function_name": "orch-test-1",
                "region": "europe-west1"
            }
        },
        "timestamp": "2021-11-16T20:27:20.256255690Z",
        "severity": "DEBUG",
        "labels": {
            "execution_id": "frkqgv7h4s86"
        },
        "logName": "projects/trv-hs-src-consolidation-test/logs/cloudfunctions.googleapis.com%2Fcloud-functions",
        "trace": "projects/trv-hs-src-consolidation-test/traces/4f1fa5e834247f28382e1ae2d571ad7d",
        "receiveTimestamp": "2021-11-16T20:27:30.465945431Z"
    }

    event = {"resource": {"type": "start"}}

    # event = {
    #     "textPayload": "Function execution took 5 ms, finished with status code: 200",
    #     "insertId": "000000-a8c36fc4-754c-4244-b57e-8c2f64990ed6",
    #     "resource": {
    #         "type": "cloud_function",
    #         "labels": {
    #             "project_id": "trv-hs-src-consolidation-test",
    #             "region": "europe-west1",
    #             "function_name": "orch-test-1"
    #         }
    #     },
    #     "timestamp": "2021-11-29T20:18:35.496750640Z",
    #     "severity": "DEBUG",
    #     "labels": {
    #         "execution_id": "an76uyawgxow"
    #     },
    #     "logName": "projects/trv-hs-src-consolidation-test/logs/cloudfunctions.googleapis.com%2Fcloud-functions",
    #     "trace": "projects/trv-hs-src-consolidation-test/traces/142fa8e3bb8056e7ecc6ff52e4bbb4af",
    #     "receiveTimestamp": "2021-11-29T20:18:45.663684339Z"
    # }

    # event = {
    #     "textPayload": "Worker pool stopped.",
    #     "insertId": "qn1qtncdm4",
    #     "resource": {
    #         "type": "dataflow_step",
    #         "labels": {
    #             "step_id": "",
    #             "job_name": "word-count-3",
    #             "project_id": "823514981911",
    #             "region": "europe-west4",
    #             "job_id": "2021-12-05_04_54_17-499810410684916097"
    #         }
    #     },
    #     "timestamp": "2021-12-05T13:03:23.169986038Z",
    #     "severity": "INFO",
    #     "labels": {
    #         "dataflow.googleapis.com/region": "europe-west4",
    #         "dataflow.googleapis.com/job_name": "word-count-3",
    #         "dataflow.googleapis.com/job_id": "2021-12-05_04_54_17-499810410684916097",
    #         "dataflow.googleapis.com/log_type": "system"
    #     },
    #     "logName": "projects/trv-hs-src-consolidation-test/logs/dataflow.googleapis.com%2Fjob-message",
    #     "receiveTimestamp": "2021-12-05T13:03:24.341853669Z"
    # }

    test_data = base64.b64encode(json.dumps(event).encode('utf-8'))
    print(json.dumps(event).encode('utf-8'))
    on_pub_sub_event({'data': test_data}, None)
