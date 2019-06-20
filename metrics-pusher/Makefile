ENV_NAME = metrics-pusher

include ../python-common.mk

PROJECT=metrics-pusher

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt

deploy.yml:
	# A dummy file since metrics-pusher does not need this
	touch deploy.yml

override define fn_k8s_deploy
	echo "Skipping Kubernetes deployment"
endef
