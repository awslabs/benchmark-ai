# Elasticsearch Tunnel
Host estunnel
    Hostname ${bastion_public_ip}
    User ubuntu
    IdentitiesOnly yes
    IdentityFile ${bastion_private_key_filename}
    LocalForward 9200 ${es_endpoint}:443

Host bastion
    Hostname ${bastion_public_ip}
    User ubuntu
    IdentitiesOnly yes
    IdentityFile ${bastion_private_key_filename}

Host ${host_wildcard} ip-*.ec2.internal
    User ec2-user
    IdentitiesOnly yes
    IdentityFile ${worker_private_key_filename}
    ProxyCommand ssh -W %h:%p -i ${bastion_private_key_filename} ubuntu@${bastion_public_ip}