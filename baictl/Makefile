ENV_NAME = baictl
PROJECT = baictl

include ../etc/base-common.mk
include ../etc/python-common.mk

_venv:
	# Override to avoid looking at the other `environment.yml` files (lint-environment.yml, deploy-environment.yml)
	# because there is only an `environment.yml`. There is no need for the other environments at the moment.
	conda env update --file environment.yml --prune --name $(ENV_NAME)

check-parameter-region:
ifndef AWS_REGION
	$(error AWS_REGION parameter is required)
endif

check-parameter-prefix-list-id:
ifndef AWS_PREFIX_LIST_ID
	$(error AWS_PREFIX_LIST_ID parameter is required)
endif

create-infra: check-parameter-region check-parameter-prefix-list-id venv

create-infra: check-parameter-region check-parameter-prefix-list-id venv _create-infra
_create-infra:
	./baictl create infra --aws-region=$(AWS_REGION) --aws-prefix-list-id=$(AWS_PREFIX_LIST_ID) --aws-ssh-access-cidr-blocks=$(EXTRA_CIDR_BLOCK) --extra-users=$(EXTRA_USERS) --extra-roles=$(EXTRA_ROLES) --cidr-blocks=$(WHITE_LISTED_CIDR_BLOCKS)

destroy-infra: check-parameter-region venv _destroy-infra
_destroy-infra:
	./baictl destroy infra --aws-region=$(AWS_REGION)

sync-infra: check-parameter-region venv _sync-infra
_sync-infra:
	./baictl sync infra --aws-region=$(AWS_REGION) --mode=pull

publish:
	echo "Nothing to publish"

default:
	echo "Targets available: "
	echo "	- create-infra AWS_REGION AWS_PREFIX_LIST_ID"
	echo "		Creates the Anubis infrastructure"
	echo ""
	echo "	- destroy-infra AWS_REGION AWS_PREFIX_LIST_ID"
	echo "		Destroys the Anubis infrastructure"
