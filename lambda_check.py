import boto3
import re
from collections import defaultdict
from datetime import datetime, timedelta
import os
import json
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS and Spinnaker configurations
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-1')
SPINNAKER_APPLICATIONS = os.environ.get('SPINNAKER_APPLICATIONS', 'alpha,beta,preprod').split(',')
MAX_CLUSTER_AGE_HOURS = int(os.environ.get('MAX_CLUSTER_AGE_HOURS', '2'))
DRY_RUN = os.environ.get('DRY_RUN', 'True').lower() == 'true'

def get_clusters(asg_client, application):
    logger.info(f"Getting clusters for application: {application}")
    paginator = asg_client.get_paginator('describe_auto_scaling_groups')
    clusters = defaultdict(list)
    
    for page in paginator.paginate():
        for asg in page['AutoScalingGroups']:
            if asg['AutoScalingGroupName'].startswith(application + '-'):
                parts = asg['AutoScalingGroupName'].split('-')
                if len(parts) >= 4:
                    service_name = '-'.join(parts[1:-1])
                    version = re.search(r'v(\d+)', parts[-1])
                    if version:
                        clusters[service_name].append({
                            'name': asg['AutoScalingGroupName'],
                            'version': int(version.group(1)),
                            'creation_time': asg['CreatedTime']
                        })
    
    for service in clusters:
        clusters[service].sort(key=lambda x: x['version'], reverse=True)
    
    logger.info(f"Found {sum(len(c) for c in clusters.values())} clusters for application {application}")
    return clusters

def should_terminate(cluster, newest_cluster):
    age = datetime.now(cluster['creation_time'].tzinfo) - cluster['creation_time']
    should_term = (cluster['version'] < newest_cluster['version'] and 
                   age > timedelta(hours=MAX_CLUSTER_AGE_HOURS))
    logger.info(f"Cluster {cluster['name']} should terminate: {should_term}")
    return should_term

def terminate_cluster(asg_client, cluster_name):
    if DRY_RUN:
        logger.info(f"DRY RUN: Would terminate cluster: {cluster_name}")
        return

    try:
        asg_client.delete_auto_scaling_group(
            AutoScalingGroupName=cluster_name,
            ForceDelete=True
        )
        logger.info(f"Successfully terminated cluster: {cluster_name}")
    except Exception as e:
        logger.error(f"Error terminating cluster {cluster_name}: {str(e)}")

def process_application(asg_client, application):
    logger.info(f"Processing application: {application}")
    service_clusters = get_clusters(asg_client, application)
    
    for service, clusters in service_clusters.items():
        logger.info(f"Checking service: {service}")
        if len(clusters) < 2:
            logger.info(f"Not enough clusters for {service} to perform termination.")
            continue
        
        newest_cluster = clusters[0]
        logger.info(f"Newest cluster: {newest_cluster['name']} (v{newest_cluster['version']})")
        
        for cluster in clusters[1:]:
            if should_terminate(cluster, newest_cluster):
                logger.info(f"Terminating old cluster: {cluster['name']} (v{cluster['version']})")
                terminate_cluster(asg_client, cluster['name'])
            else:
                logger.info(f"Cluster {cluster['name']} (v{cluster['version']}) does not meet termination criteria.")

def lambda_handler(event, context):
    logger.info("Lambda function started")
    logger.info(f"AWS Region: {AWS_REGION}")
    logger.info(f"Spinnaker Applications: {SPINNAKER_APPLICATIONS}")
    logger.info(f"Max Cluster Age Hours: {MAX_CLUSTER_AGE_HOURS}")
    logger.info(f"Dry Run: {DRY_RUN}")

    try:
        logger.info("Creating AutoScaling client")
        asg_client = boto3.client('autoscaling', region_name=AWS_REGION)
        logger.info("AutoScaling client created successfully")
        
        for application in SPINNAKER_APPLICATIONS:
            logger.info(f"Starting to process application: {application}")
            process_application(asg_client, application.strip())
            logger.info(f"Finished processing application: {application}")
    except Exception as e:
        logger.error(f"An error occurred in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

    logger.info("Lambda function completed successfully")
    return {
        'statusCode': 200,
        'body': json.dumps('Cluster check and termination process completed for all applications.')
    }
