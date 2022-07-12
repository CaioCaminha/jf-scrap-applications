import datetime
import json
import logging
from urllib import response
import boto3
import requests
from botocore.exceptions import UnknownKeyError
from bs4 import BeautifulSoup
import re 

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AWS_REGION = 'us-east-1'
LINKEDIN_BASE_URL = ''
TABLE_NAME = 'jf-linkedin-table'

sqs_client = boto3.client('sqs', region_name= AWS_REGION)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def scrap(event, context):
    body = {
        "message": "Go Serverless v3.0! Your function executed successfully!",
        "input": event,
    }

    return {"statusCode": 200, "body": json.dumps(body)}
