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
                    "region": "europe-west1",
                    "next": "Step1"
                },
                "Step1": {
                    "type": "Task",
                    "target_type": "CloudFunction",
                    "target_name": "orch-test-2",
                    "function": trigger_step_1,
                    "project_id": "trv-hs-src-consolidation-test",
                    "region": "europe-west1",
                    "next": "Step2"
                },
                "Step2": {
                    "type": "Task",
                    "target_type": "CloudFunction",
                    "target_name": "orch-test-3",
                    "project_id": "trv-hs-src-consolidation-test",
                    "region": "europe-west1",
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
                                    "target_type": "CloudFunction",
                                    "target_name": "orch-test-4",
                                    "project_id": "trv-hs-src-consolidation-test",
                                    "region": "europe-west1",
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
                                    "target_type": "CloudFunction",
                                    "target_name": "orch-test-5",
                                    "function": stop,
                                    "project_id": "trv-hs-src-consolidation-test",
                                    "region": "europe-west1",
                                    "end": True
                                }
                            }
                        }
                    ],
                    "next": "Int"
                },
                "Int": {
                    "type": "Task",
                    "target_type": "CloudFunction",
                    "target_name": "orch-test-6",
                    "function": stop,
                    "project_id": "trv-hs-src-consolidation-test",
                    "region": "europe-west1",
                    "next": "End"
                },
                "End": {
                    "type": "Task",
                    "target_type": "CloudFunction",
                    "target_name": "orch-test-7",
                    "function": stop,
                    "project_id": "trv-hs-src-consolidation-test",
                    "region": "europe-west1",
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
