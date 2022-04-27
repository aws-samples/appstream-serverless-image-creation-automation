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
from io import StringIO

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


# Establish ssh connection to passed instance
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


def lambda_handler(event, context):
    logger.info("Beginning execution of AS2_Automation_Linux_Scripted_Install function.")

    # Retrieve image builder SSH key name from event data
    logger.info("Querying for image builder SSH key name.")
    try :
        ssh_key_name = event['AutomationParameters']['ImageBuilderSSHKeyName']
        logger.info("SSH key name found: %s.", ssh_key_name)
    except Exception as e :
        logger.error(e)
        logger.info("Unable to find SSH key name in event data.")
    
    # Get RSA key from parameter store
    logger.info("Retreiving RSA key from Parameter Store.")
    global privkey 
    privkey = paramiko.RSAKey.from_private_key(file_obj=StringIO(get_parameters(ssh_key_name)))

    # Start SSH client
    global ssh 
    ssh = paramiko.SSHClient()

    # Automatically adding the hostname and new host key to the local HostKeys object
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Retrieve image builder IP address from event data
    logger.info("Querying for image builder instance IP address.")
    try :
        ip = event['BuilderStatus']['ImageBuilders'][0]['NetworkAccessConfiguration']['EniPrivateIpAddress']
        logger.info("IP address found: %s.", ip)
    except Exception as e :
        logger.error(e)
        logger.info("Unable to find IP address for image builder instance in event data.")
        
    # Retrieve commands to run on image builder from event data
    logger.info("Querying for installation commands.")
    try :
        commandArray = event['AutomationParameters']['ImageBuilderCommands']
        if commandArray :
            logger.info("Command array found: %s.", commandArray)
        else :
            logger.info("Unable to find array of commands to perform on the image builder in event data. Defaulting to performing a yum update command.")
            commandArray = ["sudo yum -y update"]
    except Exception as e2 :
        logger.error(e2)
        logger.info("Error retreiving command array from event data: %s", e2)        

    # User account embeded in base image
    username = "as2-automation"

    logger.info("Connecting to image builder: %s.", ip)
    isConnected = connect_ssh(ip, username)

    # Once connected to image builder, run commands found in commands array        
    if (isConnected) :
        logger.info("Successfully connected to image builder.")
        commands = commandArray
            
        for cmd in commands:
            logger.info("Running command: %s", cmd)
            run_command(cmd)

        logger.info("Completed all commands, closing SSH connection.")
        ssh.close()    

    logger.info("Completed AS2_Automation_Linux_Scripted_Install function, returning to Step Function.")
    return {
        'Method' : "Script",
        'Status' : "Complete"
    }
