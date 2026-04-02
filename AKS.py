#!/usr/bin/env python3
"""
AKS Troubleshooting Log Collector
Collects cluster and node information from Azure AKS clusters for troubleshooting.
"""

import os
import sys
import json
import datetime
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient
from kubernetes import client, config
from kubernetes.client.rest import ApiException


class AKSTroubleshooter:
    """Collects troubleshooting data from AKS clusters."""
    
    def __init__(self, subscription_id, resource_group, cluster_name):
        """
        Initialize the AKSTroubleshooter.
        
        Args:
            subscription_id (str): Azure subscription ID
            resource_group (str): Resource group containing the AKS cluster
            cluster_name (str): Name of the AKS cluster
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.cluster_name = cluster_name
        self.log_data = []
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def log(self, message, level="INFO"):
        """Add a log entry with timestamp."""
        log_entry = f"[{self.timestamp}] [{level}] {message}"
        self.log_data.append(log_entry)
        print(log_entry)
    
    def connect_to_azure(self):
        """Authenticate and connect to Azure."""
        try:
            self.log("Connecting to Azure Cloud...")
            credential = DefaultAzureCredential()
            self.aks_client = ContainerServiceClient(
                credential=credential,
                subscription_id=self.subscription_id
            )
            self.log("Successfully connected to Azure Cloud")
            return True
        except Exception as e:
            self.log(f"Failed to connect to Azure: {str(e)}", "ERROR")
            return False
    
    def get_cluster_credentials(self):
        """Retrieve AKS cluster credentials."""
        try:
            self.log(f"Retrieving credentials for cluster: {self.cluster_name}")
            # Get cluster credentials
            cluster = self.aks_client.managed_clusters.get(
                self.resource_group, 
                self.cluster_name
            )
            
            # Get admin credentials
            creds = self.aks_client.managed_clusters.list_cluster_admin_credentials(
                self.resource_group, 
                self.cluster_name
            )
            
            # Extract kubeconfig from credentials
            kubeconfig = creds.kubeconfigs[0].value.decode('utf-8')
            
            # Write kubeconfig to temporary file
            temp_kubeconfig = "/tmp/aks_kubeconfig"
            with open(temp_kubeconfig, 'w') as f:
                f.write(kubeconfig)
            
            # Load kubernetes config
            config.load_kube_config(config_file=temp_kubeconfig)
            
            self.log(f"Successfully retrieved credentials for {self.cluster_name}")
            self.log(f"Cluster status: {cluster.provisioning_state}")
            
            # Log cluster details
            self.log(f"Cluster location: {cluster.location}")
            self.log(f"Kubernetes version: {cluster.kubernetes_version}")
            self.log(f"Node count: {cluster.agent_pool_profiles[0].count if cluster.agent_pool_profiles else 'N/A'}")
            
            return True
            
        except Exception as e:
            self.log(f"Failed to get cluster credentials: {str(e)}", "ERROR")
            return False
    
    def collect_node_information(self):
        """Collect node information from the AKS cluster."""
        try:
            self.log("Collecting node information...")
            v1 = client.CoreV1Api()
            nodes = v1.list_node()
            
            self.log(f"Found {len(nodes.items)} nodes in the cluster")
            
            for node in nodes.items:
                self.log(f"\n--- Node: {node.metadata.name} ---")
                self.log(f"  Status: {node.status.conditions[-1].type if node.status.conditions else 'Unknown'}")
                self.log(f"  Kubernetes Version: {node.status.node_info.kubelet_version}")
                self.log(f"  OS: {node.status.node_info.os_image}")
                self.log(f"  Architecture: {node.status.node_info.architecture}")
                self.log(f"  CPU Cores: {node.status.capacity.get('cpu', 'N/A')}")
                self.log(f"  Memory: {node.status.capacity.get('memory', 'N/A')}")
                self.log(f"  Pod CIDR: {node.spec.pod_cidr if node.spec.pod_cidr else 'N/A'}")
                
                # Node conditions
                self.log(f"  Conditions:")
                for condition in node.status.conditions:
                    if condition.status == "True":
                        self.log(f"    - {condition.type}: {condition.status} (Last: {condition.last_transition_time})")
                
                # Node labels (useful for troubleshooting)
                self.log(f"  Labels:")
                important_labels = ['node-type', 'kubernetes.azure.com/node-image-version', 'kubernetes.azure.com/mode']
                for label in important_labels:
                    if label in node.metadata.labels:
                        self.log(f"    - {label}: {node.metadata.labels[label]}")
                        
            return nodes.items
            
        except ApiException as e:
            self.log(f"Kubernetes API error: {str(e)}", "ERROR")
            return []
        except Exception as e:
            self.log(f"Error collecting node information: {str(e)}", "ERROR")
            return []
    
    def collect_pod_information(self, namespace="default"):
        """Collect pod information from the cluster."""
        try:
            self.log(f"Collecting pod information from namespace: {namespace}...")
            v1 = client.CoreV1Api()
            pods = v1.list_namespaced_pod(namespace=namespace)
            
            self.log(f"Found {len(pods.items)} pods in namespace {namespace}")
            
            # Identify problematic pods (not running)
            problematic_pods = []
            for pod in pods.items:
                status = pod.status.phase
                if status != "Running":
                    problematic_pods.append(pod)
                    self.log(f"  Problematic pod: {pod.metadata.name} - Status: {status}")
                    
                    # Log pod events for problematic pods
                    self.log(f"    Events for {pod.metadata.name}:")
                    events = v1.list_namespaced_event(
                        namespace=namespace,
                        field_selector=f"involvedObject.name={pod.metadata.name}"
                    )
                    for event in events.items:
                        self.log(f"      {event.reason}: {event.message}")
            
            return problematic_pods
            
        except ApiException as e:
            self.log(f"Kubernetes API error: {str(e)}", "ERROR")
            return []
        except Exception as e:
            self.log(f"Error collecting pod information: {str(e)}", "ERROR")
            return []
    
    def collect_cluster_events(self):
        """Collect recent cluster events."""
        try:
            self.log("Collecting recent cluster events...")
            v1 = client.CoreV1Api()
            events = v1.list_event_for_all_namespaces(timeout_seconds=30)
            
            recent_events = []
            for event in events.items[:50]:  # Last 50 events
                recent_events.append(event)
                self.log(f"  Event: {event.reason} - {event.message} (Namespace: {event.metadata.namespace})")
            
            return recent_events
            
        except Exception as e:
            self.log(f"Error collecting cluster events: {str(e)}", "ERROR")
            return []
    
    def generate_log_file(self, output_file="AKS.log"):
        """Generate the final log file."""
        try:
            self.log(f"Generating log file: {output_file}")
            
            with open(output_file, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write("AKS TROUBLESHOOTING LOG\n")
                f.write(f"Generated: {self.timestamp}\n")
                f.write(f"Cluster: {self.cluster_name}\n")
                f.write(f"Resource Group: {self.resource_group}\n")
                f.write("=" * 80 + "\n\n")
                
                for log_entry in self.log_data:
                    f.write(log_entry + "\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("END OF LOG\n")
                f.write("=" * 80 + "\n")
            
            self.log(f"Successfully generated {output_file}")
            return True
            
        except Exception as e:
            self.log(f"Failed to generate log file: {str(e)}", "ERROR")
            return False
    
    def run_troubleshooting(self):
        """Execute the complete troubleshooting workflow."""
        self.log("Starting AKS troubleshooting...")
        
        # Step 1: Connect to Azure
        if not self.connect_to_azure():
            self.log("Azure connection failed. Exiting.", "ERROR")
            self.generate_log_file()
            return False
        
        # Step 2: Get cluster credentials
        if not self.get_cluster_credentials():
            self.log("Failed to get cluster credentials. Exiting.", "ERROR")
            self.generate_log_file()
            return False
        
        # Step 3: Collect node information
        nodes = self.collect_node_information()
        
        # Step 4: Collect pod information from key namespaces
        self.collect_pod_information(namespace="default")
        self.collect_pod_information(namespace="kube-system")
        
        # Step 5: Collect cluster events
        self.collect_cluster_events()
        
        # Step 6: Generate final log
        self.generate_log_file()
        
        self.log("AKS troubleshooting completed successfully")
        return True


def main():
    """Main execution function."""
    
    # Configuration - Replace with your actual values
    SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "your-subscription-id")
    RESOURCE_GROUP = os.environ.get("AKS_RESOURCE_GROUP", "your-resource-group")
    CLUSTER_NAME = os.environ.get("AKS_CLUSTER_NAME", "your-cluster-name")
    
    # Validate configuration
    if SUBSCRIPTION_ID == "your-subscription-id" or \
       RESOURCE_GROUP == "your-resource-group" or \
       CLUSTER_NAME == "your-cluster-name":
        print("ERROR: Please set environment variables or update script with your AKS details:")
        print("  - AZURE_SUBSCRIPTION_ID")
        print("  - AKS_RESOURCE_GROUP")
        print("  - AKS_CLUSTER_NAME")
        sys.exit(1)
    
    # Create and run the troubleshooter
    troubleshooter = AKSTroubleshooter(
        subscription_id=SUBSCRIPTION_ID,
        resource_group=RESOURCE_GROUP,
        cluster_name=CLUSTER_NAME
    )
    
    troubleshooter.run_troubleshooting()


if __name__ == "__main__":
    main()