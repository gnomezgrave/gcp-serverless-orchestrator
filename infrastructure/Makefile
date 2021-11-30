.DEFAULT_GOAL := help
# PROJECT sets the GCP project which is used
PROJECT=trv-hs-src-consolidation-test

# PROJECT_NUMBER get the uniqe integer for your project
PROJECT_NUMBER=$(shell gcloud projects list --filter="$(PROJECT)" --format="value(PROJECT_NUMBER)")

# CLOUDSDK_CORE_PROJECT tell gcloud sdk which project is in scope
CLOUDSDK_CORE_PROJECT=$(PROJECT)

TF_VERSION="0.13.3"

terraform-cli: ## run a terraform-cli container interactively (shell)
	docker run --rm --interactive --tty \
		--hostname terraform-cli \
		--volume $(PWD)/../:/orchestrator \
		--volume $(GOOGLE_APPLICATION_CREDENTIALS):$(GOOGLE_APPLICATION_CREDENTIALS) \
		--env GOOGLE_APPLICATION_CREDENTIALS \
		--workdir /orchestrator/infrastructure/terraform/ \
		--entrypoint sh \
		hashicorp/terraform:$(TF_VERSION)
.PHONY: terraform-cli