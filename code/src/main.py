import os
import json
import base64
import logging

from orchestrator import DAG, DAGBuilder, OrchestrationStatus, ExecutionStatus
from orchestrator import Event, DataflowEvent, CloudFunctionEvent, EventsFactory
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
    data = json.loads(data)

    status_bucket_name = os.environ.get('STATUS_BUCKET', 'orchestration-status-bucket-edge-default')

    task = EventsFactory.create_from_event(event_data=data)

    dag_definition = OrchestrationDagDefinition.get_dag()
    dag = DAGBuilder(dag=dag_definition).build_dag()
    all_tasks = dag.get_all_tasks()
    exec_status = ExecutionStatus(status_bucket_name)

    if task.target_type == TargetTypes.START:
        node = dag.get_start_node()
        run_id = task.run_id
    else:
        execution = exec_status.get_execution(task.execution_id)
        print("Task", task.run_id, task.execution_id)
        print("Execution", execution)

        run_id = execution['run_id']
        node = all_tasks.get(task.task_name).next

    print(node.node_name)
    executions = node.execute()

    if not executions:
        print("Something went wrong!")
        return

    orchestration_status = OrchestrationStatus(bucket_name=status_bucket_name, run_id=run_id)

    for execution in executions:
        exec_status.save_execution(execution[0])
        node = execution[1]
        if node.node_type == NodeTypes.TASK:
            orchestration_status.update_task_status(node)

    print(task.task_name)

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

    event = {
        "resource": {
            "type": "start",
        }
    }

    event = {
        "textPayload": "Function execution took 5 ms, finished with status code: 200",
        "insertId": "000000-a8c36fc4-754c-4244-b57e-8c2f64990ed6",
        "resource": {
            "type": "cloud_function",
            "labels": {
                "project_id": "trv-hs-src-consolidation-test",
                "region": "europe-west1",
                "function_name": "orch-test-1"
            }
        },
        "timestamp": "2021-11-29T20:18:35.496750640Z",
        "severity": "DEBUG",
        "labels": {
            "execution_id": "an76uyawgxow"
        },
        "logName": "projects/trv-hs-src-consolidation-test/logs/cloudfunctions.googleapis.com%2Fcloud-functions",
        "trace": "projects/trv-hs-src-consolidation-test/traces/142fa8e3bb8056e7ecc6ff52e4bbb4af",
        "receiveTimestamp": "2021-11-29T20:18:45.663684339Z"
    }

    event = {
        "textPayload": "Worker pool stopped.",
        "insertId": "qx3hwqc1rr",
        "resource": {
            "type": "dataflow_step",
            "labels": {
                "job_id": "2021-11-29_12_36_11-10607817986534386915",
                "region": "europe-west4",
                "job_name": "word-count-2",
                "project_id": "823514981911",
                "step_id": ""
            }
        },
        "timestamp": "2021-11-29T20:33:19.545054946Z",
        "severity": "INFO",
        "labels": {
            "dataflow.googleapis.com/job_name": "word-count-2",
            "dataflow.googleapis.com/region": "europe-west4",
            "dataflow.googleapis.com/job_id": "2021-11-29_12_23_53-13791387142391100791",
            "dataflow.googleapis.com/log_type": "system"
        },
        "logName": "projects/trv-hs-src-consolidation-test/logs/dataflow.googleapis.com%2Fjob-message",
        "receiveTimestamp": "2021-11-29T20:33:20.765324918Z"
    }

    test_data = base64.b64encode(json.dumps(event).encode('utf-8'))
    on_pub_sub_event({'data': test_data}, None)
