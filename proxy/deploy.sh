#!/bin/bash

# Deploy Gmail webhook proxy
gcloud functions deploy gmail-webhook-proxy \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point gmail_webhook_proxy \
    --memory 256MB \
    --timeout 60s \
    --region us-central1

# Deploy Calendar webhook proxy  
gcloud functions deploy calendar-webhook-proxy \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point calendar_webhook_proxy \
    --memory 256MB \
    --timeout 60s \
    --region us-central1

# Deploy health check
gcloud functions deploy proxy-health-check \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point proxy_health_check \
    --memory 128MB \
    --timeout 30s \
    --region us-central1

echo "Proxy functions deployed successfully!"
echo "Gmail webhook URL: https://us-central1-YOUR_PROJECT.cloudfunctions.net/gmail-webhook-proxy"
echo "Calendar webhook URL: https://us-central1-YOUR_PROJECT.cloudfunctions.net/calendar-webhook-proxy"
echo "Health check URL: https://us-central1-YOUR_PROJECT.cloudfunctions.net/proxy-health-check"