[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit) [![cfn_nag:passing](https://img.shields.io/badge/cfn__nag-passing-brightgreen.svg)](https://github.com/stelligent/cfn_nag) ![GitHub](https://img.shields.io/github/license/aws-samples/appstream-serverless-image-creation-automation)

# Amazon AppStream 2.0 Serverless Image Automation for Windows

Customers often ask how they can streamline the management and maintenance of their Amazon AppStream 2.0 images and fleets. The AppStream 2.0 service includes a rich set of APIs that allow you to programmatically interact with the service. In addition, the Image Assistant utility within the image builder instances supports [command line interface (CLI)](https://docs.aws.amazon.com/appstream2/latest/developerguide/programmatically-create-image.html) operations for adding applications to the fleet and creating images. What we commonly see is customers struggle with linking the two together; interacting with the service external to the image builder and running commands programmatically within the Microsoft Windows guest operating system within.

This repository contains the supporting scripts for the AWS EUC blog article [Automatically Create Customized AppStream 2.0 Windows Images](https://aws.amazon.com/blogs/desktop-and-application-streaming/tag/euc/). Please refer to the blog article for guidance on deploying the solution. 

<p align="center">
   <img src="/WindowsSolutionDiagram.png" alt="Solution Diagram for Windows Image Builders" />
</p>

Once you have successfully deployed the solution and ran the sample automation pipeline, you should customize the applications installed into the image and the parameters of the workflow to meet your needs.

### Customizing Executions of Step Function

For any parameters not specified in the Step Function execution JSON, a default value will be used. These default values can be viewed and/or modified on the Lambda function that creates the image builder.
1.	Navigate to the AWS Lambda console and select **Functions**.
2.	Click on the **AS2_Automation_Windows_FN01_Create_Builder_########** function.
3.	Select the **Configuration** tab.
4.	Select **Environment variables**.
5.	To change a default value, click **Edit**, modify the value, and click **Save**.


Default values were entered when the automation was deployed from CloudFormation. These values are used as inputs into the Step Function running the automation and the below parameters can be passed into the Step Function to override them. Options include:
- **ImageBuilderName**: The name to use when creating the image builder instance.
- **ImageBuilderType**: The instance type/class to use. See the AppStream 2.0 [pricing page](https://aws.amazon.com/appstream2/pricing/) for a list of instance types available.
- **ImageBuilderDescription**: The description associated with the image metadata.
- **ImageBuilderType**: The instance type of the image builder.
- **ImageOutputPrefix**: The name of the image created from the automation; a timestamp is automatically appended to the end.
- **DeleteBuilder**: true or false, option to retain or delete the image builder once the automation is complete. (Default is false)
- **ImageBuilderImage**: Name of the base image to use when creating the image builder.
- **ImageBuilderSubnet**: Subnet ID to place the image builder instance in.
- **ImageBuilderSecurityGroup**: Security Group ID to assign to the image builder instance.
- **ImageBuilderIAMRole**: IAM Role ARN to assign to the image builder instance.
- **ImageBuilderDomain**: The Active Directory domain to join the image builder instance to. Must be [configured in the AppStream console](https://docs.aws.amazon.com/appstream2/latest/developerguide/active-directory.html).
- **ImageBuilderOU:** The OU to place the image builder instance inside of, in distinguished name format. Must be [configured in the AppStream console](https://docs.aws.amazon.com/appstream2/latest/developerguide/active-directory.html).
- **ImageBuilderInternetAccess**: true or false, choice to provide default [internet access](https://docs.aws.amazon.com/appstream2/latest/developerguide/internet-access.html) to the image builder instance. You must specify a public subnet for ImageBuilderSubnet if using default internet access.
- **ImageTags**: The [tags](https://docs.aws.amazon.com/appstream2/latest/developerguide/tagging-basic.html) to apply to the generated AppStream 2.0 image. This should be entered as a list of key-value pairs seperated by spaces: tag1 value1 tag2 value2
- **UseLatestAgent**: true or false, specify whether to pin the image to the version of the AppStream 2.0 agent that is currently installed, or to always use the latest agent version.
- **NotifyARN**: ARN of the SNS topic that completion email will be sent to.
- **PackageS3Bucket**: the bucket name where the application silent installation packages were uploaded.

An example JSON statement used to start an execution of the automation Step Function can be found below. In this example, several of the above parameters are entered to control the behavior of the automation. The image will be named "AS2_Automation_Windows_Example_TIMESTAMP", uses a stream.standard.large instance size, will ensure the latest version of the AppStream agent is installed, tags the image, and places the image builder into the Image_Builders OU in the Active Direcotry domain yourdomain.int.
```
{
    "ImageBuilderName": "AS2_Automation_Windows_Example",
    "ImageBuilderType": "stream.standard.large",
    "ImageOutputPrefix": "AS2_Automation_Windows_Example",
    "ImageBuilderDomain": "yourdomain.int,
    "ImageBuilderOU": "OU=Image_Builders,OU=AppStream,DC=yourdomain,DC=int",
    "UseLatestAgent": true,
    "ImageTags": "'tag1' 'value1' 'tag2' 'value2'",
    "DeleteBuilder": true
}
```

### Customizing Installation Packages

While the sample applications included as part of this article are useful in demonstrating the workflow, you should now update the packages and scripts to reflect the applications required in your image(s). 
1.	Use the existing packages provided with the workshop as a template when creating or modifying your own install routines. In particular, your install routines need to ensure that they are adding the application to the AppStream Image Assistant catalog. Please refer to the [CLI documentation](https://docs.aws.amazon.com/appstream2/latest/developerguide/programmatically-create-image.html#cli-operations-managing-creating-image-image-assistant) for additional details about programmatically adding applications to the catalog.

Below is the relevant section of PowerShell code in the sample install scripts that you can use when creating your own application install packages:

```
    ##*===============================================
    ##* APPSTREAM VARIABLE DECLARATION
    ##*===============================================
    [string]$AppName = 'Notepad++'
    [string]$AppPath = 'C:\Program Files\Notepad++\notepad++.exe'
    [string]$AppDisplayName = 'Notepad++'
    [string]$AppParameters = ''
    [string]$AppWorkingDir = ''
    [string]$AppIconPath =  ''
    [string]$ManifestPath = $PSScriptRoot + '\NotepadPPManifest.txt'
    
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

```
2.	Once you have created your own application install packages, upload them to the Amazon S3 bucket created by the CloudFormation template.
3.	Navigate to the AWS Lambda console and select **Functions**.
4.	Choose the **AS2_Automation_Windows_FN02_Scripted_Install_########** function.
5.	In the **Code source** section, scroll down to the line 77 in the default script. The line of hash marks outlines the beginning and end of each application install section.
6.	Modify or replace the sections for the sample applications referencing your own packages in Amazon S3 or downloaded off the web.
7.	Once complete, click **Deploy** to make the updated code active for the next execution of the Lambda function.


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.

