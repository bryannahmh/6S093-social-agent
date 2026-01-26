# Social Agent VM Deployment Guide

This guide explains how to deploy the social-agent application to a Google Cloud Platform VM instance.

## Prerequisites

- Google Cloud SDK (gcloud) installed and configured
- Access to project `project-iap-485119` with billing enabled
- Appropriate IAM permissions to create Compute Engine instances

## Quick Deployment

Run the deployment script:

```bash
cd /Users/brymh/Desktop/IAP/social-agent
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

## Manual Deployment Steps

### 1. Set GCP Project

```bash
gcloud config set project project-iap-485119
```

### 2. Create VM Instance

```bash
gcloud compute instances create social-agent-vm \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --metadata-from-file startup-script=deploy/vm-setup.sh
```

### 3. SSH into VM

```bash
gcloud compute ssh social-agent-vm --zone=us-central1-a
```

### 4. Upload Application Files

Once SSH'd into the VM, you need to upload your application files. You can do this in several ways:

**Option A: Using gcloud from your local machine**
```bash
# From your local machine
gcloud compute scp --recurse \
    /Users/brymh/Desktop/IAP/social-agent/* \
    social-agent-vm:/opt/social-agent/ \
    --zone=us-central1-a
```

**Option B: Using git (if your code is in a repository)**
```bash
# SSH into VM first
cd /opt/social-agent
git clone <your-repo-url> .
```

**Option C: Manual file transfer**
Use `gcloud compute scp` to transfer individual files.

### 5. Configure Environment Variables

SSH into the VM and edit the environment file:

```bash
sudo nano /opt/social-agent/.env
```

Add the following environment variables:

```bash
# OpenRouter API
OPENROUTER_API_KEY=your_openrouter_api_key

# Notion API
NOTION_API_KEY=your_notion_api_key
NOTION_PAGE_IDS=page_id_1,page_id_2

# Mastodon API
MASTODON_BASE_URL=https://your-mastodon-instance.com
MASTODON_ACCESS_TOKEN=your_mastodon_access_token

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Replicate API
REPLICATE_API_TOKEN=your_replicate_api_token
```

### 6. Install Application Dependencies

The startup script should have installed dependencies, but if needed:

```bash
cd /opt/social-agent
source venv/bin/activate
pip install -r requirements.txt
```

### 7. Test the Application

Test the application manually:

```bash
cd /opt/social-agent
source venv/bin/activate
python3 main.py
```

### 8. Verify Cron Job

Check that the cron job is set up:

```bash
sudo crontab -l
```

You should see an entry like:
```
0 9 * * * /opt/social-agent/deploy/run-social-agent.sh >> /var/log/social-agent.log 2>&1
```

### 9. Monitor Logs

View application logs:

```bash
tail -f /var/log/social-agent.log
```

View setup logs:

```bash
cat /var/log/social-agent-setup.log
```

## VM Specifications

- **Machine Type**: e2-medium (2 vCPUs, 4GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Disk**: 20GB standard persistent disk
- **Zone**: us-central1-a
- **Estimated Cost**: ~$25/month (varies by usage)

## Scheduling

The application runs daily at 9:00 AM UTC via cron. To change the schedule, edit the cron job:

```bash
sudo crontab -e
```

Cron format: `minute hour day month weekday`
- `0 9 * * *` = Daily at 9:00 AM UTC
- `0 */6 * * *` = Every 6 hours
- `0 9 * * 1-5` = Weekdays at 9:00 AM UTC

## Troubleshooting

### Check VM Status
```bash
gcloud compute instances describe social-agent-vm --zone=us-central1-a
```

### View Startup Script Output
```bash
gcloud compute instances get-serial-port-output social-agent-vm --zone=us-central1-a
```

### Check Application Logs
```bash
gcloud compute ssh social-agent-vm --zone=us-central1-a
tail -f /var/log/social-agent.log
```

### Restart VM
```bash
gcloud compute instances restart social-agent-vm --zone=us-central1-a
```

### Delete VM (if needed)
```bash
gcloud compute instances delete social-agent-vm --zone=us-central1-a
```

## Security Considerations

1. **Environment Variables**: The `.env` file contains sensitive credentials. Ensure it has proper permissions (600).
2. **Firewall Rules**: The VM is created with HTTP/HTTPS tags. Adjust firewall rules as needed.
3. **Service Account**: The VM uses the default compute service account. Consider creating a custom service account with minimal permissions.
4. **Secrets Management**: For production, consider using Google Secret Manager instead of `.env` files.

## Cost Optimization

- **Stop VM when not needed**: `gcloud compute instances stop social-agent-vm --zone=us-central1-a`
- **Use preemptible instances**: Add `--preemptible` flag when creating VM (cheaper but can be terminated)
- **Monitor usage**: Use Cloud Console to track costs
