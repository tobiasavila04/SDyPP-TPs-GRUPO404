terraform {
  required_version = ">= 1.3.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "sdypp-terraform-state-bucket" # Cambiar por el nombre del bucket GCS real
    prefix = "terraform/state/hit2"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}
