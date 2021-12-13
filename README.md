# GCP Serverless Orchestrator

A serverless framework for orchestrating GCP services in a defined flow. It can only orchestrate Cloud Functions and
Dataflow jobs at the moment, but more services will come in the future.

![Sample](docs/GCP_Orchestrator.png)

## High-level Concept

:pencil: **NOTE:** The concept is thoroughly explained in [my blog article](https://gnomezgrave.com/2020/12/04/how-to-orchestrate-dataflow-jobs-with-cloud-functions/).

This entire orchestration process is based on Cloud Logging service and the logs each service puts at the end of an
execution.

Here is a sample log line pushed to Cloud Logging when a Cloud Function is finished executing.

```json
{
  "insertId": "000000-9ed6ca06-19a5-48cc-9f29-f0605f988982",
  "labels": {
  "execution_id": "grcug3cacqj4"
  },
  "logName": "projects/ppeiris-orchestration-test/logs/cloudfunctions.googleapis.com%2Fcloud-functions",
  "receiveTimestamp": "2021-12-12T15:49:46.962297629Z",
  "resource": {
  "labels": {
  "function_name": "orch-test-1",
  "project_id": "ppeiris-orchestration-test",
  "region": "europe-west1"
  },
  "type": "cloud_function"
  },
  "severity": "DEBUG",
  "textPayload": "Function execution took 426 ms, finished with status code: 200",
  "timestamp": "2021-12-12T15:49:36.384721526Z",
  "trace": "projects/ppeiris-orchestration-test/traces/c4d487678a5270c113bbde284fc35bed"
}
```

These logs are captured by a [Cloud Logs Router](https://cloud.google.com/logging/docs/routing/overview) ([google_logging_project_sink](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/logging_project_sink)) and they're pushed to a Cloud Pub/Sub topic, that triggers the Orchestration function. Then it identifies which job was finished and extracts the next job(s) according to
a defined flow: DAG (Directed Acyclic Graph), and automatically triggers the next. 

### Sample DAG

Here is a sample DAG.

```python
{
  "start": "Init",
  "steps": {
    "Init": {
      "type": "Task",
      "target_type": "CloudFunction",
      "target_name": "orch-test-1",
      "project_id": "ppeiris-orchestration-test",
      "region": "europe-west1",
      "next": "Step1"
    },
    "Step1": {
      "type": "Task",
      "target_type": "CloudFunction",
      "target_name": "orch-test-2",
      "project_id": "ppeiris-orchestration-test",
      "region": "europe-west1",
      "next": "Step2"
    },
    "Step2": {
      "type": "Parallel",
      "branches": [
        {
          "start": "Branch1",
          "steps": {
            "Branch1": {
                "type": "Task",
                "target_type": "Dataflow",
                "target_name": "word-count-demo",
                "parameters": {
                'input': 'gs://dataflow-samples/shakespeare/kinglear.txt',
                'output': 'gs://wordcount_output_ppeiris/output/out',
                'temp_location': 'gs://wordcount_output_ppeiris/temp/output',
                'subnetwork': 'https://www.googleapis.com/compute/v1/projects/shared-vpc-x/regions/europe-west4/subnetworks/my-sub-network',
                'setup_file': '/dataflow/template/setup.py'
              },
              "project_id": "ppeiris-orchestration-test",
              "container_gcs_path": 'gs://my-flex-templates/ppeiris/python_command_spec.json',
              "region": "europe-west4",
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
              "target_name": "orch-test-3",
              "project_id": "ppeiris-orchestration-test",
              "region": "europe-west1",
              "end": True
            }
          }
        }
      ],
      "next": "End"
    },
    "End": {
      "type": "Task",
      "target_type": "CloudFunction",
      "target_name": "orch-test-4",
      "project_id": "ppeiris-orchestration-test",
      "region": "europe-west1",
      "end": True
    },
  }
}
```

Above DAG will create an execution plan as below.

![Sample DAG](docs/Sample_DAG.png)

:pencil: **NOTE:** This is just an illustration to explain the flow, and this component doesn't create such a diagram (at the moment).

According to this orchestration plan:

* It will first trigger the **Init** Cloud Function.
* After it's completed, it will then trigger the Dataflow job defined by **Step1**.
* When it's done, both the Dataflow job and the Cloud Functions respectively defined as **Branch1** and **Branch2** will
  get triggered in parallel.
* Only when both of them are completed, Cloud Function defined as **End** will get triggered.

All the intermediate states are stored as JSON files in Google Cloud Storage, and the orchestration is done using a Cloud Function (hence: "_serverless_"), so the costs are minimum.

## How to use

You need to change two main aspects of this project to make it work for you: code and terraform.

### Code Changes

* You can either directly use this repository, or you can copy the `orchestrator` directory into your source code directory for the Orchestrator Cloud Function.
* In the `main.py` of your Cloud Function, add the below code.

  ```python
  import os
  import json
  import base64
  
  from orchestrator import DAGExecutor
  from orchestration_dag_definition import OrchestrationDagDefinition
  
  def on_pub_sub_event(pub_sub_event, context):
    data = base64.b64decode(pub_sub_event['data']).decode('utf-8')
    data = json.loads(data)
  
    # Make sure this bucket exists and your code has read/write access.
    status_bucket_name = os.environ.get('STATUS_BUCKET', 'orchestration-status-bucket')
  
    # Creates the executor with the storage bucket, and executes it using the log line it received.
    DAGExecutor(dag_definition=OrchestrationDagDefinition.get_dag(), bucket_name=status_bucket_name).execute(data=data)
  ```

  :pencil: **NOTE:**  
  Make sure you have defined all the requirements you need in a `requirements.txt`, including the ones that are defined in `/code/src/requirements.txt`.


It's that simple! The `DAGExecutor` class will handle all the parsing and execution of your jobs for you!

Well, you still need to define a DAG definition as a Python `dict` for your orchestration flow as defined in [OrchestrationDagDefinition](code/src/orchestration_dag_definition.py) or as shown above, along with the complementary functions. 

The syntax for the DAG will be explained in a separate section. 


### Infrastructure

We use `terraform` to define our resources, and they're defined inside the `infrastructure/terraform` directory. 

* You should change the `project` variable inside the [vars.tf](infrastructure/terraform/vars.tf) as the project you're going to deploy this Orchestrator. 

* Then you can use the `make` recipe to use the official terraform Docker image.
  ```shell
  make terraform-cli
  ```

  This will (download the Docker image and) bring you to a new shell that you can use to deploy the infrastructure.

* Following commands will deploy your version of the Orchestrator to your project defined with `project` variable in `infrastructure/terraform/vars.tf`

  ```shell
  terraform init
  terraform apply --auto-approve
  ```

* If you want to deploy multiple versions of this Orchestrator, you can create separate workspaces for them, otherwise the `default` workspace will be used.

  ```shell
  terraform workspace create demo
  ```

:fire: **IMPORTANT:**

Do **NOT** remove the filter for the orchestration Cloud Function in the log sinks!   
It will create an infinite cycle of executions because the Orchestrator will react to its own execution end. Even if you want to explicitly define the Cloud Functions to filter, do NOT remove the filter exemption for the Orchestrator.

![Log Sink for CF](docs/cf_log_sink.png)

Make sure you add this filter explicitly for **ALL** the Log Sinks you create that listens to Cloud Functions.


## Design

Check [this document](code/src/orchestrator/README.md) for more information.

## DAG Definition

In order for us to define the orchestration flow, we should create a JSON to define the DAG. It should have the following structure in the parent level.

### DAG Structure

```json
{
  "start": "Init",
  "steps": {
  "Init": {},
  "Task1": {},
  ...
  }
}
```

Every DAG definition MUST have a `"start"` attribute pointing to a valid Step in the `steps` section.

### Steps

This is a mapping/dict of steps to be executed where the key is an arbitrary name for the step, and the value contains the attributes required to perform the execution.

Regardless of the type of the Step, it should have the below attributes.

* `type`  
  Defines the type of the Task. Should be a value from `NodeTypes` enum (Task, Parallel, End, or Condition).
* `next`  
  Defines the name of the next step to be triggered after the execution of the current Task. This MUST be a valid step name that already present in the steps.
* `end`  
  Declares if this step is the final step of this DAG. If the `next` is not defined, this will automatically be marked as `True`, but not vise versa.

:fire: **IMPORTANT:** Only one of `next` and `end` attributes should be defined for a single step. A step must at least have one of them, but not both of them defined for a single step.

#### Task

For the steps with `type` as Task, there are additional attributes to be defined.

* `target_type`  
  If this step is a Task, this attribute defines the type of the Task. It should be a value from `TargetTypes` enum (Function, Cloud Function, or Dataflow). "Start" is not a valid `target_type` and it's only used for **Events**.
* `target_name`  
  This declared the name of the Task to be triggered. This will be the name of the Cloud Function or the name of the Dataflow job.
* `function` (not used at the moment)  
  This attribute points to a function (function object) that should be triggered when we execute the **Task**.
* `parameters` (optional)  
  Defines the parameters (as a `dict`) that should be passed to the Task when being executed.

**Cloud Functions and Dataflow Jobs**

Cloud Functions and Dataflow jobs require the below additional attributes along with the ones in Tasks. 

* `project_id`  
  Defines the project ID on which the Task should be executed. If not defined, it will use the project where the Orchestrator (this component) is running. If you want to run Tasks on a different project, you must define this!
* `region`  
  Defines the GCP region on which the Task should be executed. If not defined, it will use the region of the Orchestrator. This can cause problems if the given type of the Task is not available in the region. 

**Dataflow Jobs**

For a Dataflow Job, `parameters` attribute MUST present and should contain the below fields that are required to trigger a Dataflow job.

* `temp_location`  
  Defines the temporary location for the Dataflow jobs to use for intermediate results/files.
* `subnetwork`  
  Defines the name (URI) of a subnetwork on where the Dataflow job should be run. Make sure the current project (or the project defined by `project_id`) has permission to spawn workers in this subnet.
 
If the Dataflow job is defined as a Flex template, we should also specify the below attributes.

* `setup_file`  
  Defines the file path for the `setup.py` inside the launcher Docker image. 
* `container_gcs_path`  
  Defines the GCS location of the template spec file that the execution should use.

:pencil: **NOTE:**  If you're not familiar with Flex templates, please read [this article](https://gnomezgrave.com/2020/11/21/dataflow-flex-templates-and-how-to-use-them/).

If the Dataflow job is defined using Classic templates, you should specify the below attribute.

* `template_path`  
  Defines the GCS path for the template metadata file.

#### Parallel

Parallel steps defines the Tasks that should be executed (theoretically) in parallel. The parallel executions are defined as `"branches"` each containing a new DAG and should follow the same syntax as [DAG Structure](#dag-definition).

```json
{
  "type": "Parallel",
  "branches": [
    {
      "start": "Branch1",
      "steps": {
        "Branch1": {},
        "Branch2": {},
        ...
      }
    },
    {
      "start": "Branch2",
      "steps": {
        "Branch3": {},
        "Branch4": {},
        ...
      }
    }
  ],
  "next": "Int"
}
```

Please check the [Sample DAG](#sample-dag) section to see examples for Cloud Function, Dataflow job, and Parallel steps.

### Constraints

There are several constraints we have to remember when defining a DAG. Here is a summarized list.

* Each DAG (both parent and child DAGs) MUST have a `"start"` attribute, and it MUST point to an existing step in the DAG.
* It MUST not have cycles! It means, one Node should be traversed once and ONLY once. So the `"next"` shouldn't point to an already 
* Every Node should have a `type` defined, and it MUST be a valid value from `NodeTypes`. 
* One of `"next"` or `"end"` MUST be defined for each step, but not none or both of them.


## Limitations

This orchestration framework has some known limitations at the moment, and feel free to raise a Pull Request if you'd like to contribute.

### Re-using the same Cloud Function

This uses the `target_name` attribute as the key to extract the name of the Cloud Function to be triggered. We currently don't have another attribute in the log event that we can use to trace back to both the execution and the DAG definition.

This feature should be implemented in order to us to re-use the same Cloud Function in different steps (probably with different `parameters`).

### Dataflow Job failures

The orchestrator doesn't catch when a Dataflow Job is failed in the middle, or even when the Launcher VM fails. We should call the Dataflow API to extract the actual status of the Dataflow job when we receive the log event. We should use the [`projects().locations().get()`](https://cloud.google.com/dataflow/docs/reference/rest/v1b3/projects.locations.jobs) API call to retrieve the final state of the Dataflow Job. And we know by experience that this API call doesn't immediately reflect the last state of the Dataflow job, and we had to wait around 30 seconds for it to return the correct status. We also need to find a proper way of doing this without explicitly waiting in the code.

If the launcher VM failed, it won't push a `"Worker pool stopped"` message, but rather a `"Error occurred in the launcher container: Template launch failed. See console logs."` message. We're not currently reacting the latter.

### Limited Task/Node types

This currently supports only Cloud Functions, Dataflow Jobs, and Parallel steps. Many other Node types should be introduced in the future to make the maximum use out of this orchestrator. 
