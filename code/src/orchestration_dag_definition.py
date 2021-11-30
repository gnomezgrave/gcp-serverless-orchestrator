class OrchestrationDagDefinition:
    @staticmethod
    def get_dag():
        return {
            "start": "Init",
            "steps": {
                "Init": {
                    "type": "Task",
                    "target_type": "CloudFunction",
                    "target_name": "orch-test-1",
                    "function": start,
                    "project_id": "trv-hs-src-consolidation-test",
                    "next": "Step1"
                },
                "Step1": {
                    "type": "Task",
                    "target_type": "CloudFunction",
                    "target_name": "orch-test-1",
                    "function": trigger_step_1,
                    "project_id": "trv-hs-src-consolidation-test",
                    "next": "Step2"
                },
                "Step2": {
                    "type": "Task",
                    "target_type": "Dataflow",
                    "target_name": "word-count-2",
                    "parameters": {
                        'input': 'gs://dataflow-samples/shakespeare/kinglear.txt',
                        'output': 'gs://wordcount_output_ppeiris/output/out',
                        'temp_location': 'gs://wordcount_output_ppeiris/temp/output',
                        'subnetwork': 'https://www.googleapis.com/compute/v1/projects/shared-vpc-182609/regions/europe-west4/subnetworks/trv-hs-playground-eu-w4',
                        'setup_file': '/dataflow/template/setup.py'
                    },
                    "project_id": "trv-hs-src-consolidation-test",
                    "container_gcs_path": 'gs://flex-templates-ppeiris/ppeiris/python_command_spec.json',
                    "region": "europe-west4",
                    "function": trigger_step_3,
                    "next": "Step3"
                },
                "Step3": {
                    "type": "Parallel",
                    "branches": [
                        {
                            "start": "Branch1",
                            "steps": {
                                "Branch1": {
                                    "type": "Task",
                                    "target_type": "Dataflow",
                                    "target_name": "word-count-3",
                                    "parameters": {
                                        'input': 'gs://dataflow-samples/shakespeare/kinglear.txt',
                                        'output': 'gs://wordcount_output_ppeiris/output/out',
                                        'temp_location': 'gs://wordcount_output_ppeiris/temp/output',
                                        'subnetwork': 'https://www.googleapis.com/compute/v1/projects/shared-vpc-182609/regions/europe-west4/subnetworks/trv-hs-playground-eu-w4',
                                        'setup_file': '/dataflow/template/setup.py'
                                    },
                                    "project_id": "trv-hs-src-consolidation-test",
                                    "container_gcs_path": 'gs://flex-templates-ppeiris/ppeiris/python_command_spec.json',
                                    "region": "europe-west4",
                                    "function": trigger_step_3,
                                    "end": True
                                }
                            }
                        },
                        {
                            "start": "Branch2",
                            "steps": {
                                "Branch2": {
                                    "type": "Task",
                                    "target_type": "Dataflow",
                                    "target_name": "word-count-4",
                                    "parameters": {
                                        'input': 'gs://dataflow-samples/shakespeare/kinglear.txt',
                                        'output': 'gs://wordcount_output_ppeiris/output/out',
                                        'temp_location': 'gs://wordcount_output_ppeiris/temp/output',
                                        'subnetwork': 'https://www.googleapis.com/compute/v1/projects/shared-vpc-182609/regions/europe-west4/subnetworks/trv-hs-playground-eu-w4',
                                        'setup_file': '/dataflow/template/setup.py'
                                    },
                                    "project_id": "trv-hs-src-consolidation-test",
                                    "container_gcs_path": 'gs://flex-templates-ppeiris/ppeiris/python_command_spec.json',
                                    "region": "europe-west4",
                                    "function": trigger_step_3,
                                    "end": True
                                }
                            }
                        }
                    ],
                    "next": "End"
                },
                "End": {
                    "type": "Task",
                    "target_type": "Function",
                    "target_name": "end",
                    "function": stop,
                    "project_id": "trv-hs-src-consolidation-test",
                    "end": True
                },
            }
        }


def start():
    pass


def trigger_step_1():
    pass


def trigger_branch_1():
    pass


def trigger_branch_2():
    pass


def trigger_step_3():
    pass


def stop():
    pass
