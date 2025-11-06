variable "historical_cutoff_date" {
  description = "The cutoff date for historical data extraction"
  type        = string
  default     = "2025-10-25 23:58:00"
}

variable "db_host" {
  type = string
}

variable "db_port" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_user" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true  # This prevents the value from showing in logs
}

variable "report_sender_email" {
  description = "Email address to send daily reports from"
  type        = string
  default     = "sl-coaches@proton.me"
}

variable "report_recipient_email" {
  description = "Email address to receive daily reports"
  type        = string
  default     = "trainee.mohammad.muarij@sigmalabs.co.uk"
}