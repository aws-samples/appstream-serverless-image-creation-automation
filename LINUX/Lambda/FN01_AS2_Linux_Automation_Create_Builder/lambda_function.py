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
import botocore

logger = logging.getLogger()
LOGLEVEL = os.getenv('LOGLEVEL', 'INFO').upper()
logger.setLevel(LOGLEVEL)

appstream = boto3.client('appstream')

def lambda_handler(event, context):
    logger.info("Beginning execution of AS2_Automation_Linux_Create_Builder function.")

    # Retrieve starting parameters from event data
    # If parameter not found, inject default values defined in Lambda function
    if 'ImageBuilderName' in event :
        IB_Name = event['ImageBuilderName']
    else :
        IB_Name = os.environ['Default_IB_Name']

    if 'ImageBuilderImage' in event :
        IB_Image = event['ImageBuilderImage']
    else :
        IB_Image = os.environ['Default_Image']

    if 'ImageBuilderType' in event :
        IB_Type = event['ImageBuilderType']
    else :
        IB_Type = os.environ['Default_Type']        

    if 'ImageBuilderSubnet' in event :
        IB_Subnet = event['ImageBuilderSubnet']
    else :
        IB_Subnet = os.environ['Default_Subnet']

    if 'ImageBuilderSecurityGroup' in event :
        IB_SG = event['ImageBuilderSecurityGroup']
    else :
        IB_SG = os.environ['Default_SG']

    if 'ImageBuilderIAMRole' in event :
        IB_Role = event['ImageBuilderIAMRole']
    else :
        IB_Role = os.environ['Default_Role']
        
    if 'ImageBuilderDisplayName' in event :
        IB_DisplayName = event['ImageBuilderDisplayName']
    else :
        IB_DisplayName = os.environ['Default_DisplayName']   

    if 'ImageBuilderDescription' in event :
        IB_Description = event['ImageBuilderDescription']
    else :
        IB_Description = os.environ['Default_Description']   

    if 'ImageBuilderInternetAccess' in event :
        IB_Internet = event['ImageBuilderInternetAccess']
    else :
        IB_Internet = False
        
    if 'ImageOutputPrefix' in event :
        IB_Prefix = event['ImageOutputPrefix']
    else :
        IB_Prefix = os.environ['Default_Prefix']

    if 'ImageTags' in event :
        Image_Tags = event['ImageTags']
    else :
        Image_Tags = False         
        
    if 'UseLatestAgent' in event :
        UseLatestAgent = event['UseLatestAgent']
    else :
        UseLatestAgent = True     

    if 'DeleteBuilder' in event :
        Delete_Builder = event['DeleteBuilder']
    else :
        Delete_Builder = False    

    if 'DeployMethod' in event :
        DeployMethod = event['DeployMethod']
    else :
        DeployMethod = os.environ['Default_Method']
        
    if 'ImageBuilderCommands' in event :
        ImageBuilderCommands = event['ImageBuilderCommands']
    else :
        ImageBuilderCommands = False

    if 'CreateManifests' in event :
        CreateManifests = event['CreateManifests']
    else :
        CreateManifests = True  

    if 'DeleteTempManifests' in event :
        DeleteTempManifests = event['DeleteTempManifests']
    else :
        DeleteTempManifests = False

    if 'RemoveXvfb' in event :
        RemoveXvfb = event['RemoveXvfb']
    else :
        RemoveXvfb = True                             

    if 'ImageBuilderSSHKeyARN' in event :
        ImageBuilderSSHKeyARN = event['ImageBuilderSSHKeyARN']
        # Obtain SSH key name from ARN, split the ARN then remove the leading word parameter           
        ARNtoName = ImageBuilderSSHKeyARN.split(':')
        ImageBuilderSSHKeyName = ARNtoName[5].lstrip("parameter")
    elif 'ImageBuilderSSHKeyName' in event :
        ImageBuilderSSHKeyName = event['ImageBuilderSSHKeyName']
    else :
        ImageBuilderSSHKeyARN = os.environ['Default_ImageBuilderSSHKeyARN']
        # Obtain SSH key name from ARN, split the ARN then remove the leading word parameter           
        ARNtoName = ImageBuilderSSHKeyARN.split(':')
        ImageBuilderSSHKeyName = ARNtoName[5].lstrip("parameter")

    if 'NotifyARN' in event :
        NotifyARN = event['NotifyARN']
    else :
        NotifyARN = False

    try :
        # Checking for existing Image Builder with same name   
        logger.info("Checking for existing Image Builder: %s.", IB_Name)
        response = appstream.describe_image_builders(
        Names=[
            IB_Name,
        ],
        MaxResults=1
        )
        
        logger.info("Builder already exists, skipping creation and reconfiguring input parameters to match.")
        
        # Reconfigure variables to values from existing Image Builder
        BuilderName = IB_Name
        IB_Type = response['ImageBuilders'][0]['InstanceType']
        IB_Image = response['ImageBuilders'][0]['ImageArn']
        IB_Subnet = response['ImageBuilders'][0]['VpcConfig']['SubnetIds'][0]
        IB_SG = response['ImageBuilders'][0]['VpcConfig']['SecurityGroupIds'][0]
        IB_Role = response['ImageBuilders'][0]['IamRoleArn'] 
        IB_DisplayName = response['ImageBuilders'][0]['DisplayName']
        IB_Description = response['ImageBuilders'][0]['Description']
        IB_Internet = response['ImageBuilders'][0]['EnableDefaultInternetAccess']
        
        PreExistingBuilder = True
    
    except :
        logger.info("Image Builder does not exist, beginning creation.")
        try :
            response = appstream.create_image_builder(
                Name=IB_Name,
                ImageName=IB_Image,
                InstanceType=IB_Type,
                Description=IB_Description,
                DisplayName=IB_DisplayName,
                VpcConfig={
                    'SubnetIds': [
                        IB_Subnet,
                    ],
                    'SecurityGroupIds': [
                        IB_SG,
                    ]
                },
                IamRoleArn=IB_Role,
                EnableDefaultInternetAccess=IB_Internet,
                Tags={
                    'Automated': 'True'
                }
            )
        
            BuilderName = response['ImageBuilder']['Name']
            BuilderARN = response['ImageBuilder']['Arn']
            
            logger.info("Created new Image Builder with ARN: %s.", BuilderARN)

            PreExistingBuilder = False
        
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                logger.error(error)
                logger.info("Image Builder Already Exists, moving on to next step.")
                BuilderName = IB_Name
            else:
                logger.error(error)
                raise error
    
        except Exception as e:
            logger.error(e)
            raise e
    
    logger.info("Completed AS2_Automation_Linux_Create_Builder function, returning to Step Function.")
    return {
        "AutomationParameters": {
            'ImageBuilderName' : BuilderName,
            'ImageBuilderType' : IB_Type,
            'ImageBuilderImage' : IB_Image,
            'ImageBuilderSubnet' : IB_Subnet,
            'ImageBuilderSecurityGroup' : IB_SG,
            'ImageBuilderIAMRole' : IB_Role,
            'ImageBuilderDisplayName' : IB_DisplayName,
            'ImageBuilderDescription' : IB_Description,
            'ImageBuilderInternetAccess' : IB_Internet,
            'ImageBuilderCommands' : ImageBuilderCommands,
            'ImageBuilderSSHKeyName' : ImageBuilderSSHKeyName,
            'PreExistingBuilder' : PreExistingBuilder,
            'DeleteBuilder' : Delete_Builder,
            'ImageOutputPrefix' : IB_Prefix,
            'ImageTags' : Image_Tags,
            'UseLatestAgent' : UseLatestAgent,            
            'CreateManifests' : CreateManifests,
            'DeleteTempManifests' : DeleteTempManifests,
            'RemoveXvfb' : RemoveXvfb,
            'DeployMethod' : DeployMethod,
            'NotifyARN' : NotifyARN
        }
    }