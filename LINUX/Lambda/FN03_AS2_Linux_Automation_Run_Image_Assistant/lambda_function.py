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
import datetime
import paramiko
import os
from datetime import datetime
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
    logger.info("Beginning execution of AS2_Automation_Linux_Run_Image_Assistant function.")

    # Retrieve image builder SSH key name from event data
    logger.info("Querying for image builder SSH key name.")
    try :
        ssh_key_name = event['AutomationParameters']['ImageBuilderSSHKeyName']
        logger.info("SSH key name found: %s.", ssh_key_name)
    except Exception as e :
        logger.error(e)
        logger.info("Unable to find SSH key name in event data.")

    # Get RSA Key from parameter store
    logger.info("Retreiving RSA key from Parameter Store.")
    global privkey 
    privkey = paramiko.RSAKey.from_private_key(file_obj=StringIO(get_parameters(ssh_key_name)))

    # Start SSH client
    global ssh 
    ssh = paramiko.SSHClient()

    # Automatically adding the hostname and new host key to the local HostKeys object
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    #Retrieve image builder IP address from event data
    logger.info("Querying for Image Builder instance IP address.")
    try :
        ip = event['BuilderStatus']['ImageBuilders'][0]['NetworkAccessConfiguration']['EniPrivateIpAddress']
        logger.info("IP address found: %s.", ip)
    except Exception as e :
        logger.error(e)
        logger.info("Unable to find IP address for Image Builder instance in event data.")
       
    # User account embeded in base image
    username = "as2-automation"

    # Retrieve image name from event data
    try :
        image_name = event['AutomationParameters']['ImageOutputPrefix']
        logger.info("Image name prefix found in event data: %s.", image_name)
    except Exception as e2 :
        image_name = 'AS2_Automation_Image'
        logger.info("No image name prefix found in event data, defaulting to AS2_Automation_Image.")
    
    # Retrieve UseLatestAgent from event data, default to True
    try :
        UseLatestAgent = event['AutomationParameters']['UseLatestAgent']
        logger.info("UseLatestAgent found in event data, setting to %s.", UseLatestAgent)
    except Exception as e3 :
        UseLatestAgent = True
        logger.info("UseLatestAgent not found in event data, defaulting to True")
        
    if UseLatestAgent :
        latest_agent = ' --use-latest-agent-version'
    else :
        latest_agent = ' --no-use-latest-agent-version'

    # Retrieve image tags from event data
    try :
        ImageTags = event['AutomationParameters']['ImageTags']
        if ImageTags :
            logger.info("Image Tags found in event data: %s.", ImageTags)
        else :
            logger.info("No Image Tags found in event data, generated image will not be tagged.")
    except Exception as e4 :
        ImageTags = False
        logger.info("No Image Tags found in event data, generated image will not be tagged.")
        
    if ImageTags :
        tag_image = ' --tags ' + ImageTags
    else :
        tag_image = ''   

    # Base image assistant command
    prefix = 'sudo AppStreamImageAssistant create-image --name '

    # Generate full image name using image name prefix and timestamp
    now = datetime.now()
    dt_string = now.strftime("-%Y-%m-%d-%H-%M-%S")
    full_image_name = image_name + dt_string
    
    # Final image assistant command
    command = prefix + full_image_name + latest_agent + tag_image

    # Connect to remote image builder using pywinrm library
    logger.info("Connecting to Image Builder: %s.", ip)
    isConnected = connect_ssh(ip, username)

    # Once connected to image builder, run command to create image          
    if (isConnected) :
        logger.info("Successfully connected to image builder.")        

        logger.info("Running command: %s", command)
        run_command(command)

        logger.info("Completed image creation command, closing ssh connection.")
        ssh.close()    

    logger.info("Completed AS2_Automation_Linux_Run_Image_Assistant function, returning values to Step Function.")
    return {
        "Images": [
          {
            "Name": full_image_name
          }
        ]
    }