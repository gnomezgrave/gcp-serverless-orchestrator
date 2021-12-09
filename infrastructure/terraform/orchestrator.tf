resource "google_storage_bucket" "orchestrator_status_bucket" {
  name        = join("-", concat(["orchestrator-status", var.environment, terraform.workspace]))
  provider    = google
  location    = var.region

  force_destroy = true
}

data "archive_file" "orchestrator_file" {
  type        = "zip"
  output_path = "${path.module}/.files/orchestrator_file.zip"
  source {
    content  = file("${path.module}/../../code/src/main.py")
    filename = "main.py"
  }
  source {
    content  = file("${path.module}/../../code/src/requirements.txt")
    filename = "requirements.txt"
  }
  source {
    content  = file("${path.module}/../../code/src/__init__.py")
    filename = "__init__.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestrator/__init__.py")
    filename = "orchestrator/__init__.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestrator/dag.py")
    filename = "orchestrator/dag.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestration_dag_definition.py")
    filename = "orchestration_dag_definition.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestrator/nodes.py")
    filename = "orchestrator/nodes.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestrator/node_factory.py")
    filename = "orchestrator/node_factory.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestrator/events.py")
    filename = "orchestrator/events.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestrator/dag_builder.py")
    filename = "orchestrator/dag_builder.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestrator/enums.py")
    filename = "orchestrator/enums.py"
  }
  source {
    content  = file("${path.module}/../../code/src/orchestrator/status.py")
    filename = "orchestrator/status.py"
  }
}

resource "google_storage_bucket_object" "orchestrator_zip" {
  # To ensure the Cloud Function gets redeployed when the zip file is updated.
  name   =  format("%s#%s", "orchestrator.zip", data.archive_file.orchestrator_file.output_md5)
  bucket = google_storage_bucket.cloudfunctions_bucket.name
  source = "${path.module}/.files/orchestrator_file.zip"
}


# IAM entry for all users to invoke the function
resource "google_cloudfunctions_function_iam_binding" "orchestrator_invoker" {
  cloud_function = google_cloudfunctions_function.orchestrator_function.name
  region = "europe-west1"
  role   = "roles/cloudfunctions.invoker"
  members = ["serviceAccount:sa-gcp-orchestrator@trv-hs-src-consolidation-test.iam.gserviceaccount.com"]
}

resource "google_cloudfunctions_function" "orchestrator_function" {
  name                  = join("-", concat(["orchestrator", var.environment, terraform.workspace]))
  description           = "Orchestrates the GCS services"
  region                = "europe-west1"
  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.cloudfunctions_bucket.name
  source_archive_object = google_storage_bucket_object.orchestrator_zip.name
  timeout               = 60
  entry_point           = "on_pub_sub_event"
  runtime               = "python37"
  event_trigger {
    event_type         = "google.pubsub.topic.publish"
    resource           = google_pubsub_topic.orchestrator_dataflow_events.name
  }
  environment_variables = {
    ENV = var.environment
    OWNER = terraform.workspace
    STATUS_BUCKET = google_storage_bucket.orchestrator_status_bucket.name
  }

  depends_on = [google_storage_bucket_object.orchestrator_zip]
}
