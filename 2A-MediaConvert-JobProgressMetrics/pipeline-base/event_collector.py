#!/usr/bin/env python3.6
import boto3
import datetime
import json
import time
import decimal
from botocore.client import ClientError
from boto3 import resource
from boto3.dynamodb.conditions import Key
import logging
import subprocess
#import urllib
from urllib.parse import urlparse
import timecode
from timecode import Timecode
import xmltodict
import logging
import os
import traceback

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

KINESIS_CLIENT = boto3.client('kinesis')
DYNAMO_CLIENT = boto3.resource('dynamodb')

SIGNED_URL_EXPIRATION = 300

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)

def get_signed_url(expires_in, bucket, obj):
    """
    Generate a signed URL
    :param expires_in:  URL Expiration time in seconds
    :param bucket:
    :param obj:         S3 Key name
    :return:            Signed URL
    """
    s3_cli = boto3.client("s3")
    presigned_url = s3_cli.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': obj},
                                                  ExpiresIn=expires_in)
    return presigned_url

def jobMediaInfo(job):
    """

    :param job:
    """
    print('Mediainfo: job: ' + job['id'])

    # Loop through input videos in the job
    for input in job['settings']['inputs']:
        s3_path = input['fileInput']
        urlp = urlparse(s3_path)
        # Extract the Key and Bucket names for the inputs
        key = urlp[2]
        key = key.lstrip('/')
        bucket = urlp[1]
        
        signed_url = get_signed_url(SIGNED_URL_EXPIRATION, bucket, key)
        logger .info("Signed URL: {}".format(signed_url))
        
        print ("bucket and key "+bucket+" "+key)
        
        # Launch MediaInfo
        # Pass the signed URL of the uploaded asset to MediaInfo as an input
        # MediaInfo will extract the technical metadata from the asset
        # The extracted metadata will be outputted in XML format and
        # stored in the variable xml_output
        try:
            xml_output = subprocess.check_output(["./mediainfo", "--full", "--output=XML", signed_url])
            print(xml_output)
        except subprocess.CalledProcessError as e:
            print (e.output)
            
        json_output = xmltodict.parse(xml_output)
        
        input['mediainfo'] = json_output['Mediainfo']
        
        #print(json.dumps(json_output, indent=4, cls=DecimalEncoder))

    return True

def jobAnalyzeInputs(job):
    
    job['analysis'] = {}
    
    job['analysis']['frameCount'] = 0

    print('Analyze: job: ' + job['id'] )

    # number of inputs
    job['analysis']['num_inputs'] = len(job['settings']['inputs'])

    #number of outputs
    num_outputs = 0
    for og in job['settings']['outputGroups']:
        num_outputs += len(og['outputs'])
    job['analysis']['num_outputs'] = num_outputs

    # calculate total frames in inputs and job
    for input in job['settings']['inputs']:
       
        inputFPS = input['mediainfo']['File']['track'][0]['Frame_rate'][0]
        
        if 'InputClippings' in input:   
            for clip in input['InputClippings']:
                start_tc = timecode.Timecode(inputFPS, clip['StartTimecode'])
                end_tc = timecode.Timecode(inputFPS, clip['EndTimecode'])
                input_duration = end_tc - start_tc
                input['frameCount'] = int(input_duration.tc_frames())
                input['duration'] = input['frameCount'] * inputFPS
        else:

            input['frameCount'] = int(input['mediainfo']['File']['track'][0]['Frame_count'])
            input['duration'] = float(input['mediainfo']['File']['track'][0]['Duration'][0])

        job['analysis']['frameCount'] += input['frameCount']
        job['analysis']['codec'] = input['mediainfo']['File']['track'][0]['Video_Format_List']

def putProgressMetrics(job, timestamp, METRICSTREAM):
    """ 
    """
    for key, value in job['progressMetrics'].items():
        putJobMetric(job, timestamp, key, value, METRICSTREAM)
        
    return True

def putStatusMetrics(job, timestamp, status, METRICSTREAM):
    
    #if 'eventStatus' not in job:
    #    return

    for s in ['SUBMITTED', 'PROGRESSING', 'ERROR', 'COMPLETE']:
        if status == s:
            putJobMetric(job, timestamp, s, 1, METRICSTREAM)
        else:
            putJobMetric(job, timestamp, s, 0, METRICSTREAM)


