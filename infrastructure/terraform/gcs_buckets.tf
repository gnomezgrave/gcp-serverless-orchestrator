resource "google_storage_bucket" "cloudfunctions_bucket" {
  name     = join("-", concat(["cloud-functions-bucket", var.environment, terraform.workspace]))
  provider = google
  location = var.region

  force_destroy = true
}

resource "google_storage_bucket" "orchestration_status_bucket" {
  name     = join("-", concat(["orchestration-status-bucket", var.environment, terraform.workspace]))
  provider = google
  location = var.region

}