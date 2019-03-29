This document contains some tips on how to operate the Benchmark AI system.

# SSH

The terraform modules will create a very handy file named `ssh-config` at the `bai` directory:

```
# SSH into bastion
ssh -F bai/ssh-config bastion

# SSH into an EKS worker
ssh -F bai/ssh-config <IP of worker | DNS of worker>
```

# Tunnel for Elasticsearch + Kibana

```
ssh -F bai/ssh-config estunnel -N
```

Now you can access Kibana by visiting: https://localhost:9200/_plugin/kibana


# Inside an EKS worker

After SSHing into the EKS instance you are interested in:

## Kubelet logs

```
sudo journalctl -u kubelet
```