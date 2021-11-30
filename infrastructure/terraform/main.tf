terraform {
  backend "gcs" {
    bucket = "trv-hs-src-consolidation-test-terraform"
    prefix = "edge"
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

provider "google-beta" {
  project = var.project
  region  = var.region
}

