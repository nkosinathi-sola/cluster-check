import boto3
import re
from collections import defaultdict
from datetime import datetime, timedelta

# AWS credentials and region
AWS_ACCESS_KEY = 'xxxxxxxxxxxxxxxxxxxx'
AWS_SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxx'
AWS_REGION = 'eu-west-1'

# Spinnaker and AWS configurations
SPINNAKER_APPLICATION = 'alpha'  # The environment name
MAX_CLUSTER_AGE_HOURS = 24  # Maximum age of the old cluster before termination

def get_aws_client(service):
    return boto3.client(
        service,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION
    )

def get_clusters(asg_client):
    response = asg_client.describe_auto_scaling_groups()
    
    clusters = defaultdict(list)
    for asg in response['AutoScalingGroups']:
        if asg['AutoScalingGroupName'].startswith(SPINNAKER_APPLICATION + '-'):
            parts = asg['AutoScalingGroupName'].split('-')
            if len(parts) >= 4:
                service_name = '-'.join(parts[1:-1])  # Everything between 'alpha-' and '-v000'
                version = re.search(r'v(\d+)', parts[-1])
                if version:
                    clusters[service_name].append({
                        'name': asg['AutoScalingGroupName'],
                        'version': int(version.group(1)),
                        'creation_time': asg['CreatedTime']
                    })
    
    # Sort clusters for each service by version (descending)
    for service in clusters:
        clusters[service].sort(key=lambda x: x['version'], reverse=True)
    
    return clusters

def should_terminate(cluster, newest_cluster):
    age = datetime.now(cluster['creation_time'].tzinfo) - cluster['creation_time']
    return (cluster['version'] < newest_cluster['version'] and 
            age > timedelta(hours=MAX_CLUSTER_AGE_HOURS))

def terminate_cluster(asg_client, cluster_name):
    try:
        asg_client.delete_auto_scaling_group(
            AutoScalingGroupName=cluster_name,
            ForceDelete=True
        )
        print(f"Successfully terminated cluster: {cluster_name}")
    except Exception as e:
        print(f"Error terminating cluster {cluster_name}: {str(e)}")

def main():
    asg_client = get_aws_client('autoscaling')
    
    service_clusters = get_clusters(asg_client)
    
    for service, clusters in service_clusters.items():
        print(f"\nChecking service: {service}")
        if len(clusters) < 2:
            print(f"  Not enough clusters for {service} to perform termination.")
            continue
        
        newest_cluster = clusters[0]
        print(f"  Newest cluster: {newest_cluster['name']} (v{newest_cluster['version']})")
        
        for cluster in clusters[1:]:
            if should_terminate(cluster, newest_cluster):
                print(f"  Terminating old cluster: {cluster['name']} (v{cluster['version']})")
                terminate_cluster(asg_client, cluster['name'])
            else:
                print(f"  Cluster {cluster['name']} (v{cluster['version']}) does not meet termination criteria.")

if __name__ == "__main__":
    main()
