from cgitb import html
import datetime
import json
from operator import contains
import uuid
import logging
from urllib import response
import boto3
import requests
from botocore.exceptions import UnknownKeyError
from bs4 import BeautifulSoup
import re 

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

AWS_REGION = 'us-east-1'
PLATFORM_TYPE_ITEM = 'linkedin'

LINKEDIN_BASE_URL = 'https://www.linkedin.com/jobs/search/?distance=25.0&f_JT=C&f_TPR=r86400&f_WT=2&geoId=92000000&keywords=software%20developer&sortBy=DD&position=1&pageNum=0'

#dynamodb configuration
TABLE_NAME = 'jf-job-finder'
dynamodb = boto3.resource('dynamodb').Table(TABLE_NAME)

#sqs configuration
SQS_LINKEDIN_QUEUE = 'https://sqs.us-east-1.amazonaws.com/926265474128/jf-linkedin.fifo'
MESSAGE_GROUP = 'messageGroup1'
sqs_client = boto3.client('sqs', region_name= AWS_REGION)

def scrap(event, context):
    html_text = requests.get(LINKEDIN_BASE_URL).text

    soup = BeautifulSoup(html_text, 'lxml')
    
    #print(html_text)

    job_list = soup.find('ul', class_="jobs-search__results-list")
    processed_jobs = []

    for job_element in job_list:
        job = {}
        job_id = str(uuid.uuid4())
        job_url = ''
        
        try:
            
            div_base_card = job_element.find('div', class_= 'base-search-card__info')
            job_url = job_element.find('a', class_= 'base-card__full-link absolute top-0 right-0 bottom-0 left-0 p-0 z-[2]')['href']

            job_title = div_base_card.h3.text
            job_company = div_base_card.h4.a.text
            
            html_job_page = requests.get(job_url).text
            job_soup = BeautifulSoup(html_job_page, 'lxml')
            
            job_description = job_soup.find('div', class_='show-more-less-html__markup').text
        

            job['id'] = job_id
            job['title'] = re.sub('[\n]', '', job_title)
            job['company'] = re.sub('[\n]', '', job_company)
            job['description'] = re.sub('[\n]', '', job_description)
            job['job_url'] = job_url
            job['platform_type_item'] = PLATFORM_TYPE_ITEM

            LOG.info(f'Sending Job to DynamoDB | JOB_ID = {job_id}')
            response_dynamodb = dynamodb.put_item(TableName=TABLE_NAME, Item=job)
            response_code = response_dynamodb['ResponseMetadata']['HTTPStatusCode']


            #If ternário em python
            LOG.info(f'Job Sent to DynamoDB | Response Code = {response_code}')
            processed_jobs.append(job_id) if response_code == 200 else LOG.error("Job not saved into DynamoDB")
        except Exception as err:
            LOG.error(f'Error occurred {err}') if str(err) != 'find() takes no keyword arguments' else LOG.info('') 
    
    message = {'ids': processed_jobs}
    
    response = sqs_client.send_message(
        QueueUrl= SQS_LINKEDIN_QUEUE,
        MessageBody=json.dumps(message),
        MessageGroupId=MESSAGE_GROUP
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        LOG.info(f'Message sent to sqs | response: {response}')
    else:
        LOG.error('Could not sent message to sqs')

