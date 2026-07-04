#!/usr/bin/env bash
# Deploys FinSight to Cloud Run -- the exact command used for the live deployment (see
# PROGRESS.md's 2026-07-04 entry for the full deploy-architecture rationale: same-container
# MCP Toolbox + ADK app, dedicated service account, adk web as the UI).
#
# Prerequisites (one-time, not run by this script):
#   1. A GCP project with billing enabled.
#   2. APIs enabled: gcloud services enable run.googleapis.com bigquery.googleapis.com \
#        aiplatform.googleapis.com artifactregistry.googleapis.com
#   3. A dedicated service account with roles/bigquery.user + roles/aiplatform.user:
#        gcloud iam service-accounts create finsight-run-sa \
#          --display-name="FinSight Cloud Run service account"
#        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
#          --member="serviceAccount:finsight-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
#          --role="roles/bigquery.user"
#        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
#          --member="serviceAccount:finsight-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
#          --role="roles/aiplatform.user"
#
# Usage: PROJECT_ID=your-project REGION=us-central1 ./deployment/deploy_cloud_run.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SERVICE_ACCOUNT="finsight-run-sa@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud run deploy finsight \
  --source . \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --service-account="$SERVICE_ACCOUNT" \
  --allow-unauthenticated \
  --memory=1Gi \
  --timeout=300 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=TRUE,BIGQUERY_PROJECT=${PROJECT_ID},BIGQUERY_DATASET=bigquery-public-data.thelook_ecommerce,MODEL_ROUTER=gemini-2.5-flash,MODEL_WORKER=gemini-2.5-flash,MODEL_VERIFIER=gemini-2.5-pro,ENABLE_TRACING=FALSE,ENABLE_VERIFIER=TRUE"
