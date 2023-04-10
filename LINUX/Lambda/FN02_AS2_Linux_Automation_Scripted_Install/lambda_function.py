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
import paramiko
import os
from io import StringIO

logger = logging.getLogger()
LOGLEVEL = os.getenv('LOGLEVEL', 'INFO').upper()
logger.setLevel(LOGLEVEL)


# Get parameter from SSM
def get_parameters(param):
    # Start SSM client
    ssm = boto3.client('ssm')
    
    # Retrieve passed parameter from SSM parameter store
    response = ssm.get_parameters(
        Names=[param],WithDecryption=True
    )
    
    for parameter in response['Parameters']:
        return parameter['Value']


# Establish ssh connection to instance
def connect_ssh(ip, username):
    connected = False

    try:
        ssh.connect(hostname=ip, port=22, username=username, pkey=privkey)
        connected = True
        return connected
    except:
        ssh.close()
        

# Run shell command on connected instance
def run_command(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdin.flush()
    
    data = stdout.read().splitlines()
    
    for line in data:
        print(line)        


# Main function handler
def lambda_handler(event, context):
    logger.info("Beginning execution of AS2_Automation_Linux_Scripted_Install function.")

    # Retrieve image builder SSH key name from event data
    logger.info("Querying for image builder SSH key name.")
    try :
        ssh_key_name = event['AutomationParameters']['ImageBuilderSSHKeyName']
        logger.info("SSH key name found in event data: %s.", ssh_key_name)
    except Exception as e :
        logger.error(e)
        logger.info("Unable to find SSH key name in event data.")

    # Retrieve option to dynamically generate AppStream application optimization manifests from event data
    if 'CreateManifests' in event['AutomationParameters'] :
        create_manifests = event['AutomationParameters']['CreateManifests']
        logger.info("CreateManifests found in event data, setting to: %s.", create_manifests)
    else :
        create_manifests = True
        logger.info("CreateManifests not found in event data, defaulting to True.")

    # Retrieve option to delete temporary manifest files from event data
    if 'DeleteTempManifests' in event['AutomationParameters'] :
        delete_manifests = event['AutomationParameters']['DeleteTempManifests']
        logger.info("DeleteTempManifests found in event data, setting to: %s.", delete_manifests)
    else :
        delete_manifests = False
        logger.info("DeleteTempManifests not found in event data, defaulting to False.")

    # Retrieve option to remove Xvfb after manifest generation is complete from event data
    if 'RemoveXvfb' in event['AutomationParameters'] :
        remove_xvfb = event['AutomationParameters']['RemoveXvfb']
        logger.info("RemoveXvfb found in event data, setting to: %s.", remove_xvfb)
    else :
        remove_xvfb = True
        logger.info("RemoveXvfb not found in event data, defaulting to True.")

    # Retrieve image builder IP address from event data
    try :
        ip = event['BuilderStatus']['ImageBuilders'][0]['NetworkAccessConfiguration']['EniPrivateIpAddress']
        logger.info("Image builder IP address found in event data: %s.", ip)
    except Exception as e :
        logger.error(e)
        logger.info("Unable to find IP address for image builder instance in event data.")
        
    # Retrieve commands to run on image builder from event data
    try :
        commandArray = event['AutomationParameters']['ImageBuilderCommands']
        if commandArray :
            logger.info("Installation command array found in event data: %s.", commandArray)
        else :
            logger.info("Unable to find array of commands to perform on the image builder in event data. Defaulting to performing a 'yum update' command.")
            commandArray = ["sudo yum -y update"]
    except Exception as e2 :
        logger.error(e2)
        logger.info("Error retreiving command array from event data: %s", e2)      

    # Get RSA key from parameter store
    logger.info("Retreiving RSA key from Parameter Store.")
    global privkey 
    privkey = paramiko.RSAKey.from_private_key(file_obj=StringIO(get_parameters(ssh_key_name)))

    # Start SSH client
    global ssh 
    ssh = paramiko.SSHClient()

    # Automatically adding the hostname and new host key to the local HostKeys object
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # User account embeded in base image
    username = "as2-automation"

    logger.info("Connecting to image builder: %s.", ip)
    isConnected = connect_ssh(ip, username)

    # Once connected to image builder, run commands found in commands array        
    if (isConnected) :
        logger.info("Successfully connected to image builder.")

        # Install Xvfb package on image builder to enable launching of apps for AppStream app manifest creation
        run_command ("sudo yum -y install Xvfb > /dev/null")
            
        for cmd in commandArray:
            # If the command is related to adding app to AppStream catalog, check if a manifest should be dynamically generated
            if "AppStreamImageAssistant add-application" in cmd :
                logger.info("Image Assistant add-application command detected, parsing command.")
                if "--absolute-manifest-path" in cmd :
                    # If the presence of manifest is detected in the command, a new one will not be dynamically generated
                    logger.info("Manifest found in passed image assistant command, using that with application import.")
                    manifest_file = False
                elif not create_manifests :
                    # If no manifest command is detected and the option to generate manifests dynamically is disabled, one will not be generated
                    logger.info("No manifest found in command, but one will not be generated due to CreateManifests being set to false.")
                    manifest_file = False
                else :
                    # If no manifest command is detected, one will be dynamically generated
                    logger.info("No Manifest found in passed image assistant command, attempting to create one.")
                    app_path = cmd.split("--absolute-app-path ")[1] # Split off everything after absolute-app-path
                    app_path = app_path.split(" ")[0] # Split off everything before space to get path to app
                    app_exe = app_path.rsplit("/")[-1] # Split app path to get executable name
                    manifest_command = "xvfb-run /tmp/generate_appstream_manifest.sh " + app_path + " " + app_exe
                    run_command(manifest_command) # Generate manifest file
                    
                    # Check if generation was successful (manifest exists)
                    manifest_file = "/tmp/as2_manifest_" + app_exe + ".txt"
                    manifest_check = "test -e " + manifest_file + " && echo exists"
                    stdin, stdout, stderr = ssh.exec_command(manifest_check)
                    output_data = stdout.read().splitlines()
                    file_exists = False
                    for lines in output_data:
                        if "exists" in str(lines):
                            file_exists = True
                    
                    # If manifest generation was successful, append image assistant command
                    if file_exists :
                        logger.info("Manifest generated. Appending to image assistant command.")
                        cmd = cmd + " --absolute-manifest-path " + manifest_file
                    else :
                        logger.info("Manifest not generated. Using original image assistant command without a manifest.")                 

                logger.info("Running image assistant command: %s", cmd)
                run_command(cmd)

                # If manifest was dynamically generated and cleanup is configured, delete manifest
                if delete_manifests and manifest_file:
                    logger.info("Removing temporary dynamically generated app manifest file: %s", manifest_file)
                    delete_command = "sudo rm " + manifest_file
                    run_command(delete_command)
                
                manifest_file = False    
            else :
                # Execute commands that are not related to 'AppStreamImageAssistant add-application'
                logger.info("Running command: %s", cmd)
                run_command(cmd)

        # Remove Xvfb package from image builder if requested
        if remove_xvfb :
            run_command ("sudo yum -y remove Xvfb > /dev/null")
            logger.info("Removed Xvfb from image builder.")
        else :    
            logger.info("Xvfb will not be removed from image builder.")
            
        logger.info("Completed all commands, closing SSH connection.")
        ssh.close()    
    else :
        logger.info("Connection to image builder failed.")

    logger.info("Completed AS2_Automation_Linux_Scripted_Install function, returning to Step Function.")
    return {
        'Method' : "Script",
        'Status' : "Complete"
    }