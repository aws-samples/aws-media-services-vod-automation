from __future__ import print_function
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

#import json
import base64

host = 'https://search-analytics-rig-es-mmnst5fjhi3wg67u5zwuqgkfqy.us-west-2.es.amazonaws.com'   #ES domain endpoint
 
awsauth = AWS4Auth('KEY','SECRET-KEY','region','es')
es = Elasticsearch(hosts=[{'host': host, 'port': 443}], http_auth=awsauth, use_ssl=True, verify_certs=True, connection_class=RequestsHttpConnection)

def post_to_es(doc):
    _index = "lambda-v1"    # Append date here to get a daily index
    _type = "Event"       
    es.index(index=_index, doc_type=_type, body=doc)
    #print("success!")

def lambda_handler(event, context):

    for record in event['Records']:
       #Kinesis data is base64 encoded so decode here
       payload=base64.b64decode(record["kinesis"]["data"])
       print("Decoded payload: " + str(payload))

       post_to_es(str(payload))

    