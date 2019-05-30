# Monitoring MediaConvert Workloads using CloudWatch Events, Kinesis, and Elasticsearch

Observability is key to effectivily operating any workflow on AWS.  Workload monitoring helps to understand the characteristics of the load we are putting on a system over time.  This information can be useful for resolving problems, analyzing costs and for understanding how to make workflows more efficient.  In [VOD Automation Part 2: MediaConvert Job Progress Metrics](../MediaConvert-JobProgressMetrics/README.md), we kept track of the progress of MediaConvert jobs over time and exposed it as an API that could be called from web applications.  In this module, we'll be using the same data, but we'll be combining the data from all of our jobs to provide information about our transcoding workload as a whole. We'll use [Kinesis Firehose](https://aws.amazon.com/kinesis/data-firehose/) to consume job progress metrics from a stream and Elasticsearch and Kibana to search and aggregate the data and visualize our workloads.  Kinesis Firehose simplifies the configuration of setting up data pipelines to common data stores on AWS, such as Elasticsearch.  Elasticsearch provides both search and timeseries analysis capabilities that useful for ad-hoc analysis of semi-structured data and for creating dashboards.  Finally, Kibana, which is packaged with Elasticsearch is used for data visualization.

![FIXME stack](../images/MonitoringSlide.png)


In this architecture, we set up a data pipeline where the [MediaConvert Job Progress Metrics](../MediaConvert-JobProgressMetrics/README.md) stack from the previous module is the _producer_ and the Elasticsearch stack is the _consumer_.

Once the stack is in place we can use the provided dashboard to visualize the MediaConvert workload for a specific region.

The dashboard is a just an example with what can be done with this data.  Use Kibana to explore the data and experiment to provide information that is useful to you.

# Stack Resources

* **MediaConvert Progress Metrics stack:** We'll use the data produced from the Job Progress Metrics stack.

* **Kinesis Firehose:** A Kinesis firehose is created for each kind of data that is collected in the progress stack: events, jobs and metrics.  The firehose is configured to deliver data to an Elasticsearch instance.  The firehose is also configured to deliver data to S3 if delivery to Elasticsearch fails. 

* **Elasticsearch:** Elasticsearch is used to perform filtering, timeseries analysis and aggregation of job data so we can view information about our workload.  

* **Elasticsearch Index Custom Resources:** Custom resources are included in the stack to create index mappings for each of the data types generated from the Progress Metrics stack: events, jobs and metrics.


## Costs

This sample uses AWS services that do not provide a free tier.  These include Kinesis, Kinesis Firehose and Elasticsearch.  The billing will depend on the amount of data that is present in your pipeline.  The amount of data will vary depending on your MediaConvert workload.

# Running the example

## Prerequisites

1. You'll need to deploy the the progress monitoring stack in [MediaConvert-JobProgressMetrics](../MediaConvert-JobProgressMetrics/README.md) that will be the producer of the data in our pipeline.  You will not need the progress REST API, so you can skip that step if you want.

2. MediaConvert workload: This workflow monitors the existing MediaConvert workloads in your account.  If you do not have any MediaConvert jobs running, there will be no data in the dashboard.

## Securing Kibana

The MediaConvert job data exposed in this stack includes the account id it is running in. 

The stack uses an [ip-based policy](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/es-ac.html#es-ac-types-ip) to grant access to Elaticsearch resources.  This grants access to the Elasticsearch APIs and Kibana, but only through the IP/IP range you provide to the stack when it is deployed.  See the the **ESDomain** logical resource in [pipeline-es.yaml](pipeline-es/pipeline-es.yaml) to view the policy. 

See the following resources for other methods of setting up access to Kibana HTTP resources:

* [How to Control Access to Your Amazon Elasticsearch Service Domain](https://aws.amazon.com/blogs/security/how-to-control-access-to-your-amazon-elasticsearch-service-domain/) 
* [Amazon Cognito Authentication for Kibana](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/es-cognito-auth.html)
* [Controlling access to Kibana and Logstash](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/es-kibana.html#es-kibana-proxy)


## Deploy the stack 

 To get started right away just launch the stack using the button below.
 
 Fill in the input parameters for the stack using the outputs from the `pipeline` stack you created previously.

Region| Launch
------|-----
us-east-1 (N. Virginia) | [![Launch in us-east-1](http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/images/cloudformation-launch-stack-button.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=pipeline&templateURL=https://s3.amazonaws.com/rodeolabz-us-east-1/vodtk/3-mediaconvert-workload-monitoring/pipeline-es/pipeline-es.yaml)
us-west-2 (Oregon) | [![Launch in us-west-2](http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/images/cloudformation-launch-stack-button.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=pipeline&templateURL=https://s3.amazonaws.com/rodeolabz-us-west-2/vodtk/3-mediaconvert-workload-monitoring/pipeline-es/pipeline-es.yaml)



## Run MediaConvert Jobs

* After the stack is completely deployed, run several jobs so as to generate data to propagate to Elasticsearch. Creating indices below will fail if there's no data present.

* If you will be using the sample dashboard provided in the tutorial, the `workflow` keyword is expected to be present in the job user metadata. Make sure to provide one, otherwise, some of the visualizations may not load properly.

## Configure Kibana

1. Use the link in the KibanaUrl stack output to open the Kibana console created by your stack.  

3. You should end up on a page that looks like this:

    ![Kibana](../images/Kibana.png)

### Create index patterns for event, job and metric data

4. You'll need to configure an index pattern for Jobs, Metrics and Events so we can visualize them in Kibana.
5. For the Events index type `eventindex-*` in the **Index name or pattern** box.
6. Select `time` as the **Time Filter field name**.
7. Click on the **Create button**
8. Select the **Create Index Pattern** button to create another index pattern
7. Type `jobindex-*` in the **Index name or pattern** box.
6. Select `createdAt` as the **Time Filter field name**. 
7. Click on the **Create button**
8. Select the **Create Index Pattern** button to create another index pattern
7. Type `metricindex-*` in the **Index name or pattern** box.
6. Select `Timestamp` as the **Time Filter field name**. 
7. Click on the **Create button**

### Import the sample dashboard

1. Select the **Management** tab from the Kibana side bar menu.
2. Select **Saved Objects** from the top of the panel
3. In the Saved Objects page, select the **Import** button.
4. In your repo, navigate to this directory `/3-MediaConvert-JobWorkloadMonitoring/pipeline-es/dashboards` and select the file [workload-dashboard.json](dashboards/workload-dashboard.json)
5. Select **Open** and accept the warning message about overwritting duplicate objects.

    ![kibana saved objects](../images/kibana-saved-objects.png)

6. Open the imported dashboard by selecting **Dashboard** from the Kibana sidebar menu.  Select the dashboard `MediaConvert Workload(last 1 hour)` from the list.

    ![kibana dashboard](../images/kibana-dashboard.png)

7. You may need to adjust the time picker in the upper right corner to select the last hour of data.  Click on the timepicker and select the **Quick** menu.  Then select **Last 1 hour** from the choices presented.

    ![timepicker](../images/kibana-timepicker.png)


NOTE: the appearance of the dashboard may be slightly different than the one shown here.  It depends on the workload running in your account and region where the stack is deployed.  There should be one row of graphs for each MediaConvert queue that has active MediaConvert jobs in the past hour.  There should also be a table at the bottom of the page with job details for the last hour.  The dashboard in the example shows an account with 2 MediaConvert queues.
