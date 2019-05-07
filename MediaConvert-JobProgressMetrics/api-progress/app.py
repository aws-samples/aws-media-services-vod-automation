from chalice import Chalice
import boto3
from boto3 import resource
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr
import json
import uuid
import random
import logging
import decimal
import os

app = Chalice(app_name='api-progress')

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)

VERSION = 'v1'

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# The boto3 dynamoDB resource
dynamodb_resource = resource('dynamodb')

@app.route('/', methods=['GET'], cors=True)
def index():
    DYNAMO_TABLE_NAME = os.environ['JobTable']
    return {'DYNAMO_TABLE_NAME': DYNAMO_TABLE_NAME}

@app.route('/progress/job/{jobId}', methods=['GET'], cors=True)
def job_progress(jobId):
    DYNAMO_TABLE_NAME = os.environ['JobTable']
    DYNAMO_INDEX_NAME = 'id-createdAt-index' 

    logger.info('GET progress for {} from {}'.format(jobId, DYNAMO_TABLE_NAME))
    
    try:
        table = dynamodb_resource.Table(DYNAMO_TABLE_NAME)
        
        response = table.query(IndexName=DYNAMO_INDEX_NAME, KeyConditionExpression=Key('id').eq(jobId))
    
    except ClientError as e:
        logger.info("ClientError from Dynamodb {}".format(e.response['Error']['Message']))
        raise BadRequestError("Dynamodb returned error message '%s'" % e.response['Error']['Message'])
    except Exception as e:
        logger.info("ClientError from Dynamodb {}".format(e.response['Error']['Message']))
        raise ChaliceViewError("Dynamodb returned error message '%s'" % e.response['Error']['Message'])

    print (json.dumps(response, cls=DecimalEncoder))
    # there is no information about this job yet
    if response['Count'] > 0:
        return response['Items'][0]
    else:
        return {}

@app.route('/progress/status/{status}', methods=['GET'], cors=True)
def status_progress(status):
    DYNAMO_TABLE_NAME = os.environ['JobTable']
    
    logger.info('GET progress for jobs with status {} from {}'.format(status, DYNAMO_TABLE_NAME))

    table = dynamodb_resource.Table(DYNAMO_TABLE_NAME)
    
    response = table.query(
        IndexName='status-createdAt-index', 
        KeyConditionExpression=Key('status').eq(status),
        ScanIndexForward=False
    )
    items =  response['Items']

    while True:
        print(len(response['Items']))
        if response.get('LastEvaluatedKey'):
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                IndexName='status-createdAt-index', 
                KeyConditionExpression=Key('status').eq(status),
                ScanIndexForward=False
            )
            items += response['Items']
        else:
            break
    
    return items

# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#
