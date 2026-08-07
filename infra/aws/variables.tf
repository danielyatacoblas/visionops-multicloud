variable "region" {
  type        = string
  description = "Region selected after quota and cost preflight."
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment."
  default     = "demo"
}

variable "enable_cloud_resources" {
  type        = bool
  description = "Safety switch. Must be explicitly enabled after reviewing cost and identity."
  default     = false
}

variable "owner" {
  type        = string
  description = "Non-sensitive owner tag."
  default     = "portfolio"
}
