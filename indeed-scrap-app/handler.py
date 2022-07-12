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
indeed_base_url = 'https://www.indeed.com/jobs?q&l=Remote&sc=0kf%3Aattr(DSQF7)jt(' \
                         'contract)%3B&rbl=Remote&jlid=aaa2b906602aa8f5&fromage=1'
indeed_url_job_page = 'https://www.indeed.com/viewjob'
table_name = 'jf-job-finder'

sqs_client = boto3.client('sqs', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

def scrap(event, context):

    html_text = requests.get(indeed_base_url).text
    
    #lxml is the html parser
    soup = BeautifulSoup(html_text, 'lxml')
    

    job_list = soup.find('ul', class_="jobsearch-ResultsList css-0")
    processed_jobs = []


    for job_element in job_list:
        try:
            job = {}

            div_title = job_element.find('h2', class_='jobTitle jobTitle-newJob css-bdjp2m eu4oa1w0')
            title = ''

            company = job_element.find('span', class_='companyName')

            job_id = ''

            if div_title is not None and company is not None:
                title = div_title.a.span.text

                job_id = div_title.a['id'].replace('job_', '')
                processed_jobs.append(job_id)

                url = f'{indeed_url_job_page}?jk={job_id}'

                html_job_page = requests.get(url).text
                job_soup = BeautifulSoup(html_job_page, 'lxml')
                job_description = job_soup.find(id='jobDescriptionText').text

                # the strip() method removes all the blank enters, creating an unique text
                job['id'] = job_id
                job["Description"] = job_description.strip()
                job["JobUrl"] = url
                job["Title"] = title
                job["Company"] = company.text
                
                
            response_dynamodb = table.put_item(TableName=table_name, Item=job)
            logger.info(response_dynamodb['ResponseMetadata']['HTTPStatusCode'])
        except Exception as err:
            logger.error(f'Error occurred {err}') 
    
    message = {'ids': processed_jobs}
    response = sqs_client.send_message(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/926265474128/jf-indeed.fifo",
        MessageBody=json.dumps(message),
        MessageGroupId='messageGroup1'
    )
    logger.info(response)
    if response['ResponseMetadata']['HTTPStatusCode'] is 200:
        logger.info(f'Message sent to sqs | response: {response}')
    else:
        logger.error('Could not sent message to sqs')