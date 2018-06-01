# VOD Automation Toolkit

This project contains workflow examples for automating Video On Demand (VOD) workflows on AWS.  These are code samples to get you started on common tasks rather than an end to end architecture suitable for production.  We will prefer simple, easy to understand examples that are appropriate to answer the "How do I ...?" kind of questions someone might find on  the AWS Forums.

The building blocks here are organized into sample workflows such as workload monitoring, content analytics, and video quality checks. 

## Workflows 

Workflows are independent of one another unless noted in the **Prerequisite** section of the workflow README file.

1. **Video ingest and conversion basics** 
    *  **[(A) MediaConvert watchfolder with SNS notifications (tutorial and CloudFormation):](./1A-MediaConvert-WatchfolderAndNotification/README.md)** Automatically trigger video transcoding when a video is added to an S3 bucket.  This workflow also has a [companion tutorial](./1A-MediaConvert-WatchfolderAndNotification/README-tutorial.md) to step through creating resources in the console.
    * **[(B) MediaConvert events (tutorial and CloudFormation)](./1B-MediaConvert-events/README-tutorial.md)** Collect and store MediaConvert CloudWatch events using Lambda and Dynamodb
    
2. **Video conversion job metrics and monitoring**
    * **[(A) MediaConvert job progress metrics](./2A-MediaConvert-JobProgressMetrics/README.md)** Analyze and track the progress of MediaConvert jobs. Calculate new metrics about in-progress jobs from MediaConvert CloudWatch events.
    * **[(B) Monitoring MediaConvert workloads](./2B-MediaConvert-workload-monitoring/README.md)** Track and visualize MediaConvert workloads over time using CloudWatch events, Kinesis Streams, Kinesis Firehose and Elasticsearch
3. Video analysis
    *  **[(A) Analyze MediaConvert inputs using MediaInfo (tutorial and CloudFormation)](./1C-MediaConvert-mediainfo/README-tutorial.md)** Collect and store mediainfo output whenever MediaConvert INPUT_INFORMATION CloudWatch events occur using Lambda and Dynamodb




