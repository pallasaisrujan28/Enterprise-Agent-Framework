#!/bin/bash

# Build and Push Docker Images to ECR
# This script builds both frontend and backend Docker images and pushes them to Amazon ECR

set -e

echo "======================================"
echo "Build and Push Docker Images to ECR"
echo "======================================"

# Configuration
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
PROJECT_NAME="synthetic-audience"

BACKEND_REPO="$PROJECT_NAME-backend"
FRONTEND_REPO="$PROJECT_NAME-frontend"

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo ""

# Step 1: Create ECR repositories if they don't exist
echo "Creating ECR repositories..."

aws ecr create-repository \
    --repository-name $BACKEND_REPO \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true \
    2>/dev/null || echo "Backend repository already exists"

aws ecr create-repository \
    --repository-name $FRONTEND_REPO \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true \
    2>/dev/null || echo "Frontend repository already exists"

# Step 2: Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Step 3: Build Backend Image
echo "======================================"
echo "Building Backend Image..."
echo "======================================"

cd "/Users/Saisrujan/Downloads/Synthetic Data/backend"

docker build \
    --platform linux/amd64 \
    -t $BACKEND_REPO:latest \
    -t $ECR_REGISTRY/$BACKEND_REPO:latest \
    -t $ECR_REGISTRY/$BACKEND_REPO:$(date +%Y%m%d-%H%M%S) \
    .

echo "Backend image built successfully!"

# Step 4: Build Frontend Image
echo "======================================"
echo "Building Frontend Image..."
echo "======================================"

cd "/Users/Saisrujan/Downloads/Synthetic Data/frontend"

docker build \
    --platform linux/amd64 \
    -t $FRONTEND_REPO:latest \
    -t $ECR_REGISTRY/$FRONTEND_REPO:latest \
    -t $ECR_REGISTRY/$FRONTEND_REPO:$(date +%Y%m%d-%H%M%S) \
    .

echo "Frontend image built successfully!"

# Step 5: Push Backend Image
echo "======================================"
echo "Pushing Backend Image to ECR..."
echo "======================================"

docker push $ECR_REGISTRY/$BACKEND_REPO:latest
docker push $ECR_REGISTRY/$BACKEND_REPO:$(docker images $ECR_REGISTRY/$BACKEND_REPO --format "{{.Tag}}" | grep -v latest | head -1)

echo "Backend image pushed successfully!"

# Step 6: Push Frontend Image
echo "======================================"
echo "Pushing Frontend Image to ECR..."
echo "======================================"

docker push $ECR_REGISTRY/$FRONTEND_REPO:latest
docker push $ECR_REGISTRY/$FRONTEND_REPO:$(docker images $ECR_REGISTRY/$FRONTEND_REPO --format "{{.Tag}}" | grep -v latest | head -1)

echo "Frontend image pushed successfully!"

# Step 7: Save image URIs for ECS deployment
cat > "/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment/image-uris.env" << EOF
BACKEND_IMAGE_URI=$ECR_REGISTRY/$BACKEND_REPO:latest
FRONTEND_IMAGE_URI=$ECR_REGISTRY/$FRONTEND_REPO:latest
ECR_REGISTRY=$ECR_REGISTRY
AWS_REGION=$AWS_REGION
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
EOF

echo "======================================"
echo "Images Built and Pushed Successfully!"
echo "======================================"
echo "Backend Image: $ECR_REGISTRY/$BACKEND_REPO:latest"
echo "Frontend Image: $ECR_REGISTRY/$FRONTEND_REPO:latest"
echo ""
echo "Image URIs saved to: aws-deployment/image-uris.env"
echo ""
echo "Next step: Run ./05-deploy-ecs.sh to deploy to ECS"
