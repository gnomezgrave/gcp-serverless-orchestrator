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
    event = {"resource": {"type": "start"}}

    test_data = base64.b64encode(json.dumps(event).encode('utf-8'))
    on_pub_sub_event({'data': test_data}, None)
