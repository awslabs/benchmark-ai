resource "tls_private_key" "bastion_private_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "bastion_key" {
  key_name   = "bastion_key"
  public_key = "${tls_private_key.bastion_private_key.public_key_openssh}"
}

resource "local_file" "bastion_privatekey_pem" {
  sensitive_content  = "${tls_private_key.bastion_private_key.private_key_pem}"
  filename = "${var.data_dir}/bastion_private.pem"
  provisioner "local-exec" {
    # HACK while Terraform does not have a proper way to set file permissions: https://github.com/terraform-providers/terraform-provider-local/issues/19
    command = "chmod 400 ${local_file.bastion_privatekey_pem.filename}"
  }
}

resource "aws_security_group" "ssh-access-rules" {
  name        = "ssh-access-rules"
  description = "ssh-access-rules"
  vpc_id      = "${module.vpc.vpc_id}"

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    prefix_list_ids = "${var.prefix_list_ids}"
  }

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    cidr_blocks =   "${var.ssh_access_cidr_blocks}"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags {
    "Name" = "ssh-access-rules"
  }
}

resource "aws_security_group" "loopback" {
  name        = "loopback communication"
  description = "loopback communication"
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
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags {
    "Name" = "loopback communication"
  }
}

data "aws_ami" "amazon-linux-2" {
  most_recent = true

  filter {
    name   = "owner-alias"
    values = ["amazon"]
  }

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm*"]
  }
}

resource "aws_instance" "bastion" {
  ami                         = "${data.aws_ami.amazon-linux-2.id}"
  availability_zone           = "${data.aws_availability_zones.available.names[0]}"
  instance_type               = "t2.micro"
  subnet_id                   = "${module.vpc.public_subnets[0]}"
  vpc_security_group_ids      = ["${module.eks.worker_security_group_id}", "${aws_security_group.loopback.id}", "${aws_security_group.ssh-access-rules.id}"]
  associate_public_ip_address = true

  key_name = "${aws_key_pair.bastion_key.key_name}"

  tags {
    "Name" = "BenchmarkAI Bastion"
  }
}
