resource "google_pubsub_topic" "orchestrator_dataflow_events" {
  name = join("-", concat(["orchestrator-dataflow-events", var.environment, terraform.workspace]))
}

resource "google_logging_project_sink" "dataflow_job_completion_sink" {
  unique_writer_identity = true
  name = join("-", concat(["dataflow-job-completion-sink", var.environment, terraform.workspace]))
  destination = "pubsub.googleapis.com/projects/${var.project}/topics/${google_pubsub_topic.orchestrator_dataflow_events.name}"
  filter = "resource.type=dataflow_step AND (textPayload=\"Worker pool stopped.\" OR \"Error occurred in the launcher container: Template launch failed. See console logs.\")"
}

resource "google_logging_project_sink" "cloud_function_completion_sink" {
  unique_writer_identity = true
  name = join("-", concat(["cloud-function-completion-sink", var.environment, terraform.workspace]))
  destination = "pubsub.googleapis.com/projects/${var.project}/topics/${google_pubsub_topic.orchestrator_dataflow_events.name}"
  filter = "resource.type=\"cloud_function\" NOT resource.labels.function_name=${google_cloudfunctions_function.orchestrator_function.name}  textPayload: \"Function execution took\" "
}