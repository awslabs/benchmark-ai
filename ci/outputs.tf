# HACK: These two are for anubis-driver.py  
output "blackbox_vpc_default_group_id" {
  value = aws_default_security_group.default.id
}
output "blackbox_public_group_id" {
  value = aws_security_group.blackbox_public.id
}
