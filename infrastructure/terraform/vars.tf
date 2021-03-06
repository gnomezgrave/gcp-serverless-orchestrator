variable "project" {
  description = "The id of the gcp project"
  default     = "trv-hs-src-consolidation-test"
}

variable "region" {
  description = "The region of the gcp project"
  default     = "europe-west4"
}

variable "cf_region" {
  description = "The region for Cloud Functions"
  default     = "europe-west1"
}

variable "environment" {
  description = "The name of the environment"
  default     = "edge"
}

