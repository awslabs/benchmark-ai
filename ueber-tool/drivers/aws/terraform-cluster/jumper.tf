provider "tls" {
  version = ">= 1.2.0"
}

resource "tls_private_key" "jumper_private_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "jumper_key" {
  key_name   = "jumper_key"
  public_key = "${tls_private_key.jumper_private_key.public_key_openssh}"

  
}

resource "local_file" "jumper_privatekey_pem" {
    content = "${tls_private_key.jumper_private_key.private_key_pem}"
    filename="jumper_private.pem"
}

resource "aws_security_group" "users-amazon-ssh" {
    name        = "users-amazon-ssh"
    description = "users-amazon-ssh"
    vpc_id      = "${module.vpc.vpc_id}"

    ingress {
        from_port       = 22
        to_port         = 22
        protocol        = "tcp"
        prefix_list_ids = ["pl-01a74268"]
    }


    egress {
        from_port       = 0
        to_port         = 0
        protocol        = "-1"
        cidr_blocks     = ["0.0.0.0/0"]
    }

    tags {
        "Name" = "users-amazon-ssh"
    }
}

resource "aws_security_group" "recursive" {
    name        = "recursive communication"
    description = "recursive communication"
    vpc_id      = "${module.vpc.vpc_id}"

    ingress {
        from_port       = 0
        to_port         = 65535
        protocol        = "tcp"
        security_groups = []
        self            = true
    }

    ingress {
        from_port       = 0
        to_port         = 65535
        protocol        = "udp"
        security_groups = []
        self            = true
    }


    egress {
        from_port       = 0
        to_port         = 0
        protocol        = "-1"
        cidr_blocks     = ["0.0.0.0/0"]
    }

    tags {
        "Name" = "recursive communication"
    }
}


resource "aws_instance" "jumper" {
    ami                         = "ami-00035f41c82244dab"
    availability_zone           = "${data.aws_availability_zones.available.names[0]}"
    instance_type               = "t2.micro"
    key_name                    = "stsukrov_jumper"
    subnet_id                   = "${module.vpc.public_subnets[0]}"
    vpc_security_group_ids      = ["${module.eks.worker_security_group_id}", "${aws_security_group.recursive.id}", "${aws_security_group.users-amazon-ssh.id}"]
    associate_public_ip_address = true

    key_name = "${aws_key_pair.jumper_key.key_name}"
    
    tags {
        "Name" = "EC2 jumper to access ES"
    }
}