# Store metrics in the same format as Cloudwatch in case we want to use
# Cloudwatch as a metrics store later
def getJobMetricDimensions(job):
    ret = {}
    dimensions = []
    filters = {}
    
    job_dim= {}
    job_dim['Name'] = 'jobId'
    job_dim['Value'] = job['id']
    dimensions.append(job_dim)

    filters['jobId'] = job['id']
    filters['account'] = job['queue'].split(':')[4]
    filters['region'] = job['queue'].split(':')[3]

    queue_dim = {}
    queue_dim['Name'] = 'queue'
    queue_dim['Value'] = job['queue']
    dimensions.append(queue_dim)
    
    filters['queue'] = job['queue']
    filters['queueName'] = job['queue'].split('/')[1]
    
    for key in job['userMetadata']:
        value = job['userMetadata'][key]
        dimension = {}
        dimension['Name'] = key 
        dimension['Value'] = value
        dimensions.append(dimension)

        filters[key] = value

        # doing this so we can index dyanmo records by filters - dynamo needs a 
        # top level objects as index keys.  No nesting.
        if key not in job:
            job[key] = value

    ret['dimensions'] = dimensions
    ret['filters'] = filters
    return ret

def putJobMetric(job, timestamp, metricname, value, METRICSTREAM):
    filters_dims = getJobMetricDimensions(job)
    dims = filters_dims['dimensions']

    metricdata = []        
    
    metric = {}
    metric['MetricName'] = metricname
    metric['Dimensions'] = dims
    metric['Timestamp'] = timestamp
    metric['Value'] = value
    metricdata.append(metric)
    
    #print("putJobMetric: name = "+metricname+" value = "+str(value))
    #CLOUDWATCH_CLIENT.put_metric_data(Namespace='COL/MediaConvert', MetricData = metricdata)

    # Add filters for downstream consumers such as elasticearch
    metric['filters'] = filters_dims['filters']

    response = KINESIS_CLIENT.put_record(
        StreamName=METRICSTREAM,
        Data=json.dumps(metric, cls=DecimalEncoder),
        PartitionKey=metric['MetricName']
    )
    print(json.dumps(metric, cls=DecimalEncoder))
    print(json.dumps(response, default=str))


def getMediaConvertJob(id, JOBTABLE):
    
    try:
        table = DYNAMO_CLIENT.Table(JOBTABLE)
        response = table.get_item(Key={'id': id}, ConsistentRead=True)
    
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        if 'Item' not in response:
            return None
        else:
            item = response['Item']
            print("GetItem succeeded:")
            #print(json.dumps(item, indent=4, cls=DecimalEncoder))
            return item

def calculateProgressMetrics(job):
    '''
    job has the most recent values for the based metrics and base durations from events.
    Calculate progress metrics.
    '''
    progressMetrics = {}

    # BASE TIMES FROM EVENTS
    # createTime = timestamp of CREATE event
    # firstProgressingTime  = timestamp of earliest PROGRESSING event
    # lastProgressingTime = timestamp of latest PROGRESSING event or COMPLETE event
    # lastStatusTime = timestamp of latest status update or COMPLETE event
    # completeTime = timestamp of COMPLETE event
    # lastTime = latest timestamp seen so far

    # BASE METRICS FROM EVENTS
    # framesDecoded = most recent STATUS event frames decoded or frame count if COMPLETE event
    # ['analysis'] frameCount = frame count from CREATE event
    if 'progressMetrics' in job and 'framesDecoded' in job['progressMetrics']:
        progressMetrics['framesDecoded'] = job['progressMetrics']['framesDecoded']

    if 'analysis' in job and 'frameCount' in job['analysis']:
        progressMetrics['frameCount'] = job['analysis']['frameCount']

    # CALCULATED METRICS

    # percentDecodeComplete = framesDecoded / frameCount * 100 
    # framesRemainging = frameCount - framesDecoded
    if 'framesDecoded' in progressMetrics:
        if 'analysis' in job and 'frameCount' in job['analysis']:
            
            progressMetrics['percentDecodeComplete'] \
                = job['progressMetrics']['framesDecoded'] / job['analysis']['frameCount'] * 100

            progressMetrics['framesRemaining'] \
                = job['analysis']['frameCount'] - job['progressMetrics']['framesDecoded']

    # queuedDuration = firstProgressingTime - createTime
    if 'firstProgressingTime' in job['eventTimes'] and 'createTime' in job['eventTimes']:
        progressMetrics['queuedDuration'] \
            = job['eventTimes']['firstProgressingTime'] - job['eventTimes']['createTime']

    # progressingDuration = lastProgressingTime  - firstProgressingTime
    if 'firstProgressingTime' in job['eventTimes'] and 'lastProgressingTime' in job['eventTimes']:
        progressMetrics['progressingDuration'] \
            = job['eventTimes']['lastProgressingTime'] - job['eventTimes']['firstProgressingTime'] 

    # statusDuration = lastStatusTime - firstProgressingTime
    if 'firstProgressingTime' in job['eventTimes'] and 'lastStatusTime' in job['eventTimes']:
        progressMetrics['statusDuration'] \
            = job['eventTimes']['lastStatusTime'] - job['eventTimes']['firstProgressingTime']
    
    # decodeDuration = decodeTime - firstProgressingTime
    if 'firstProgressingTime' in job['eventTimes'] and 'decodeTime' in job['eventTimes']:
        progressMetrics['decodeDuration'] \
            = job['eventTimes']['decodeTime'] - job['eventTimes']['firstProgressingTime']

    # decodeRate = framesDecoded / statusDuration 
    if 'framesDecoded' in progressMetrics and 'statusDuration' in progressMetrics:
        progressMetrics['decodeRate'] = progressMetrics['framesDecoded'] / progressMetrics['statusDuration']

    # estDecodeTimeRemaining = decodeRate * framesRemaining
    if 'decodeRate' in progressMetrics and progressMetrics['decodeRate'] > 0 and 'framesRemaining' in progressMetrics:
        progressMetrics['estDecodeTimeRemaining'] =  progressMetrics['framesRemaining'] / progressMetrics['decodeRate']
    
    return progressMetrics

