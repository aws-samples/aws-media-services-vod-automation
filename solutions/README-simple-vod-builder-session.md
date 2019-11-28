## Spinning up the Video On-Demand on AWS CloudFormation stack

1. Log in to your AWS account
2. Go to https://aws.amazon.com/solutions/video-on-demand-on-aws/
3. Click on the **Launch the solution in the AWS console** button
4. Click next to go to the **Stack details** page
5. Fill in the **stack name **
6. Fill in the **Notification email address** with an email you can access during the lab
7. Change the **Enable MediaPackage** parameter to `true`
8. Use the defaults for the rest of the parameters
9. Click the next button to reach the **Review** page
10. Check the box that says "I acknowledge that AWS CloudFormation might create IAM resources."
11. Click on the **Create stack** button

## Execute the VOD on AWS Workflow

1. Check your email for a message with the subject **AWS Notification - Subscription Confirmation**. 
2. Open the email and click on the link to confirm subscription.
3. Open the AWS CloudFormation console and find the stack you deployed at the start of the session
4. Open the **Outputs** tab and find the name of bucket in the **Source** output.  
5. Open that bucket in the S3 console.
6. Download the sample video to your computer: https://tinyurl.com/vodllama
7. Upload the sample video to the Source bucket
8. This will trigger the VOD on AWS Workflow!
9. You should receive a series of emails notifying you of the progress of the workflow

## Play the HLS output in JW Player

1. Open the email notification that has the subject that starts with "Workflow Status:: Complete::"
2. Copy the link to the HLS output from the email 
3. Open the JW Player Stream tester: https://www.jwplayer.com/developers/stream-tester/
4. Copy the link to the **File Url** form field
5. Scroll down and click on the **Test Stream** button to play the video
6. Use the settings (gear icon) to view the HLS bitrate ladder available to the player.  You should see many more levels than the previous video we created using the console.
7. Now force the player to play the lowest and highest bitrate videos by selecting them from the settings.  
8. What do you notice?

## Walk though the VOD on AWS Workflow

### S3

1. Open the Source S3 bucket
2. Open the **Properties** tab, scroll down to **Advanced Settings** and click on the **Events** card
3. You will see a list of triggers for different file extensions
4. Click the radio button for the .mp4 trigger and click **Edit** to view the configuration
5. The trigger is configured for `All object create events` and invokes the Lambda function called `<stack-name>`-step-functions

### step-functions Lambda

This Lambda is used to invoke a step function for each of the three stages of the workflow: Ingest, Process, and Publish

1. The code for the step-functions lambda is located on GitHub in the video-on-demand-on-aws project: https://github.com/awslabs/video-on-demand-on-aws/blob/master/source/step-functions/index.js
   

### Ingest Step Function

This step functions analyzes the input and intitates the workflow

1. Open the Step Functions console.
2. Find the `<stack-name>`-ingest Step Function
3. Open the most recent execution to view the visual workflow
4. View the inputs, outputs for the functions and the tasks in the state machine
5. The last step of the workflow will invoke the **step-functions Lambda** to initiate the Process stage of the workflow

### Process Step Function

The process step function triggers a backgroud MediaConvert job based on the input analysis and configuration of the VOD on AWS Stack.  The job is monitored using a CloudWatch event that will trigger the **step-functions** lambda when MediaConvert emits a JOB COMPLETE event.

1. Open the Step Functions console.
2. Find the `<stack-name>`-process Step Function
3. Open the most recent execution to view the visual workflow
4. View the inputs, outputs for the functions and the tasks in the state machine
5. The **Encode Job Submit** task invoked the `<stack-name>`-encode lambda
6. The code is located on GitHub in the video-on-demand-on-aws project: https://github.com/awslabs/video-on-demand-on-aws/blob/master/source/encode/index.js
7. Notice that this lambda constructs a MediaConvert job and calls the MediaConvert Node.js API.

#### MediaConvert

1. Open the MediaConvert console
2. Find the most recent job for the input you uploaded in the **Jobs** page
3. Click on the link in the **Job ID** column to view the job
4. Click on the **Job Details** button to view the details of the job configuration.
5. Notice this job has MP4 outputs and an HLS stack with many more levels in the bitrate ladder than the one we created in the console.
6. Compare the MediaConvert job outputs to the email you recieved from the workflow.  Notice the email list outputs for HLS, MSS, CMAF and DASH, but MediaConvert only has HLS.  The MSS, CMAF and DASH are created later in the workflow during the Publish phase.

### Publish Step Function

The publish step functions invokes MediaPackage to create a new asset based on the pacakging group defined by the VOD on AWS stack.  This packaging group repackages the MediaConvert HLS output into DASH, MSS, and CMAF outputs.  This lambda also sends a notification that the job is complete.

#### MediaPackage

1. Open the MediaPackage console
2. Click on the **Packaging Groups** menu
3. The `<stack-name>`-packaging-group defines the packages that will be created for each asset created by the workflow
4. Click on the **Assets** menu.  There should be one asset created for each HLS group output by MediaConvert

### CloudFront

CloudFront is serving to purposes in this workflow.  It is bringing the video data closer to viewers by caching the videos at the edge and it is provding read access control to the video using an Origin Access Identitiy.

1. Take a look at the domain for the video outputs from the Job Complete email.  Notice that the origin is CloudFront rather than S3 or MediaPackage.
2. Open the CloudFront console.
3. Find the CloudFront distribuion whose Origin is has a bucet name that starts with **`<stack-name>`-destination**  
4. Click on the link in the **ID** column 
5. Navigate to the **Origins** tab and note that there are two origins configured: one for S3 and one for MediaPackage.



