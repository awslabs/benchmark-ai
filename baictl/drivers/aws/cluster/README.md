These are just notes for mabreu@ - ignore them for now.


brew install kubernetes-cli

# To fix https://docs.aws.amazon.com/eks/latest/userguide/install-aws-iam-authenticator.html
curl -o aws-iam-authenticator https://amazon-eks.s3-us-west-2.amazonaws.com/1.11.5/2018-12-06/bin/darwin/amd64/aws-iam-authenticator && chmod +x ./aws-iam-authenticator && cp ./aws-iam-authenticator $HOME/bin/aws-iam-authenticator && export PATH=$HOME/bin:$PATH && echo 'export PATH=$HOME/bin:$PATH' >> ~/.bash_profile

kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v1.10.1/src/deploy/recommended/kubernetes-dashboard.yaml






-------------
export  KUBECONFIG=/Users/mabreu/git_projects/ci-infrastructure/terraform-kubernetes/kubeconfig_test-eks
aws-iam-authenticator token -i test-eks