def jobCreateEvent(event, JOBTABLE):
    """
    Process a job create event and return the updated job data.
    """
        
    #tsevent = int(datetime.datetime.strptime(event["time"], "%Y-%m-%dT%H:%M:%SZ").timestamp())
    job = event['detail']['responseElements']['job']
    event['detail']['status'] = job['status']
    tsevent = job['createdAt']
    job['queueName'] = job['queue'].split('/')[1]
    job['filters'] = getJobMetricDimensions(job)['filters']

    # analyze inputs
    jobMediaInfo(job)                   # Adds mediainfo to job
    jobAnalyzeInputs(job)               # Adds analysis to job
  
    storedJob = getMediaConvertJob(job['id'], JOBTABLE)

    # if we recieved any events out of order, we need to merge them in to the base job
    # info from the create event
    job['eventStatus'] = job['status']

    # This is the first event for this job
    if storedJob == None:
        job['eventTimes'] = {}
        job['eventTimes']['lastTime'] = tsevent
        job['eventTimes']['createTime'] = tsevent
    
    else:
        
        # save previously recorded event times
        job['eventTimes'] = storedJob['eventTimes']
        
        # add createTime
        job['eventTimes']['createTime'] = tsevent

        # update lastTime, if needed.  This would be weird to not already be set, though
        if tsevent > storedJob['eventTimes']['lastTime']:
            job['eventTimes']['lastTime'] = tsevent

        # merge job status
        if 'status' in storedJob:
            job['status'] = storedJob['status']
        
        if 'progressMetrics' not in job:
            job['progressMetrics'] = {}

        # if the job completed but we didn't have a framecount from the CREATE event, set it now
        if job['status'] == 'COMPLETE':
            job['progressMetrics']['framesDecoded'] = job['analysis']['frameCount']
            
        # merge in input details from stored job
        if 'inputDetails' in storedJob:
            job['inputDetails'] = storedJob['inputDetails'] 
    

    # New jobs that are not queued start in PROGRESSING status
    if job['status'] == 'PROGRESSING':
        job['eventTimes']['firstProgressingTime'] = tsevent

    # calculate progress metrics
    job['progressMetrics'] = calculateProgressMetrics(job)

    return job

