# MediaConvert Job Progress Metrics  

This sample code and cloudformation shows how to build an serverless workflow that keeps track of the progress of MediaConvert jobs in an AWS region using event data and exposes the data using an API. You can add this to any region where you want to monitor the progress of MediaConvert jobs.

Video delivery workflows use MediaConvert to transcode source videos into formats that ensure high quality playback on all of the devices and platforms needed to reach target viewers.  Video ingest can be automated using various techniques such as watchfolders, web applications or batch processing.  As with any application, observability is key to successful operation of video ingest workflows. Monitoring jobs that are created asyncronously is a task that is common to most automation scenarios.  The MediaConvert Job Progress Metrics Workflow keeps track of your jobs using [AWS Lambda](https://aws.amazon.com/lambda/), [Amazon CloudWatch Events](https://aws.amazon.com/cloudwatch) and [Amazon API Gateway](https://aws.amazon.com/api-gateway).  We'll use [Chalice](https://github.com/aws/chalice) to quickly create API APIs.  Chalice is a python serverless microframework for AWS. It allows you to quickly create and deploy applications that use Amazon API Gateway and AWS Lambda.  We'll also use [mediainfo](https://mediaarea.net/en/MediaInfo), an open source video package analysis tool, to enhance the metadata provided by the MediaConvert events.

The workflow will create the following API endpoints:

**/jobs/\<status\>**
    
* List progress metrics for all jobs with the specified status.
  
**/jobs/\<JobId\>**

* List progress metrics the jobs with the specified MediaConvert JobId


This repository contains sample code for the Lambda functions depicted in the diagram as well as an [AWS CloudFormation](https://aws.amazon.com/cloudformation/) template for creating the function and related resources.

There is a companion tutorial on capturing and storing MediaConvert event data in [FIXME](./README-tutorial.md) for creating a simliar workflow using the AWS console.  Use the tutorial to go in depth on how the workflow is built and configured.

![screenshot for instruction](../images/ProgressMetricsSlide.png)



## Walkthrough of the Workflow
1. The Ingest user uploads a video to the WatchFolder bucket /inputs folder in S3.  Only files added to the /inputs folder will trigger the workflow.

2. The s3:PutItem event triggers a Lambda function that calls MediaConvert to convert the videos.

3. Converted videos are stored in S3 by MediaConvert.

4. When the conversion job finishes MediaConvert emits aws:mediaconvert _Job State Change Event_ type CloudWatch events with the job status.

5. The COMPLETE and ERROR status events trigger SNS to send notifications to subscribers.

## Running the Example

### Launching the Stack on AWS

The backend infrastructure can be deployed in US West - Oregon (us-west-2) using the provided CloudFormation template.
Click **Launch Stack** to launch the template in the US West - Oregon (us-west-2) region in your account:

A CloudFormation template is provided for this module in the file `WatchFolder.yaml` to build the workflow automatically. Click **Launch Stack** to launch the template in your account in the region of your choice : 

Region| Launch
------|-----
US East (N. Virginia) | [![Launch in us-east-1](http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/images/cloudformation-launch-stack-button.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=emc-watchfolder&templateURL=https://s3.amazonaws.com/rodeolabz-us-east-1/vodtk/1a-mediaconvert-watchfolder/WatchFolder.yaml)
US West (Oregon) | [![Launch in us-west-2](http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/images/cloudformation-launch-stack-button.png)](https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/new?stackName=emc-watchfolder&templateURL=https://s3.amazonaws.com/rodeolabz-us-west-2/vodtk/1a-mediaconvert-watchfolder/WatchFolder.yaml)

1. Make sure to enter an e-mail address to use for workflow notifications in the workflow input form.

(On the last page of the wizard, make sure to:

2. Click the checkboxes to give AWS CloudFormation permission to **"create IAM resources"** and **"create IAM resources with custom names"**
1. Click **"Execute"**
)

The information about the resources created is in the **Outputs** tab of the stack.  Save this in a browser tab so you can use it later when you create other stacks and MediaConvert jobs.

![outputs](../images/cf-watchfolder-stack.png)

## Testing the Example
  
You can use your own video or use the test.mp4 video included in this folder to test the workflow.  

1. Open the S3 console overview page for the watchfolder S3 bucket you created earlier.
2. Click on **+ Create folder** and enter `inputs` as the folder name and click **Save**
3. Click on the **inputs** folder link to open it.
1. Select **Upload** and then choose the file `test.mp4` from the directory for this lab module on your computer.
1. Note the time that the upload completed.
1. Open the MediaConvert jobs page and find a job for the input 'test.mp4' that was started near the time your upload completed.  

    ![Lambda trigger configuration screenshot](../images/verify-watchfolder.png)

1. Click on the jobId link to open the job details page.
2. Click on the link for the MP4 or HLS output (depending on what is supported by your browser).  This will take you to the S3 folder where your output is located.
3. Click on the ouput object link.
4. Play the test video by clicking on the S3 object http resource listed under the **Link** label.

    ![test video](../images/play-test-video.png)

5. Check the email you used to setup the workflow.  You should have a message similar to the one below.  The link should take you to the same job details page you found manually in the previous steps:

    ![sns email](../images/sns-email.png)

## Cleaning Up the Stack Resources

To remove all resources created by this example, do the following:

1. Delete the video files in the WatchFolder and MediaBucket S3 buckets.
2. Delete the CloudFormation stack.
1. Delete the CloudWatch log groups associated with each Lambda function created by the CloudFormation stack.

## Adapting this workflow 

### Restricting the source application metrics are collected from
It's easy to create outputs with other formats supported by MediaConvert.  MediaConvert job settings can be placed in JSON files in the WatchFolder S3 bucket /jobs folder.  The workflow will run a job for each settings file.  If no setting are specified, then the Default job included in this project will run.

## CloudFormation Template Resources
The following sections explain all of the resources created by the CloudFormation template provided with this example.

### CloudWatch Events
  
- **NotifyEventRule** - Notification rule that matches MediaConvert COMPLETE and ERROR events created from this workflow.  The rule uses userMetadata.application JSON values that are set when a MediaConvert job is created to identify jobs from this workflow.  We are using the name of the stack as the value of the userMetadata.application (see code in [convert.py](./convert.py)).  The target of the rule is the NotificationSns SNS Topic.  An InputTransformer is applied by the rule to format the information in the event before it passes on the messages to the target.

### IAM
- **MediaConvertRole** - A role that is passed to MediaConvert Python SDK via the API.  MediaConvert used this role to obtain access the the account resources needed to complete a conversion job.

- **LambdaRole** - an IAM role with policies to allow LambdaConvert to invoke the MediaConvert service, pass the MediaConvert role and access the WatchFolder bucket to look for user defined job inputs.

### Lambda
- **EventCollectorLambda** a lambda function triggered for any MediaConvert event.  It updates the current state of the MediaConvert objects in Dynamodb, calculates current metrics based on data in the event, performs analysis on the input media and passes all resulting data into the Kinesis data stream.


### S3

- **WatchFolder** - S3 bucket used to store inputs and optional job settings to the conversion workflow.  The NotificationConfiguration sets up the lambda trigger whenever an object is uploaded to the **/inputs** folder.  MediaCOnvert job settings JSON files can be place in the **/jobs** folder.  The workflow will run a job for each settings file it finds there. The bucket is set to expire objects that are more than 7 days old.  This setting is useful for testing, but can be removed, if needed.

- **MediaBucket** - S3 bucket used to store outputs of the conversion workflow.  Cross Origin Resource sharing is enabled to allow the videos to be played out from websites and browsers.  The bucket is set to expire objects that are more than 7 days old.  This setting is useful for testing, but can be removed, if needed.

- **MediaBucketPolicy** - Sets policy for MediaBucket to public read for testing.
  

## Additional resources

[AWS Video On Demand with MediaConvert Workshop](https://github.com/aws-samples/aws-media-services-simple-vod-workflow/blob/master/README.md) - use the MediaConvert console to develop video conversion jobs for adaptive bitrate and file-based delivery.  Includes adding captions, clipping and stitching and watermarking.

[Video on Demand on AWS](https://aws.amazon.com/answers/media-entertainment/video-on-demand-on-aws/) - a well-architected reference architecture that you can use to get started on production workflows.  Video on Demand on AWS has a similar workflow to this sample, but adds Step Functions to orchestrate the workflow, a Cloudfront distribution to deliver efficiently at the edge, and a backend data store to keep track of the status and history of the ingested videos.  

## License

This sample is licensed under Apache 2.0.# Base MediaConvert Data Pipeline

This section sets up resources for a base data pipeline that can be used to process data from media service workflows.  

![BasePipeline Image](../../images/MediaConvertBasePipeline.png)

The basic pipeline consists of:



Lambda Configuration Options:
* UseStreams indicates whether or not to write data to a Kinesis data steam.

**Dynamodb Tables** contain the current state of MediaConvert objects including:

* Events 
* Jobs 
* Queues
* Data Pipeline Configuration

Table configuration options:
* Time to Live (tableTTL) the amount of time that data will live in the Dynamodb tables.  1-N days, default=1 

**Kinesis Data Stream** each data type that is collected is placed in a stream that is available to downstream consumers.  This provides a flexible data interface that can support multiple consumer workflows and can be esily modified without disrupting other workflows.

Stream configuration options:
* Time to Live (streamTTL) the amount of time that stream data is available for downstream consumers. 1-N days, default=1
* Buffer interval - max time to buffer data before flushing the stream

### Pipeline Latency

The latency of the data pipeline will be determined by the Stream configuration with a max set by the Buffer interval

## Prerequisites

Administrator account access or an IAM User with the profile included in this section in [base-data-pipeline-IAM.yaml](base-data-pipeline-IAM.yaml).

### Region

MediaConvert is available in several regions. But for the purpose of this lab, we will use the **US East (N. Virginia)** region.

### Deploy the stack

1. Make sure your region is set to US-East (N. Virgina).
1. From the AWS Management Console, click on **Services** and then select **CloudFormation**.
1. Select **Create stack** to go to the **Create stack** page
1. Select the **Upload a template to Amazon S3** checkbox then select **Choose file**
1. Navigate to the directory where you downloaded this repository and select **base-data-pipeline.yaml**
1. select **Open**.
1. Select **Next** to move to the **Specify details** page.
1. Enter `pipe` for the in the **Stack name** box.  Note: you can choose other stack names, but using "pipe" will create resource with names consistent with the rest of the lab.
1. Select **Next** to move to the **Options** page.  Leave this page as defaults.
1. Select **Next** to move to the **Review** page.
1. Select the checkbox to acknowledge creating resources, then select **Create**
1. Wait for the stack to be created.
1. From the Stacks page, find the Stack called **pipe**.
1. Go to the Stack details page and expand the Outputs section of the page.  You will find the following outputs there:
    
    * FIXME

1. Save this page in a browser tab or save the info to be used as you build out this stack.