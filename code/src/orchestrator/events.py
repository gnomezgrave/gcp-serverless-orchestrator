import time
from typing import Union
from .enums import TargetTypes, TaskStatus


class Event:

    def __init__(self, **kwargs):
        self._event_data = kwargs['event_data'] if 'event_data' in kwargs else None
        self._task_name = kwargs.get('task_name')
        self._target_type = kwargs.get('target_type')
        self._execution_id = kwargs.get('execution_id')
        self._run_id = kwargs.get('run_id')
        self._status = TaskStatus.NEW

    @property
    def task_name(self):
        return self._task_name

    @property
    def execution_id(self):
        return self._execution_id

    @property
    def run_id(self):
        return self._run_id

    @property
    def target_type(self):
        return self._target_type

    @property
    def status(self):
        return self._status

    def set_run_id(self, run_id):
        self._run_id = run_id

    def set_status(self, status: TaskStatus):
        self._status = status


class Start(Event):
    def __init__(self, **kwargs):
        super(Start, self).__init__(**kwargs)
        self._task_name = 'start'
        self._target_type = TargetTypes.START
        self._run_id = f"run_{int(time.time())}"


class DataflowEvent(Event):
    """
        {
          "textPayload": "Worker pool stopped.",
          "insertId": "1lfy432c42x",
          "resource": {
            "type": "dataflow_step",
            "labels": {
              "region": "europe-west4",
              "project_id": "823514981911",
              "job_name": "my-job-name-1w2",
              "step_id": "",
              "job_id": "2021-11-16_12_18_34-3586925792726812510"
            }
          },
          "timestamp": "2021-11-16T20:27:14.996634424Z",
          "severity": "INFO",
          "labels": {
            "dataflow.googleapis.com/log_type": "system",
            "dataflow.googleapis.com/region": "europe-west4",
            "dataflow.googleapis.com/job_id": "2021-11-16_12_18_34-3586925792726812510",
            "dataflow.googleapis.com/job_name": "my-job-name-1w2"
          },
          "logName": "projects/trv-hs-src-consolidation-test/logs/dataflow.googleapis.com%2Fjob-message",
          "receiveTimestamp": "2021-11-16T20:27:15.490396842Z"
        }
    """

    def __init__(self, **kwargs):
        super(DataflowEvent, self).__init__(**kwargs)
        event_data = self._event_data
        # TODO: Call the Dataflow API and extract the correct status
        self._status = TaskStatus.COMPLETED
        if event_data:
            self._task_name = event_data['resource']['labels']['job_name']
            self._execution_id = event_data['resource']['labels']['job_id']
        self._target_type = TargetTypes.DATAFLOW_JOB
        self._job_type = None


class CloudFunctionEvent(Event):
    """
        {
          "textPayload": "Function execution started",
          "insertId": "000000-610275f2-c2dd-40bc-b8d3-1e80b1906830",
          "resource": {
            "type": "cloud_function",
            "labels": {
              "project_id": "trv-hs-src-consolidation-test",
              "function_name": "orchestrator-edge-default",
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
    """

    def __init__(self, **kwargs):
        super(CloudFunctionEvent, self).__init__(**kwargs)
        event_data = self._event_data
        # TODO: Call the CloudFunctions API and extract the correct status
        self._status = TaskStatus.COMPLETED
        if event_data:
            self._task_name = event_data['resource']['labels']['function_name']
            self._execution_id = event_data['labels']['execution_id']
        self._target_type = TargetTypes.CLOUD_FUNCTION


class EventsFactory:
    @staticmethod
    def create_from_event(event_data: dict) -> Union[Event, None]:
        resource_type = event_data['resource']['type']
        if resource_type == 'dataflow_step':
            return DataflowEvent(event_data=event_data)
        elif resource_type == 'cloud_function':
            return CloudFunctionEvent(event_data=event_data)
        elif resource_type == 'start':
            return Start(event_data=event_data)
        else:
            return None

