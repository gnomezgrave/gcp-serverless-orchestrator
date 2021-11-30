import json
from json.decoder import JSONDecodeError

from google.cloud import storage

from .nodes import Task
from .enums import TaskStatus


class Status:
    def __init__(self, bucket_name):
        self._bucket_name = bucket_name
        self._bucket = storage.Client().get_bucket(bucket_name)

    def _read_json_from_gcs(self, file_path):
        blob = self._bucket.get_blob(file_path)
        if not blob:
            return {}
        json_string = blob.download_as_string()
        try:
            json_data = json.loads(json_string)
        except JSONDecodeError as e:
            print("Error in reading status file: ", e)
            return {}
        return json_data

    def _write_json_to_gcs(self, file_path, file_content):
        blob = self._bucket.blob(file_path)
        blob.upload_from_string(json.dumps(file_content))


class ExecutionStatus(Status):
    def __init__(self, bucket_name):
        super(ExecutionStatus, self).__init__(bucket_name)
        self._prefix = 'executions'

    def get_execution(self, execution_id):
        file_path = f"{self._prefix}/{execution_id}.json"
        return self._read_json_from_gcs(file_path)

    def save_execution(self, execution):
        execution_id = execution['execution_id']
        self._write_json_to_gcs(f"{self._prefix}/{execution_id}.json", execution)


class OrchestrationStatus(Status):
    def __init__(self, bucket_name, run_id):
        super(OrchestrationStatus, self).__init__(bucket_name)
        self._prefix = 'runs'
        self._orchestration_status_file = 'orchestration_status.json'
        self._run_id = run_id

        self._status_data = self._read_status_file()

    def _get_status_file_path(self):
        return '/'.join([self._prefix, self._run_id, self._orchestration_status_file])

    def _read_status_file(self):
        return self._read_json_from_gcs(self._get_status_file_path())

    def update_task_status(self, finished_task: Task):
        task = self._status_data.get(finished_task.node_name, {})
        task['status'] = finished_task.status.value
        task['task_name'] = finished_task.target_name

        self._status_data[finished_task.node_name] = task

    def save_orchestration_status(self):
        blob = self._bucket.blob(self._get_status_file_path())
        blob.upload_from_string(json.dumps(self._status_data))

    def load_orchestration_status(self):
        return self._status_data

    def set_orchestration_status(self, last_processed_date):
        last_processed_date = f"{last_processed_date.year}-{last_processed_date.month:02}-{last_processed_date.day:02}"
        blob = self._bucket.get_blob(self._orchestration_status_file)
        json_content = {
            'last_processed_date': last_processed_date,
            'reprocess': "false"
        }
        res = blob.upload_from_string(
            data=json.dumps(json_content),
            content_type='application/json'
        )
