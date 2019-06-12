#!/bin/bash
nohup /usr/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2&
timeout 15 bash -c "until docker info; do echo .; sleep 1; done"
