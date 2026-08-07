param([Parameter(Mandatory=$true)][ValidateSet("aws", "gcp", "azure")][string]$Cloud)
$ErrorActionPreference = "Stop"
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) { throw "Terraform is not installed." }
terraform version
Write-Output "Cloud: $Cloud"
Write-Output "SAFE MODE: this script does not authenticate, deploy or change cloud state."
Write-Output "PENDING: identity, account, quota, region, budget and remote state validation."
