from chalice import Chalice

import boto3
from boto3 import resource
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr
import json
import uuid
import random

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# The boto3 dynamoDB resource
dynamodb_resource = resource('dynamodb')

app = Chalice(app_name='demoworkload')

@app.route('/', methods=['GET'], cors=True)
def index():
    return {'hello': 'world'}

@app.schedule('rate(5 minutes)')
def every_5min(event):

    num = random.randrange(1,2)
    userMetadata = {'workflow':"funnycatvideos"}
    mediaconvert_workload(num, 'Default', userMetadata )

    num = random.randrange(1,2)
    userMetadata = {'workflow':"sportsbloopers"}
    mediaconvert_workload(num, 'BULK', userMetadata)

    num = random.randrange(1,2)
    userMetadata = {'workflow':"news"}
    mediaconvert_workload(num, 'PRIORITY', userMetadata )

@app.schedule('rate(10 minutes)')
def every_10min(event):

    userMetadata = {'workflow':"funnycatvideos"}
    mediaconvert_workload(10, 'BULK', userMetadata )

SOURCE_BUCKET = 's3://elementalrodeo99-us-west-2/video-archive'
DESTINATION_BUCKET = 's3://dashboarddemo99'

def mediaconvert_workload(number, queue, userMetadata):
    region = 'us-east-1'
    assetID = str(uuid.uuid4())
    
    destinationS3basename = 'dashboarddemo99'
    mediaConvertRole = 'arn:aws:iam::526662735483:role/VODMediaConvertRole'
    statusCode = 200
    body = {}

    video_list = [
        '720p60/bigcats_720p60.mp4',
        '720p60/coffee_720p60.mp4',
        '720p60/donuts_720p60.mp4',
        '720p60/flowers_720p60.mp4',
        '720p60/futbol_720p60.mp4',
        '720p60/utltimatefrisbee_720p60.mp4',
        '720p60/windsurfing_720p60.mp4',
        '720p60/winetasting_720p60.mp4',
        #'futbol_720p60_422version.mov',
        'boulder_eats-ft.mp4',
        'boulder_eats-ft.mp4',
        'boulder_eats-ft.mp4',
        'boulder_eats-ft.mp4'
    ]   

    try:
    
        # get the account-specific mediaconvert endpoint for this region
        mc_client = boto3.client('mediaconvert', region_name=region)
        endpoints = mc_client.describe_endpoints()

        # add the account-specific endpoint to the client session 
        client = boto3.client('mediaconvert', region_name=region, endpoint_url=endpoints['Endpoints'][0]['Url'], verify=False)

        for n in range(number):
            video = random.choice(video_list)

            jobSettings = JOB
            # Update the job settings with the source video from the S3 event and destination 
            # paths for converted videos
            jobSettings['Inputs'][0]['FileInput'] = SOURCE_BUCKET + '/' + video
            
            S3KeyWatermark = 'assets/' + assetID + '/MP4/' 
            jobSettings['OutputGroups'][0]['OutputGroupSettings']['FileGroupSettings']['Destination'] \
                = DESTINATION_BUCKET  + '/' +  S3KeyWatermark  

            print('jobSettings:')
            print(json.dumps(jobSettings))

            # Convert the video using AWS Elemental MediaConvert
            job = client.create_job(Role=mediaConvertRole, Queue=queue, UserMetadata=userMetadata, Settings=jobSettings)
            print (json.dumps(job, default=str))

    except Exception as e:
        print ('Exception: %s' % e)
        statusCode = 500
        raise

    finally:
        return {
            'statusCode': statusCode,
            'body': json.dumps(body),
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}
        }        

JOB = {
    "OutputGroups": [
      {
        "CustomName": "MP4",
        "Name": "File Group",
        "Outputs": [
          {
            "ContainerSettings": {
              "Container": "MP4",
              "Mp4Settings": {
                "CslgAtom": "INCLUDE",
                "FreeSpaceBox": "EXCLUDE",
                "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
              }
            },
            "VideoDescription": {
              "Width": 960,
              "ScalingBehavior": "DEFAULT",
              "Height": 540,
              "TimecodeInsertion": "DISABLED",
              "AntiAlias": "ENABLED",
              "Sharpness": 50,
              "CodecSettings": {
                "Codec": "H_264",
                "H264Settings": {
                  "InterlaceMode": "PROGRESSIVE",
                  "NumberReferenceFrames": 3,
                  "Syntax": "DEFAULT",
                  "Softness": 0,
                  "GopClosedCadence": 1,
                  "GopSize": 90,
                  "Slices": 1,
                  "GopBReference": "DISABLED",
                  "SlowPal": "DISABLED",
                  "SpatialAdaptiveQuantization": "ENABLED",
                  "TemporalAdaptiveQuantization": "ENABLED",
                  "FlickerAdaptiveQuantization": "DISABLED",
                  "EntropyEncoding": "CABAC",
                  "Bitrate": 3000000,
                  "FramerateControl": "INITIALIZE_FROM_SOURCE",
                  "RateControlMode": "CBR",
                  "CodecProfile": "MAIN",
                  "Telecine": "NONE",
                  "MinIInterval": 0,
                  "AdaptiveQuantization": "HIGH",
                  "CodecLevel": "AUTO",
                  "FieldEncoding": "PAFF",
                  "SceneChangeDetect": "ENABLED",
                  "QualityTuningLevel": "SINGLE_PASS",
                  "FramerateConversionAlgorithm": "DUPLICATE_DROP",
                  "UnregisteredSeiTimecode": "DISABLED",
                  "GopSizeUnits": "FRAMES",
                  "ParControl": "INITIALIZE_FROM_SOURCE",
                  "NumberBFramesBetweenReferenceFrames": 2,
                  "RepeatPps": "DISABLED"
                }
              },
              "AfdSignaling": "NONE",
              "DropFrameTimecode": "ENABLED",
              "RespondToAfd": "NONE",
              "ColorMetadata": "INSERT"
            },
            "AudioDescriptions": [
              {
                "AudioTypeControl": "FOLLOW_INPUT",
                "CodecSettings": {
                  "Codec": "AAC",
                  "AacSettings": {
                    "AudioDescriptionBroadcasterMix": "NORMAL",
                    "Bitrate": 96000,
                    "RateControlMode": "CBR",
                    "CodecProfile": "LC",
                    "CodingMode": "CODING_MODE_2_0",
                    "RawFormat": "NONE",
                    "SampleRate": 48000,
                    "Specification": "MPEG4"
                  }
                },
                "LanguageCodeControl": "FOLLOW_INPUT"
              }
            ]
          }
        ],
        "OutputGroupSettings": {
          "Type": "FILE_GROUP_SETTINGS",
          "FileGroupSettings": {
            "Destination": " "
          }
        }
      }
    ],
    "AdAvailOffset": 0,
    "Inputs": [
      {
        "AudioSelectors": {
          "Audio Selector 1": {
            "Offset": 0,
            "DefaultSelection": "DEFAULT",
            "ProgramSelection": 1
          }
        },
        "VideoSelector": {
          "ColorSpace": "FOLLOW"
        },
        "FilterEnable": "AUTO",
        "PsiControl": "USE_PSI",
        "FilterStrength": 0,
        "DeblockFilter": "DISABLED",
        "DenoiseFilter": "DISABLED",
        "TimecodeSource": "EMBEDDED",
        "FileInput": " "
      }
    ]
  }

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
