<#
.SYNOPSIS
StartLocalContainer.ps1 - Run the webapp on a Docker container locally

.DESCRIPTION 
This PowerShell script will build a Docker image with the app and run it.

.EXAMPLE
.\StartLocalContainer.ps1

.NOTES
Change Log
V1.00, 03/06/2023 - Initial version
#>

$default_super_password="My sup3r p4ssw0rd!"
$current_user=Get-LocalUser -Name $Env:UserName
$first_name = $current_user.FullName.split(' ', 2)[0]
$last_name = $current_user.FullName.split(' ', 2)[1]
$docker_path=(Get-Command docker).Path

Start-Process -FilePath $docker_path -NoNewWindow -Wait -ArgumentList "build",`
"--build-arg","DJANGO_SUPERUSER_LOGIN=$Env:UserName",`
"--build-arg","DJANGO_SUPERUSER_FIRSTNAME=$first_name",`
"--build-arg","DJANGO_SUPERUSER_LASTNAME=$last_name",`
"--build-arg","DJANGO_SUPERUSER_EMAIL=$Env:UserName@invalid.local",`
"--build-arg","DJANGO_SUPERUSER_PASSWORD=`"$default_super_password`"",`
"--tag","django-okta-client:latest","."
Start-Process -FilePath $docker_path -NoNewWindow -Wait -ArgumentList "run","--name","django_okta_client_test",`
"-e","DJANGO_DEBUG=true",`
"-e","OKTA_METADATA",`
"-e","PORT=8080",`
"-p","127.0.0.1:8080:8080","-d","--rm","django-okta-client:latest"
Start-Process -FilePath $docker_path -NoNewWindow -Wait -ArgumentList "logs","-f","django_okta_client_test"
