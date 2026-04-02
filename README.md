# Senior-AZ-SRE-DevOps
This repo is meant   to automate SRE &amp; DevOps
Python script that connects to Azure, accesses an AKS cluster, gathers troubleshooting data, and creates an AKS.log file:
1.Connects to Azure Cloud.

2.Connects to an AKS cluster and its nodes.

3.Parses and extracts specific data from log files for troubleshooting purposes.

4.Generates an output file named AKS.log.
-----
Prerequisites Installation
Before running the script, install the required dependencies:
pip install azure-identity azure-mgmt-containerservice kubernetes


Environment Setup:
# Set environment variables
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AKS_RESOURCE_GROUP="your-resource-group"
export AKS_CLUSTER_NAME="your-cluster-name"

# Authenticate with Azure (if using Azure CLI)
az login

Features of the Script
Azure Connection: Uses DefaultAzureCredential to authenticate with Azure

AKS Cluster Access: Retrieves cluster credentials and connects to Kubernetes API

Node Information: Collects node status, version, capacity, conditions, and labels

Pod Information: Identifies problematic pods and collects their events

Cluster Events: Gathers recent cluster-wide events

Comprehensive Logging: Creates detailed AKS.log file with all collected information
