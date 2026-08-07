param([Parameter(Mandatory=$true)][ValidateSet("aws", "gcp", "azure")][string]$Cloud)
$ErrorActionPreference = "Stop"
$folder = "infra/$Cloud"
terraform "-chdir=$folder" init
terraform "-chdir=$folder" fmt -check
terraform "-chdir=$folder" validate
terraform "-chdir=$folder" plan -var-file=environments/demo/terraform.tfvars -out=tfplan
Write-Output "Plan saved. No apply was executed."
