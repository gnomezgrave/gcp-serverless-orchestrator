import os
import json
import base64
import logging

from orchestrator import DAGExecutor

from orchestration_dag_definition import OrchestrationDagDefinition

logging.getLogger().setLevel(logging.DEBUG)


def on_pub_sub_event(pub_sub_event, context):
    """Triggered by a cloud scheduler daily. Triggers a Dataflow job to process image data.
    Args:
        pub_sub_event: Event from the trigger
        context (google.cloud.functions.Context): Metadata for the event.
    """

    data = base64.b64decode(pub_sub_event['data']).decode('utf-8')
    print(f"JSON data: {data}")
    data = json.loads(data)

    status_bucket_name = os.environ.get('STATUS_BUCKET', 'orchestration-status-bucket-edge-default')
    DAGExecutor(dag_definition=OrchestrationDagDefinition.get_dag(), bucket_name=status_bucket_name).execute(data=data)


if __name__ == '__main__':
    event = {"insertId": "1odawzb7j",
             "labels": {"dataflow.googleapis.com/job_id": "2021-12-12_03_32_45-10348224896447605834",
                        "dataflow.googleapis.com/job_name": "word-count-3",
                        "dataflow.googleapis.com/log_type": "system", "dataflow.googleapis.com/region": "europe-west4"},
             "logName": "projects/trv-hs-src-consolidation-test/logs/dataflow.googleapis.com%2Fjob-message",
             "receiveTimestamp": "2021-12-12T11:41:52.387409036Z", "resource": {
            "labels": {"job_id": "2021-12-12_03_32_45-10348224896447605834", "job_name": "word-count-3",
                       "project_id": "823514981911", "region": "europe-west4", "step_id": ""}, "type": "dataflow_step"},
             "severity": "INFO", "textPayload": "Worker pool stopped.", "timestamp": "2021-12-12T11:41:52.075418368Z"}

    test_data = base64.b64encode(json.dumps(event).encode('utf-8'))
    on_pub_sub_event({'data': test_data}, None)