def jobStateChangeEvent(event, JOBTABLE):
    
    progressMetrics = {}

    tsevent = int(datetime.datetime.strptime(event["time"], "%Y-%m-%dT%H:%M:%SZ").timestamp())
    jobId = event['detail']['jobId'] 
    storedJob = getMediaConvertJob(jobId, JOBTABLE)
    
    # This is the first event for this job
    if storedJob == None:
        job = {}
        
        job['userMetadata'] = event['detail']['userMetadata']
        job['queue'] = event['detail']['queue']  
        job['queueName'] = job['queue'].split('/')[1]
        job['eventTimes'] = {}
        job['eventTimes']['lastTime'] = tsevent
        job['progressMetrics'] = {}
        job['id'] = jobId

    else:
        job = storedJob

        if 'eventTimes' not in job:
            job['eventTimes'] = {}
    
        if 'progressMetrics' not in job:
            job['progressMetrics'] = {}
        
        if tsevent > job['eventTimes']['lastTime']:
            job['eventTimes']['lastTime'] = tsevent   

    if event['detail']['status'] == 'STATUS_UPDATE':    
    
        job['eventStatus'] = 'PROGRESSING'
        # framesDecoded = most recent STATUS event frames decoded or frame count if COMPLETE event
        if 'framesDecoded' not in job['progressMetrics'] \
                or event['detail']['framesDecoded'] > job['progressMetrics']['framesDecoded']: 
            job['progressMetrics']['framesDecoded'] = event['detail']['framesDecoded']
        
        # lastStatusTime = timestamp of latest status update or COMPLETE event
        if 'lastStatusTime' not in job['eventTimes'] or tsevent >  job['eventTimes']['lastStatusTime']:
            job['eventTimes']['lastStatusTime'] = tsevent

        job['progressMetrics'] = calculateProgressMetrics(job)
        #putProgressMetrics(job, job['eventTimes']['lastTime'])

        # progress is measured based on decoding time.  save the duration of decode so
        # we can use it to come up with a formula to pad the time for tail of job
        # after decdoe is complete.
        if 'percentDecodeComplete' in job['progressMetrics'] and job['progressMetrics']['percentDecodeComplete'] == 100:
            if 'decodeTime' not in job['eventTimes']:
                    job['eventTimes']['decodeTime'] = tsevent
        
    elif event['detail']['status'] == 'PROGRESSING':
        
        job['eventStatus'] = 'PROGRESSING'

        if 'status' not in job or job['status'] == 'SUBMITTED':
                    
            job['status'] = 'PROGRESSING'
            job['eventTimes']['firstProgressingTime'] = tsevent
            job['eventTimes']['lastProgressingTime'] = tsevent

        elif job['status'] == ['PROGRESSING']:

            # lastProgressingTime = timestamp of latest PROGRESSING event or COMPLETE event
            if 'lastProgressingTime' not in job['eventTimes']  \
                or job['eventTimes']['lastProgressingTime'] < tsevent:
                    
                job['eventTimes']['lastProgressingTime'] = tsevent
            
            # firstProgressingTime  = timestamp of earliest PROGRESSING event
            if 'firstProgressingTime' not in job['eventTimes']  \
                or job['eventTimes']['firstProgressingTime'] > tsevent:
                    job['firstProgressingTime'] = tsevent
        
        job['progressMetrics'] = calculateProgressMetrics(job)
   
    elif event['detail']['status'] == 'INPUT_INFORMATION':
            
        job['inputDetails'] = event['detail']['inputDetails']
        
    elif event['detail']['status'] == 'COMPLETE':

        job['eventStatus'] = 'COMPLETE'

        job['status'] = 'COMPLETE'
        
        # lastTime = latest timestamp seen so far
        job['eventTimes']['lastTime'] = tsevent

        # completeTime = timestamp of COMPLETE event
        job['eventTimes']['completeTime'] = tsevent
        
        # lastProgressingTime = timestamp of latest PROGRESSING event or COMPLETE event
        job['eventTimes']['lastProgressingTime'] = tsevent
        
        # lastStatusTime = timestamp of latest status update or COMPLETE event
        job['eventTimes']['lastStatusTime'] = tsevent

        # framesDecoded = most recent STATUS event frames decoded or frame count if COMPLETE event
        if 'analysis' in job and job['status'] == 'COMPLETE':
            job['progressMetrics']['framesDecoded'] = job['analysis']['frameCount']

        job['progressMetrics'] = calculateProgressMetrics(job)

    elif event['detail']['status'] == 'ERROR':

        job['eventStatus'] = 'ERROR'
        job['status'] = 'ERROR'
        
        # lastTime = latest timestamp seen so far
        job['eventTimes']['lastTime'] = tsevent

        # completeTime = timestamp of COMPLETE event
        job['eventTimes']['errorTime'] = tsevent

        job['progressMetrics'] = calculateProgressMetrics(job)
    
    return job

