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

import logging
import boto3
import json
import os
import winrm
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

appstream = boto3.client('appstream')
secretsmgr = boto3.client('secretsmanager')

def lambda_handler(event, context):
    logger.info("Beginning execution of AS2_Automation_Windows_Scripted_Install function.")

    # Retrieve S3 bucket for sourcefiles from event or environment variable
    logger.info("Querying for S3 bucket containing installation files.")
    if 'PackageS3Bucket' in event['AutomationParameters'] :
        S3Bucket = event['AutomationParameters']['PackageS3Bucket']
    else :
        S3Bucket = os.environ['Default_S3_Bucket']
    logger.info("Source S3 bucket found: %s.", S3Bucket)

    # Retrieve image builder IP address from event data
    logger.info("Querying for Image Builder instance IP address.")
    try :
        host = event['BuilderStatus']['ImageBuilders'][0]['NetworkAccessConfiguration']['EniPrivateIpAddress']
        logger.info("IP address found: %s.", host)
    except Exception as e :
        logger.error(e)
        logger.info("Unable to find IP address for Image Builder instance.")
        
    # Retrieve commands to run on image builder from event data
    try :
        commandArray = event['AutomationParameters']['ImageBuilderExtraCommands']
        if commandArray :
            logger.info("Installation command array found in event data: %s.", commandArray)
        else :
            logger.info("No additional commands to perform on the image builder in event data.")
    except Exception as e2 :
        logger.error(e2)
        logger.info("Error retreiving command array from event data: %s", e2)     
        

    # Read image builder administrator username and password from Secrets Manager
    logger.info("Retreiving instance username and password from Secrets Manager.")
    secret_name = "as2/builder/pw"
    secret_response = secretsmgr.get_secret_value(SecretId=secret_name)

    if 'SecretString' in secret_response:
        secret = json.loads(secret_response['SecretString'])
    else:
        secret = base64.b64decode(secret_response['SecretBinary'])

    user = secret['as2_builder_admin_user']
    password = secret['as2_builder_admin_pw']
    logger.info("Remote access credentials obtained: %s", user)

    try :
        # Connect to remote image builder using pywinrm library
        logger.info("Connecting to host: %s", host)
        session = winrm.Session(host, auth=(user, password))
    except Exception as e2 :
        logger.error(e2)
        logger.info("Unable to remotely connect to the Image Builder instance.")
        
    # Create temp directory
    logger.info("Creating temp directory.")
    result = session.run_ps("New-Item -Path c:\\ -Name \"temp\" -ItemType \"directory\" -force")

    # If an array of PowerShell commands were passed to the Step Function, run them
    if commandArray:
        for cmd in commandArray:
            session.run_ps(cmd)


    ############################################################
    # Install  Notepad++ package and add to application catalog
    prefix = "Read-S3Object -BucketName "
    suffix = " -KeyPrefix NotepadPP -Folder c:\\temp\\NotepadPP -ProfileName appstream_machine_role"
    command = prefix + S3Bucket + suffix       
    logger.info("Downloading Notepad++ sourcefiles from S3 to temp directory using command: %s", command)
    result = session.run_ps(command)
    dlresult = session.run_ps("Test-Path -Path c:\\temp\\NotepadPP\\Install_NotepadPP.ps1 -PathType Leaf")
    restext = str(dlresult.std_out)
    if "True" in restext :
        logger.info("Software download complete, begining software installation: Notepad++.")
        result = session.run_ps("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -ExecutionPolicy Bypass -File c:\\temp\\NotepadPP\\Install_NotepadPP.ps1")
        logger.info("Completed installation, removing local installation files: Notepad++.")
    else :
        logger.info("Unable to successfully download software installation aborted: Notepad++. Cleaning up any files downloaded. Confirm file path is correct and files were uploaded to SourceS3Bucket.")
    result = session.run_ps("Remove-Item 'C:\\temp\\NotepadPP' -Recurse")
    ############################################################
    
    
    ############################################################
    # Install  PuTTY package and add to application catalog
    prefix = "Read-S3Object -BucketName "
    suffix = " -KeyPrefix PuTTY -Folder c:\\temp\\PuTTY -ProfileName appstream_machine_role"
    command = prefix + S3Bucket + suffix 
    logger.info("Downloading PuTTY sourcefiles from S3 to temp directory using command: %s", command)
    result = session.run_ps(command)
    dlresult = session.run_ps("Test-Path -Path c:\\temp\\PuTTY\\Install_PuTTY.ps1 -PathType Leaf")
    restext = str(dlresult.std_out)
    if "True" in restext :
        logger.info("Software download complete, begining software installation: PuTTY.")
        result = session.run_ps("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -ExecutionPolicy Bypass -File c:\\temp\\PuTTY\\Install_PuTTY.ps1")
        logger.info("Completed installation, removing local installation files: PuTTY.")
    else :
        logger.info("Unable to successfully download software installation aborted: PuTTY. Cleaning up any files downloaded. Confirm file path is correct and files were uploaded to SourceS3Bucket.")
    result = session.run_ps("Remove-Item 'C:\\temp\\PuTTY' -Recurse") 
    ############################################################


    ############################################################
    # Dynamically download Draw.io and add to application catalog
    command = "mkdir 'C:\\Program Files\\Drawio\\'"
    result = session.run_ps(command)
    command = "Invoke-WebRequest -Uri https://github.com/jgraph/drawio-desktop/releases/download/v15.4.0/draw.io-15.4.0-windows-no-installer.exe -OutFile 'C:\\Program Files\\Drawio\\draw.io-15.4.0-windows-no-installer.exe'"
    logger.info("Downloading Draw.io sourcefiles from Github using command: %s", command)
    result = session.run_ps(command)
    dlresult = session.run_ps("Test-Path -Path 'C:\\Program Files\\Drawio\\draw.io-15.4.0-windows-no-installer.exe' -PathType Leaf")
    restext = str(dlresult.std_out)
    if "True" in restext :
        command = 'C:/PROGRA~1/Amazon/Photon/ConsoleImageBuilder/image-assistant.exe add-application --name Draw.io --display-name Draw.io --absolute-app-path C:/PROGRA~1/Drawio/draw.io-15.4.0-windows-no-installer.exe'
        logger.info("Software download complete, adding software to catalog: Draw.io using command: %s", command)
        result = session.run_cmd(command)
    else :
        logger.info("Unable to successfully download software installation aborted: Draw.io. Cleaning up directory.")
        result = session.run_ps("Remove-Item 'C:\\Program Files\\Drawio' -Recurse") 
    ############################################################
    
    
    # Removes the DummyApp that was required for the creation of the non-domain joined base image.
    logger.info("Removing DummyApp from image catalog (if present).")
    command = '"c:\\Program Files\\Amazon\\Photon\\ConsoleImageBuilder\\image-assistant.exe" remove-application --name DummyApp'
    result = session.run_cmd(command)

    logger.info("Completed AS2_Automation_Windows_Scripted_Install function, returning to Step Function.")
    return {
        'Method' : "Script",
        'Status' : "Complete"
    }