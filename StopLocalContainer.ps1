<#
.SYNOPSIS
StopLocalContainer.ps1 - Stops the webapp on a Docker container running locally

.DESCRIPTION 
This PowerShell script will simply stop the container started by StartLocalContainer.ps1

.EXAMPLE
.\StopLocalContainer.ps1

.NOTES
Change Log
V1.00, 03/06/2023 - Initial version
#>

$docker_path=(Get-Command docker).Path
Start-Process -FilePath $docker_path -NoNewWindow -Wait -ArgumentList "stop","django_okta_client_test"
