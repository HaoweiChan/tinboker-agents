#!/bin/bash
set -e

echo "=== Graph Builder Agent - Google Cloud Run Deployment ==="

# Load .env if exists
if [ -f .env ]; then
    echo "Loading secrets from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    exit 1
fi

# 1. Setup Project
if [ -z "$PROJECT_ID" ]; then
    read -p "Enter your GCP Project ID: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID is required (in .env or prompt)."
    exit 1
fi

echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

echo "Enabling required APIs (Cloud Run, Artifact Registry)..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# 2. Build Container
IMAGE_NAME="gcr.io/$PROJECT_ID/graph-agent"
echo "Building container image: $IMAGE_NAME ..."
gcloud builds submit --tag $IMAGE_NAME .

# 3. Configure Environment
# Check variables, prompt if missing
if [ -z "$NEO4J_URI" ]; then
    read -p "Enter Neo4j URI (e.g. bolt+s://xxx.databases.neo4j.io): " NEO4J_URI
fi
if [ -z "$NEO4J_USER" ]; then
    read -p "Enter Neo4j User (default: neo4j): " NEO4J_USER
    NEO4J_USER=${NEO4J_USER:-neo4j}
fi
if [ -z "$NEO4J_PASSWORD" ]; then
    read -s -p "Enter Neo4j Password: " NEO4J_PASSWORD
    echo ""
fi
if [ -z "$GOOGLE_API_KEY" ]; then
    read -s -p "Enter Google API Key: " GOOGLE_API_KEY
    echo ""
fi
# Optional
if [ -z "$TAVILY_API_KEY" ]; then
    # Check if user wants to provide it if missing
    if [ -t 0 ]; then # Only prompt if interactive
        read -s -p "Enter Tavily API Key (optional, press enter to skip): " TAVILY_API_KEY
        echo ""
    fi
fi

# 4. Deploy
SERVICE_NAME="graph-agent"
REGION="us-central1"

echo "Deploying to Cloud Run ($SERVICE_NAME in $REGION)..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "NEO4J_URI=$NEO4J_URI" \
  --set-env-vars "NEO4J_USER=$NEO4J_USER" \
  --set-env-vars "NEO4J_PASSWORD=$NEO4J_PASSWORD" \
  --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY" \
  --set-env-vars "TAVILY_API_KEY=$TAVILY_API_KEY" \
  --port 8000

echo ""
echo "=== Deployment Complete! ==="
echo "Your API is live. Check the URL above."
