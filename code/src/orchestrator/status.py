import json
from json.decoder import JSONDecodeError

from .nodes import Task


class Status:
    def __init__(self, bucket):
        self._bucket = bucket

    def _read_json_from_gcs(self, file_path):
        # with open(file_path) as file:
        #     json_string = file.read()
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
        if not blob or not blob.exists():
            print("Error in saving status file.")


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
    def __init__(self, bucket_name, run_id=None):
        super(OrchestrationStatus, self).__init__(bucket_name)
        self._prefix = 'runs'
        self._orchestration_status_file = 'orchestration_status.json'
        self._run_id = run_id
        self._status_data = None
        self.set_run_id(run_id)

    def set_initial_status(self, status_data):
        self._status_data = status_data

    @property
    def run_id(self):
        return self._run_id

    def set_run_id(self, run_id):
        self._run_id = run_id
        if run_id:
            self._status_data = self._read_status_file()

    def _get_status_file_path(self):
        return '/'.join([self._prefix, self._run_id, self._orchestration_status_file])

    def _read_status_file(self):
        return self._read_json_from_gcs(self._get_status_file_path())

    def update_task_status(self, finished_task: Task):
        task = self._status_data.get(finished_task.node_name, {})
        task = {**task, **finished_task.to_json()}
        self._status_data[finished_task.node_name] = task

    def get_task_status(self, node_name):
        return self._status_data.get(node_name)

    def save_orchestration_status(self):
        blob = self._bucket.blob(self._get_status_file_path())
        blob.upload_from_string(json.dumps(self._status_data))

    def load_orchestration_status(self):
        return self._status_data
