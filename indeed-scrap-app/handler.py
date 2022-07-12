import datetime
from distutils.log import Log
import json
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
MESSAGE_GROUP = 'messageGroup1'
SQS_INDEED_QUEUE = "https://sqs.us-east-1.amazonaws.com/926265474128/jf-indeed.fifo"
TABLE_NAME = 'jf-job-finder'

INDEED_BASE_URL = 'https://www.indeed.com/jobs?q&l=Remote&sc=0kf%3Aattr(DSQF7)jt(' \
                         'contract)%3B&rbl=Remote&jlid=aaa2b906602aa8f5&fromage=1'
INDEED_URL_JOB_PAGE = 'https://www.indeed.com/viewjob'


sqs_client = boto3.client('sqs', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb').Table(TABLE_NAME)


def scrap(event, context):

    html_text = requests.get(INDEED_BASE_URL).text
    
    #lxml is the html parser
    soup = BeautifulSoup(html_text, 'lxml')
    

    job_list = soup.find('ul', class_="jobsearch-ResultsList css-0")
    processed_jobs = []


    for job_element in job_list:
        try:
            job = {}
            job_id = ''
            title = ''

            div_title = job_element.find('h2', class_='jobTitle jobTitle-newJob css-bdjp2m eu4oa1w0')
            company = job_element.find('span', class_='companyName')

            if div_title is not None and company is not None:
                title = div_title.a.span.text
                job_id = div_title.a['id'].replace('job_', '')

                #realizar o append apenas se a chamada putItem ao dynamodb retornar sucesso
                processed_jobs.append(job_id)

                url = f'{INDEED_URL_JOB_PAGE}?jk={job_id}'

                html_job_page = requests.get(url).text
                job_soup = BeautifulSoup(html_job_page, 'lxml')
                job_description = job_soup.find(id='jobDescriptionText').text

                # the strip() method removes all the blank enters, creating an unique text
                job['id'] = job_id
                job["Description"] = job_description.strip()
                job["JobUrl"] = url
                job["Title"] = title
                job["Company"] = company.text
                
                
            response_dynamodb = dynamodb.put_item(TableName=TABLE_NAME, Item=job)
            
            #If ternário em python
            processed_jobs.append(job_id) if response_dynamodb['ResponseMetadata']['HTTPStatusCode'] == 200 else LOG.error("Job not saved into DynamoDB")
        except Exception as err:
            LOG.error(f'Error occurred {err}') 
    
    message = {'ids': processed_jobs}
    response = sqs_client.send_message(
        QueueUrl= SQS_INDEED_QUEUE,
        MessageBody=json.dumps(message),
        MessageGroupId=MESSAGE_GROUP
    )
    LOG.info(response)
    if response['ResponseMetadata']['HTTPStatusCode'] is 200:
        LOG.info(f'Message sent to sqs | response: {response}')
    else:
        LOG.error('Could not sent message to sqs')