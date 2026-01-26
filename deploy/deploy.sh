#!/bin/bash
# Deployment script for Social Agent VM on Google Cloud Platform
# This script creates and configures the VM instance

set -e  # Exit on error

PROJECT_ID="project-iap-485119"
ZONE="us-central1-a"
VM_NAME="social-agent-vm"
MACHINE_TYPE="e2-medium"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
DISK_SIZE="20GB"
STARTUP_SCRIPT="deploy/vm-setup.sh"

echo "=== Deploying Social Agent VM ==="
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "VM Name: $VM_NAME"
echo ""

# Set the project
echo "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Check if VM already exists
if gcloud compute instances describe $VM_NAME --zone=$ZONE --project=$PROJECT_ID &>/dev/null; then
    echo "VM $VM_NAME already exists. Deleting existing VM..."
    gcloud compute instances delete $VM_NAME --zone=$ZONE --quiet
    echo "Waiting for VM deletion to complete..."
    sleep 10
fi

# Create the VM instance
echo "Creating VM instance..."
gcloud compute instances create $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --image-family=$IMAGE_FAMILY \
    --image-project=$IMAGE_PROJECT \
    --boot-disk-size=$DISK_SIZE \
    --boot-disk-type=pd-standard \
    --metadata-from-file startup-script=$STARTUP_SCRIPT \
    --tags=http-server,https-server \
    --scopes=https://www.googleapis.com/auth/cloud-platform

echo ""
echo "=== VM Created Successfully ==="
echo "VM Name: $VM_NAME"
echo "Zone: $ZONE"
echo ""
echo "Next steps:"
echo "1. Wait for VM to finish initializing (check startup script logs)"
echo "2. SSH into the VM: gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "3. Upload application files to /opt/social-agent"
echo "4. Configure environment variables in /opt/social-agent/.env"
echo "5. Test the application manually"
echo ""
echo "To check startup script logs:"
echo "  gcloud compute instances get-serial-port-output $VM_NAME --zone=$ZONE"
echo ""
echo "To SSH into the VM:"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE"
