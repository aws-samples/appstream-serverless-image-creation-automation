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

##*=====================================================================
##*
##* APPSTREAM 2.0 WORKSHOP - EXAMPLE APPLICATION INSTALL
##*
##* Use your standard installation script for the given application 
##* in the INSTALL APPLICATION section of this example.
##* Update the APPSTREAM VARIABLE DECLARATIONS to match the given app.
##*=====================================================================


##*===============================================
##* INSTALL APPLICATION
##*===============================================
	Write-Host "Installing PuTTY."
	[string]$AppInstallerPath = $PSScriptRoot + '\putty-installer.msi'
	[string]$Arguments = '/i ' + $AppInstallerPath + ' /QN'
	Start-Process -FilePath msiexec.exe -ArgumentList $Arguments -Wait
	Write-Host "Finished installing PuTTY."

##*=====================================================================
##*
##* APPSTREAM 2.0 WORKSHOP - BEGIN
##*
##*=====================================================================


	##*===============================================
	##* APPSTREAM VARIABLE DECLARATION
	##*===============================================
	[string]$AppName = 'PuTTY'
	[string]$AppPath = 'C:\Program Files\PuTTY\putty.exe'
	[string]$AppDisplayName = 'PuTTY'
	[string]$AppParameters = ''
	[string]$AppWorkingDir = ''
	[string]$AppIconPath =  ''
	[string]$ManifestPath = $PSScriptRoot + '\PuTTYManifest.txt'

	[string]$ImageAssistantPath = "C:\Program Files\Amazon\Photon\ConsoleImageBuilder\image-assistant.exe"


	##*===============================================
	##* ADD APPLICATION TO APPSTREAM CATALOG
	##*===============================================
	#AppStream's Image Assistant Required Parameters
	$Params = " --name " + $AppName + " --absolute-app-path """ + $AppPath + """"     

	#AppStream's Image Assistant Optional Parameters
	if ($AppDisplayName) { $Params += " --display-name """ + $AppDisplayName + """" }
	if ($AppWorkingDir) { $Params += " --working-directory """ + $AppWorkingDir + """" }
	if ($AppIconPath) { $Params += " --absolute-icon-path """ + $AppIconPath + """" }      
	if ($AppParameters) { $Params += " --launch-parameters """ + $AppParameters + """" }     
	if ($ManifestPath) { $Params += " --absolute-manifest-path """ + $ManifestPath + """" }

	#Escape spaces in EXE path
	$ImageAssistantPath = $ImageAssistantPath -replace ' ','` '

	#Assemble Image Assistant API command to add applications
	$AddAppCMD = $ImageAssistantPath + ' add-application' + $Params

	Write-Host "Adding $AppDisplayName to AppStream Image Catalog using command $AddAppCMD"

	#Run Image Assistant command and parameters
	$AddApp = Invoke-Expression $AddAppCMD | ConvertFrom-Json
	if ($AddApp.status -eq 0) {
		Write-Host "SUCCESS adding $AppName to the AppStream catalog."
	} else {
		Write-Host "ERROR adding $AppName to the AppStream catalog." 
		Write-Host $AddApp.message
	}

##*=====================================================================
##*
##* APPSTREAM 2.0 WORKSHOP - END
##*
##*=====================================================================
