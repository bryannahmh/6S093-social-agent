#!/bin/bash
# Wrapper script to run the social agent application
# This script is called by cron and handles environment setup

set -e  # Exit on error

APP_DIR="/opt/social-agent"
ENV_FILE="$APP_DIR/.env"
LOG_FILE="/var/log/social-agent.log"

# Log execution start
echo "=== $(date): Starting social agent execution ===" >> $LOG_FILE

# Check if application directory exists
if [ ! -d "$APP_DIR" ]; then
    echo "ERROR: Application directory $APP_DIR does not exist" >> $LOG_FILE
    exit 1
fi

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "WARNING: Environment file $ENV_FILE does not exist" >> $LOG_FILE
fi

# Change to application directory
cd $APP_DIR

# Activate virtual environment
if [ ! -d "$APP_DIR/venv" ]; then
    echo "ERROR: Virtual environment not found at $APP_DIR/venv" >> $LOG_FILE
    exit 1
fi

source $APP_DIR/venv/bin/activate

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(cat $ENV_FILE | grep -v '^#' | xargs)
fi

# Run the application
echo "Running main.py..." >> $LOG_FILE
python3 main.py >> $LOG_FILE 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== $(date): Social agent execution completed successfully ===" >> $LOG_FILE
else
    echo "=== $(date): Social agent execution failed with exit code $EXIT_CODE ===" >> $LOG_FILE
fi

exit $EXIT_CODE
