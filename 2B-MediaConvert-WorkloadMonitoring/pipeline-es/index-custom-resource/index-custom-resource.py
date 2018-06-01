#!/usr/bin/env python3.6
import boto3
import datetime
import json
import time
import decimal
from boto3 import resource
import logging
import os
import traceback
import elasticsearch
from elasticsearch import Elasticsearch
import http.client
from botocore.vendored import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

job_index_template = '''
{
    "template": "jobindex*",
    "settings": {"number_of_shards": 1 },
      "mappings": {
        "JobMapping": {
          "properties": {
            "analysis": {
              "properties": {
                "frameCount": {
                  "type": "long"
                }
              }
            },
            "createdAt": {
              "type": "date",
              "format":"epoch_second"
            },
            "eventStatus": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "eventTimes": {
              "properties": {
                "completeTime": {
                  "type": "date",
                  "format":"epoch_second"
                },
                "createTime": {
                  "type": "date",
                  "format":"epoch_second"
                },
                "decodeTime": {
                  "type": "date",
                  "format":"epoch_second"
                },
                "firstProgressingTime": {
                  "type": "date",
                  "format":"epoch_second"
                },
                "lastProgressingTime": {
                  "type": "date",
                  "format":"epoch_second"
                },
                "lastStatusTime": {
                  "type": "date",
                  "format":"epoch_second"
                },
                "EncodeTime": {
                    "type": "date",
                    "format":"epoch_second"
                  },
                "lastTime": {
                  "type": "date",
                  "format":"epoch_second"
                }
              }
            },
            "timestampTTL": {
              "type": "date",
              "format":"epoch_second"
            },
            "queue": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "timing": {
              "properties": {
                "submitTime": {
                  "type": "date",
                  "format":"epoch_second"
                }
              }
            }
          }
        }
      }
    }
}'''

metric_index_template = '''
{
  "template": "metricindex*",
  "settings": {
    "number_of_shards": 1
  },
  "mappings": {
    "MetricMapping": {
      "_source": {
        "enabled": true
      },
      "properties": { 
        "MetricName":    { "type": "text"  }, 
        "Timestamp":  {
          "type":   "date", 
          "format": "epoch_second||epoch_millis"
        }
      }
    }
  }
}
'''

def lambda_handler(event, context):
    '''
    lambda handler to create index templates 
    '''    
    status = True
    host = os.environ['ElasticsearchEndpoint']

    logger.info('REQUEST RECEIVED:\n {}'.format(event))
    logger.info('REQUEST RECEIVED:\n {}'.format(context))
    
    try:   
        if event['RequestType'] == 'Create':
            logger.info('CREATE!')
            es = Elasticsearch([host], verify_certs=True)
            result = es.indices.put_template(name='jobtemplate', body=job_index_template)
            status1 = result.get('acknowledged', False)
            result = es.indices.put_template(name='metrictemplate', body=metric_index_template)
            status2 = result.get('acknowledged', False)
            if (status1 == False or status2 == False):
                send(event, context, "FAILED", { "Message": "Resource creation failed!" }, None)
            else:
                send(event, context, "SUCCESS", { "Message": "Resource creation successful!" }, None)
        elif event['RequestType'] == 'Update':
            logger.info('UPDATE!')
            send(event, context, "SUCCESS", { "Message": "Resource update successful!" }, None)
        elif event['RequestType'] == 'Delete':
            logger.info('DELETE!')
            send(event, context, "SUCCESS", { "Message": "Resource deletion successful!" }, None)
        else:
            logger.info('FAILED!')
            send(event, context, "FAILED", { "Message": "Unexpected event received from CloudFormation" }, None)
    
    except Exception as e:
        message = "Unexected error creating mapping: {}".format(e)
        send(event, context, "FAILED", { "Message": message }, None)
            
    return status

def send(event, context, responseStatus, responseData, physicalResourceId):
    responseUrl = event['ResponseURL']

    responseBody = {
        'Status': responseStatus,
        'Reason': 'See the details in CloudWatch Log Stream: ' + context.log_stream_name,
        'PhysicalResourceId': physicalResourceId or context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': responseData
    }

    json_responseBody = json.dumps(responseBody)

    print("Response body:\n" + json_responseBody)

    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        print("Status code: " + response.reason)
    except Exception as e:
        print("send(..) failed executing requests.put(..): " + str(e))

    return