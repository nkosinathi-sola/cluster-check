# Architecture Overview of cluster-check

## Introduction

The `cluster-check` system is designed to manage and clean up old clusters in AWS that were created by autoscaling groups and failed to be deleted automatically. This tool helps maintain a clean AWS environment by terminating clusters that are beyond a specified age and are no longer the newest version for their service. This is crucial for cost management and avoiding resource clutter in cloud environments.

## High-Level Architecture

The codebase for `cluster-check` is primarily contained within a single Python script, `check.py`. This script utilizes the AWS SDK for Python (Boto3) to interact with AWS services, specifically Auto Scaling Groups (ASGs). The script is structured to:
1. Authenticate with AWS.
2. Retrieve and analyze existing ASGs.
3. Determine which ASGs should be terminated based on age and version criteria.
4. Terminate the outdated ASGs.

### Key Components

#### AWS Client Configuration
The AWS client is configured using predefined AWS credentials and region settings. This is facilitated by the `get_aws_client(service)` function which initializes a Boto3 client for a specified AWS service.

#### Cluster Retrieval and Analysis
The `get_clusters(asg_client)` function fetches all ASGs and filters them based on naming conventions that match specific application environments managed by Spinnaker (a continuous delivery platform). It organizes these ASGs into a dictionary of clusters grouped by service name, sorting them by version.

#### Cluster Termination Logic
The decision to terminate a cluster is made by the `should_terminate(cluster, newest_cluster)` function. It checks if a cluster is older than the newest cluster for the same service and if it has been alive past the maximum allowable age. If both conditions are met, the cluster is flagged for termination.

#### Execution and Termination Process
The `terminate_cluster(asg_client, cluster_name)` function handles the actual termination of an ASG. It attempts to delete the ASG and handles any exceptions that might occur during this process.

### Execution Flow
The script's main execution flow (`main()`) ties all components together:
1. It initializes the AWS client for Auto Scaling.
2. Retrieves clusters and checks each one to determine if it should be terminated.
3. Executes termination for clusters that meet the criteria.

## Architectural Invariants

- **AWS Dependency**: The entire functionality depends on AWS services, specifically Auto Scaling Groups. The script cannot function without valid AWS credentials and network access to AWS APIs.
- **Service-Based Organization**: Clusters are assumed to be organized by service names, and each service is expected to follow a specific naming convention that includes a version identifier.
- **Single Region Operation**: Currently, operations are performed in a single AWS region as specified in the AWS configuration.

## Boundaries and Interfaces

The boundary of this system lies at the interaction with AWS services. The script acts as a client to AWS, making API calls to fetch and manipulate ASGs. This boundary encapsulates the AWS-specific logic, making it a distinct layer in the architecture. Interaction with AWS is abstracted primarily through Boto3, which provides the interface for API calls.

## Conclusion

The `cluster-check` script is a focused tool designed for a specific operational task within AWS environments. It showcases a straightforward use of Python and Boto3 to manage cloud resources effectively. By maintaining a clean separation between AWS interactions and cluster management logic, the script remains modular and relatively easy to extend or modify. This architecture document provides a roadmap for navigating and understanding the script's structure and functionality.
