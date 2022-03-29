# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Import-Module Microsoft.Powershell.LocalAccounts

#Create local administrator for remote WinRM
Write-Host "Obtaining local administrator credentials from Secrets Manager."
$secret_response = Get-SECSecretValue -SecretId "as2/builder/pw" -ProfileName appstream_machine_role
$secret = $secret_response.SecretString | ConvertFrom-Json

$username = $secret.as2_builder_admin_user
$password = $secret.as2_builder_admin_pw | ConvertTo-SecureString -AsPlainText -Force

Write-Host "Found credentials for $username."

Write-Host "Creating local user and adding to local administrators group."
New-LocalUser $username -Password $password -Description "AS2_Automation Remote WinRM administrator."
Add-LocalGroupMember -Group "Administrators" -Member $username

#Configure remote WinRM services
Write-Host "Enabling PSRemoting and WinRM Configuration."
Enable-PSRemoting -SkipNetworkProfileCheck -Force

#Opens basic authentication from Lambda functions to Image Builder
#These settings should be reviewed and modified as appropriate for fleet instances
winrm set winrm/config/client/auth '@{Basic="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'

#The network connection profile for non-domain joined machines defaults to Public
#This needs to be set to Private to allow the default Remote WinRM Firewall rules to function
$DomainCheck = (Get-WmiObject -Class Win32_computerSystem).PartOfDomain
if (-not $DomainCheck) {
    #The Unidentified network is the AppStream streaming/mangement network
	#Select the other network in customer VPC
	$ConnProfiles = Get-NetConnectionProfile | Where-Object {$_.Name  -NotLike "*Unidentified network*"}
    ForEach ($Profile in $ConnProfiles)
    {
        #Change Network Category to Private
		Set-NetConnectionProfile -Name $Profile.Name -NetworkCategory Private
    }
}
