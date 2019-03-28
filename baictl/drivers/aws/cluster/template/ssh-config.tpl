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
