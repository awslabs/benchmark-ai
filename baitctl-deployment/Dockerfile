FROM ubuntu:18.04
RUN apt update && apt install -y curl unzip python
RUN curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip" && unzip awscli-bundle.zip && ./awscli-bundle/install -b ~/bin/aws
ENTRYPOINT ["/root/bin/aws", "sts", "get-caller-identity"]
