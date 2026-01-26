#!/bin/bash
# VM Startup Script for Social Agent Application
# This script runs when the VM instance starts for the first time

set -e  # Exit on error

echo "=== Starting Social Agent VM Setup ===" | tee -a /var/log/social-agent-setup.log

# Update system packages
echo "Updating system packages..." | tee -a /var/log/social-agent-setup.log
apt-get update -y
apt-get upgrade -y

# Install Python 3.11 and pip
echo "Installing Python 3.11..." | tee -a /var/log/social-agent-setup.log
apt-get install -y python3.11 python3.11-venv python3-pip python3.11-dev

# Install system dependencies
echo "Installing system dependencies..." | tee -a /var/log/social-agent-setup.log
apt-get install -y git curl build-essential

# Create application directory
APP_DIR="/opt/social-agent"
echo "Creating application directory at $APP_DIR..." | tee -a /var/log/social-agent-setup.log
mkdir -p $APP_DIR

# Copy application files (assuming they're uploaded via metadata or gcloud)
# For now, we'll create a placeholder - actual files should be uploaded separately
echo "Setting up application files..." | tee -a /var/log/social-agent-setup.log

# Create Python virtual environment
echo "Creating Python virtual environment..." | tee -a /var/log/social-agent-setup.log
python3.11 -m venv $APP_DIR/venv

# Activate virtual environment and install dependencies
echo "Installing Python dependencies..." | tee -a /var/log/social-agent-setup.log
source $APP_DIR/venv/bin/activate
pip install --upgrade pip
pip install -r $APP_DIR/requirements.txt

# Create log directory
mkdir -p /var/log
touch /var/log/social-agent.log
chmod 666 /var/log/social-agent.log

# Set up environment variables file location
ENV_FILE="$APP_DIR/.env"
echo "Environment variables will be stored in $ENV_FILE" | tee -a /var/log/social-agent-setup.log
echo "# Environment variables should be added here" > $ENV_FILE
chmod 600 $ENV_FILE

# Make runner script executable
chmod +x $APP_DIR/deploy/run-social-agent.sh

# Set up cron job (runs daily at 9 AM UTC)
echo "Setting up cron job..." | tee -a /var/log/social-agent-setup.log
CRON_USER="root"
CRON_CMD="0 9 * * * $APP_DIR/deploy/run-social-agent.sh >> /var/log/social-agent.log 2>&1"

# Add cron job if it doesn't exist
(crontab -u $CRON_USER -l 2>/dev/null | grep -v "run-social-agent.sh"; echo "$CRON_CMD") | crontab -u $CRON_USER -

echo "=== VM Setup Complete ===" | tee -a /var/log/social-agent-setup.log
echo "Next steps:" | tee -a /var/log/social-agent-setup.log
echo "1. Upload application files to $APP_DIR" | tee -a /var/log/social-agent-setup.log
echo "2. Configure environment variables in $ENV_FILE" | tee -a /var/log/social-agent-setup.log
echo "3. Test the application manually" | tee -a /var/log/social-agent-setup.log
