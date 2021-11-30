import os
import time
import traceback

from .enums import NodeTypes, TargetTypes, DataflowTemplateType, TaskStatus


class Node:
    def __init__(self, node_name, *args, **kwargs):
        self._node_name = node_name
        self._next = None
        self._is_end = False
        self._node_type = None

    @property
    def node_name(self):
        return self._node_name

    @property
    def node_type(self):
        return self._node_type

    @property
    def next(self):
        return self._next

    @property
    def is_end(self):
        return self._is_end

    def set_next(self, next_node):
        self._next = next_node

    def set_as_end(self):
        self._is_end = True

    def execute(self):
        print("Not implemented yet!")
        return None


class Task(Node):
    def __init__(self, node_name: str, target_name: str, parameters: dict = None, function=None, **kwargs):
        super(Task, self).__init__(node_name)
        self._node_type = NodeTypes.TASK
        self._target_name = target_name
        self._parameters = parameters
        self._function = function
        self._target_type = None
        self._status = TaskStatus.NEW

    @property
    def target_name(self):
        return self._target_name

    @property
    def function(self):
        return self._function

    @property
    def parameters(self):
        return self._parameters

    @property
    def target_type(self):
        return self._target_type

    @property
    def status(self):
        return self._status

    def set_status(self, status: TaskStatus):
        self._status = status


class Function(Task):
    def __init__(self, *args, **kwargs):
        super(Function, self).__init__(*args, **kwargs)
        self._target_type = TargetTypes.FUNCTION


class CloudFunctionTask(Task):
    def __init__(self, *args, **kwargs):
        import os
        super(CloudFunctionTask, self).__init__(*args, **kwargs)
        self._target_type = TargetTypes.CLOUD_FUNCTION
        print(kwargs)
        self._gcp_project = kwargs.get('project_id', os.getenv('GCP_PROJECT'))
        self._url = f"https://europe-west1-{self._gcp_project}.cloudfunctions.net/{self.target_name}"

    def execute(self):
        import requests
        headers = self._authenticate()
        try:
            response = requests.request("POST", self._url, json={"test": "hello"}, headers=headers)

            print(response.json(), response.headers)

            execution = {
                'execution_id': response.headers['Function-Execution-Id'],
                'task_name': self.target_name,
                'node_name': self.node_name,
                'succeeded': True,
                'response': response.text
            }
            self.set_status(TaskStatus.COMPLETED)

        except Exception as e:
            traceback.print_exc()
            execution = {
                'task_name': self.target_name,
                'node_name': self.node_name,
                'succeeded': False,
                'response': str(e).replace('"', "'")
            }
            self.set_status(TaskStatus.FAILED)

        return [(execution, self)]

    def _authenticate(self):
        import requests
        env = os.getenv('ENTRY_POINT')

        if env:
            # We're running on cloud
            metadata_server_url = \
                'http://metadata/computeMetadata/v1/instance/service-accounts/default/identity?audience='
            token_full_url = metadata_server_url + self._url
            token_headers = {'Metadata-Flavor': 'Google'}
            token_response = requests.get(token_full_url, headers=token_headers)
            jwt = token_response.text
            return {
                'Content-type': "application/json",
                'Authorization': f"Bearer {jwt}",
            }

        else:
            # Running locally (most probably)
            import subprocess
            result = subprocess.run(['gcloud', 'auth', 'print-identity-token'], capture_output=True)
            token = result.stdout.decode('utf-8').strip()
            return {
                'Content-type': "application/json",
                'Authorization': f"Bearer {token}",
            }


class DataflowJob(Task):
    def __init__(self, *args, **kwargs):
        import os
        super(DataflowJob, self).__init__(*args, **kwargs)
        self._target_type = TargetTypes.DATAFLOW_JOB

        if 'container_gcs_path' in kwargs:
            self._template_path = kwargs['container_gcs_path']
            self._template_type = DataflowTemplateType.FLEX
        elif 'template_path' in kwargs:
            self._template_path = kwargs['template_path']
            self._template_type = DataflowTemplateType.CLASSIC

        self._dataflow_region = kwargs.get('region', os.getenv('FUNCTION_REGION'))
        self._gcp_project = kwargs.get('project_id', os.getenv('GCP_PROJECT'))
        self._job_type = kwargs.get('job_type', 'Flex')

    def execute(self):
        from googleapiclient.discovery import build
        from oauth2client.client import GoogleCredentials

        credentials = GoogleCredentials.get_application_default()
        # cache_discovery should be set to False to avoid errors
        dataflow = build('dataflow', 'v1b3', credentials=credentials, cache_discovery=False)
        # TODO: Create subclasses for this.
        if self._template_type == DataflowTemplateType.FLEX:

            request = dataflow.projects().locations().flexTemplates().launch(
                projectId=self._gcp_project,
                location=self._dataflow_region,
                body={
                    'launch_parameter': {
                        'jobName': self._target_name,
                        'parameters': self._parameters,
                        'environment': {
                            'additionalUserLabels': {
                                'name': 'flex_templates_example'
                            }
                        },
                        'containerSpecGcsPath': self._template_path,
                    }
                }
            )
            try:
                response = request.execute()
                print(response)
                execution = {
                    'execution_id': response['job']['id'],
                    'task_name': self.target_name,
                    'node_name': self.node_name,
                    'succeeded': True,
                    'response': response
                }
                self.set_status(TaskStatus.COMPLETED)
            except Exception as e:
                print(f"Exception occurred in executing Task: {self.node_name} --> {e}")
                traceback.print_exc()
                execution = {
                    'execution_id': f"dataflow_{time.time()}",
                    'task_name': self.target_name,
                    'node_name': self.node_name,
                    'succeeded': False,
                    'response': str(e).replace('"', "'")
                }
                self.set_status(TaskStatus.FAILED)
            return [(execution, self)]

        elif self._template_type == DataflowTemplateType.CLASSIC:
            request = dataflow.projects().templates().launch(
                projectId=self._gcp_project,
                gcsPath=self._template_path,
                body={
                    'jobName': self._target_name,
                    'parameters': self._parameters,
                }
            )

            try:
                response = request.execute()
                print(response)
                return True
            except Exception as e:
                print(f"Exception occurred in executing Task: {self.node_name} --> {e}")
                return False


class Parallel(Node):
    def __init__(self, node_name, *args, **kwargs):
        super(Parallel, self).__init__(node_name, *args, **kwargs)
        self._node_type = NodeTypes.PARALLEL
        self._branches = []

    @property
    def branches(self):
        return self._branches

    def add_branch(self, branch_node):
        self._branches.append(branch_node)

    def execute(self):
        print("Starting Parallel")
        executions = []
        for branch in self._branches:
            start = branch.get_start_node()
            execution = start.execute()
            executions += execution

        return executions