def lambda_handler(event, context): 
    """
    Event collector for mediaconvert event type.  Events are cleaned to ensure they
    have the minimum consistent schema.  The collector maintains a persistent job object 
    that it updates as events occur.  Since events may arrive out of order from the 
    time they are generated, we need to be careful about overwriting newer infomration
    with older information.

    Each event should carry at least these key value pairs:
    
    'MediaConvertCollecterEvent': { 
    'time': timestamp,
    'detail': {
        'eventName': 'MediaConvert Job State Change'
        'status': '[SUBMITTED, PROGRESSING, INPUT_INFORMATION,STATUS_UPDATE, COMPLETE, ERROR]',
        'jobId': 'jobId',
        'queue': `queue ARN`,
        'userMetadata': {'key1': 'value1', ...}
        } 
    }
    """
    print(json.dumps(event))

    job = {}
    tsevent = int(datetime.datetime.strptime(event["time"], "%Y-%m-%dT%H:%M:%SZ").timestamp())
    
    try:
        # Get environment variables set on the CloudFormation stack
        JOBTABLE = os.environ['JobTable']
        JOBTABLETTL = os.environ['JobTableTTL']
        JOBSTREAM = os.environ['JobStream']
        EVENTTABLE = os.environ['EventTable']
        EVENTTABLETTL = os.environ['EventTableTTL']
        EVENTSTREAM = os.environ['EventStream']
        METRICSTREAM = os.environ['MetricStream']
        USESTREAMS = os.environ['UseStreams']
        
        JOB_RETENTION_PERIOD = (3600 * 24 * int(JOBTABLETTL))
        EVENT_RETENTION_PERIOD = (3600 * 24 * int(EVENTTABLETTL))
        
        if event['detail-type'] == 'AWS API Call via CloudTrail' and event['detail']['eventName']== "CreateJob":
            job = jobCreateEvent(event, JOBTABLE)
        elif event['detail-type'] == 'MediaConvert Job State Change': 
            job = jobStateChangeEvent(event, JOBTABLE)
        else:
            print ("Unrecognized event! "+event['detail-type'])
            return False

        # Update job table with new version of job object
        job["timestamp"] = job['eventTimes']['lastTime']
        job["timestampTTL"] = tsevent + JOB_RETENTION_PERIOD
        s = json.dumps(job, cls=DecimalEncoder)
        job = json.loads(s, parse_float=decimal.Decimal)
        table = DYNAMO_CLIENT.Table(JOBTABLE)
        response = table.put_item(Item = job)
        print(json.dumps(response, cls=DecimalEncoder))

        # add expirtation timestamp for dynamo and save the event in dynamo
        event["timestamp"] = tsevent
        event["testTime"] = tsevent
        event["timestampTTL"] = tsevent + EVENT_RETENTION_PERIOD
        # add jobId to top level of object to use as a Dyanmo key
        event["jobId"] = job["id"]
        s = json.dumps(event, cls=DecimalEncoder)
        event = json.loads(s, parse_float=decimal.Decimal)
        table = DYNAMO_CLIENT.Table(EVENTTABLE)
        response = table.put_item(Item = event)
        print(json.dumps(response, cls=DecimalEncoder))

        # PIPELINE
        # push job to kinesis
        print("Push Job to Kinesis")
        #print(json.dumps(job, cls=DecimalEncoder))
        response = KINESIS_CLIENT.put_record(
            StreamName=JOBSTREAM,
            Data=json.dumps(job, cls=DecimalEncoder),
            PartitionKey=job["id"]
        )
        print(json.dumps(response, default=str))

        # push event to kinesis
        response = KINESIS_CLIENT.put_record(
            StreamName=EVENTSTREAM,
            Data=json.dumps(event, cls=DecimalEncoder),
            PartitionKey=event["id"]
        )
        print(json.dumps(response, default=str))

        # Progress metrics use the most recent event time we've seen since
        # metrics are calculated by data from multiple events.
        # Status metrics are based on this event only
        putProgressMetrics(job, job['eventTimes']['lastTime'], METRICSTREAM)
        putStatusMetrics(job, tsevent, job['eventStatus'], METRICSTREAM)
        
    except Exception as e:
        print('An error occured {}'.format(e))
        traceback.print_stack()
        raise
    else:
        return True