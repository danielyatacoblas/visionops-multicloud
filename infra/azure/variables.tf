variable "region" {
  type        = string
  description = "Region selected after quota and cost preflight."
  default     = "eastus"
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

variable "subscription_id" {
  type        = string
  description = "Azure subscription id. Required only for a real cloud plan."
  default     = "00000000-0000-0000-0000-000000000000"
}
