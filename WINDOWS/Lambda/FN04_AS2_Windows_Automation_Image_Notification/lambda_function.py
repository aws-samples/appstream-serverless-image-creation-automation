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
import os
import json
import textwrap

logger = logging.getLogger()
LOGLEVEL = os.getenv('LOGLEVEL', 'INFO').upper()
logger.setLevel(LOGLEVEL)

appstream = boto3.client('appstream')
sns = boto3.client('sns')


def lambda_handler(event, context):
    logger.info("Beginning execution of AS2_Automation_Windows_Image_Notification function.")

    # Retrieve SNS topic ARN from event data
    # If parameter not found, inject default value defined in Lambda function environment variables
    if 'NotificationArn' in event['AutomationParameters'] :
        NotifyARN = event['AutomationParameters']['NotificationArn']
        if NotifyARN :
            logger.info("SNS Notification ARN found found in event data: %s.", NotifyARN)
        else :
            NotifyARN = os.environ['NotificationARN']
            logger.info("SNS Notification ARN not found found in event data, using default ARN from Lambda environment variable: %s.", NotifyARN)
    else :
        NotifyARN = os.environ['NotificationARN']
        logger.info("SNS Notification ARN not found found in event data, using default ARN from Lambda environment variable: %s.", NotifyARN)
    
    # Retrieve AppStream image name from event data
    ImageName = event['ImageStatus']['Images'][0]['Name']
    
    # Attempt to query status of AppStream image
    try :
        response = appstream.describe_images(
            Names=[
                ImageName,
            ]
        )
        
        logger.info("Image found, generating notification content.")
        
        # Pull required information from response
        ImageState = response['Images'][0]['State']
        ImagePlatform = response['Images'][0]['Platform']
        AgentVersion = response['Images'][0]['AppstreamAgentVersion']
        ImageBuilderName = response['Images'][0]['ImageBuilderName']
        AppsArray = response['Images'][0]['Applications']
    
        # Create list of applications detected in image
        AppList = ""
        for App in AppsArray:
            AppList += App['Name'] + "\n"

        # Get AWS account number
        AccountId = boto3.client('sts').get_caller_identity()['Account']

    except Exception as e:
        logger.error(e)
        logger.info("Unable to query status of image.")
        
    # Get list of all parameters sent into the Lambda function from event
    FullOutput = json.dumps(event, indent=4, separators=(',', ': '), sort_keys=False)

    sbj = "AppStream Image Creation Notification: {0}".format(ImageName)
    
    msg = textwrap.dedent('''\
        ------------------------------------------------------------------------------
        Image Information:
        ------------------------------------------------------------------------------
        Name: \t\t {0}
        Platform: \t {1}
        Agent Version: \t {2}
        Builder Name: \t {3} 
        Status: \t\t {4}
        AWS Account: \t {5} \n
        ------------------------------------------------------------------------------
        Included Applications:
        ------------------------------------------------------------------------------
        {6}
        ------------------------------------------------------------------------------
        Full Output:
        ------------------------------------------------------------------------------
        {7}
        ''').format(ImageName,ImagePlatform,AgentVersion,ImageBuilderName,ImageState,AccountId,AppList,FullOutput)


    # Publish image information to SNS Topic    
    try :
        response = sns.publish(
            TopicArn=NotifyARN,
            Message=msg,
            Subject=sbj
        )
        
        MessageID = response['MessageId']
        
        logger.info("Notification published to SNS topic.")
        
    except Exception as e2:
        logger.error(e2)
        MessageID = "Error"

    logger.info("Completed AS2_Automation_Windows_Image_Notification function, returning MessageID to Step Function.")
    return MessageID

