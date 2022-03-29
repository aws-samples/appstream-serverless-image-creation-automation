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
import datetime
import winrm
import base64
import sys
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

secretsmgr = boto3.client('secretsmanager')

def lambda_handler(event, context):
    logger.info("Beginning execution of AS2_Automation_Windows_Run_Image_Assistant function.")

    # Retrieve image builder IP address from event data
    logger.info("Querying for Image Builder instance IP address.")
    try :
        host = event['BuilderStatus']['ImageBuilders'][0]['NetworkAccessConfiguration']['EniPrivateIpAddress']
        logger.info("IP address found: %s.", host)
    except Exception as e :
        logger.error(e)
        logger.info("Unable to find IP address for Image Builder instance.")

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
        # Retrieve image name from event data
        try :
            image_name = event['AutomationParameters']['ImageOutputPrefix']
            logger.info("Image name prefix found in event data: %s.", image_name)
        except Exception as e :
            image_name = 'AS2_Automation_Image'
            logger.info("No image name prefix found in event data, defaulting to AS2_Automation_Image.")
        
        # Retrieve UseLatestAgent from event data, default to True
        try :
            UseLatestAgent = event['AutomationParameters']['UseLatestAgent']
            logger.info("UseLatestAgent found in event data, setting to %s.", UseLatestAgent)
        except Exception as e2 :
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
        except Exception as e3 :
            ImageTags = False
            logger.info("No Image Tags found in event data, generated image will not be tagged.")
            
        if ImageTags :
            tag_image = ' --tags ' + ImageTags
        else :
            tag_image = ''            

        # Base image assistant command
        prefix = 'C:/PROGRA~1/Amazon/Photon/ConsoleImageBuilder/image-assistant.exe create-image --name '

        # Generate full image name using image name prefix and timestamp
        now = datetime.now()
        dt_string = now.strftime("-%Y-%m-%d-%H-%M-%S")
        full_image_name = image_name + dt_string
        
        # Final image assistant command
        command = prefix + full_image_name + latest_agent + tag_image

        # Connect to remote image builder using pywinrm library
        logger.info("Connecting to host: %s", host)
        session = winrm.Session(host, auth=(user, password))
        logger.info("Session connection result: %s", session)        

        # Run image assistant command to create image
        logger.info("Executing Image Assistant command: %s", command)
        result = session.run_cmd(command)
        logger.info("Results from image assistant command: %s", result.std_out)
        
        if b"ERROR" in result.std_out:
            logger.info("ERROR running Image Assistant!")
            sys.exit(1)
        else:
            logger.info("Completed execution of Image Assistant command.")

    except Exception as e3 :
        logger.error(e3)
        full_image_name = "Not Found"

    logger.info("Completed AS2_Automation_Windows_Run_Image_Assistant function, returning values to Step Function.")
    return {
        "Images": [
          {
            "Name": full_image_name
          }
        ]
    }