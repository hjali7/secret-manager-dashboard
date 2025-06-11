variable "namespace" {
  description = "The namespace to deploy database resources into."
  type        = string
}

variable "db_user" {
  description = "The username for the PostgreSQL database."
  type        = string
  sensitive   = true 
}
variable "db_password" {
  description = "The password for the PostgreSQL database."
  type        = string
  sensitive   = true 
}

variable "db_name" {
  description = "The name of the PostgreSQL database."
  type        = string
}