#!/bin/bash

# Deploy to Amazon ECS with Application Load Balancer and HTTPS
# This script creates ECS cluster, task definitions, services, and ALB

set -e

echo "======================================"
echo "Deploy to Amazon ECS"
echo "======================================"

# Load configuration
source "/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment/image-uris.env"
source "/Users/Saisrujan/Downloads/Synthetic Data/backend/.env.rds"

# Configuration
CLUSTER_NAME="synthetic-audience-cluster"
SERVICE_NAME_BACKEND="synthetic-audience-backend"
SERVICE_NAME_FRONTEND="synthetic-audience-frontend"
TASK_FAMILY_BACKEND="synthetic-audience-backend-task"
TASK_FAMILY_FRONTEND="synthetic-audience-frontend-task"
ALB_NAME="synthetic-audience-alb"
TARGET_GROUP_BACKEND="synthetic-audience-backend-tg"
TARGET_GROUP_FRONTEND="synthetic-audience-frontend-tg"

# Load AWS credentials from backend .env
source "/Users/Saisrujan/Downloads/Synthetic Data/backend/.env"

echo "Creating ECS infrastructure..."
echo ""

# Step 1: Create ECS Cluster
echo "Creating ECS Cluster..."
aws ecs create-cluster \
    --cluster-name $CLUSTER_NAME \
    --region $AWS_REGION \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    2>/dev/null || echo "Cluster already exists"

# Step 2: Create IAM Role for ECS Tasks
echo "Creating IAM role for ECS tasks..."

# Create trust policy
cat > /tmp/ecs-task-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create execution role
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document file:///tmp/ecs-task-trust-policy.json \
    2>/dev/null || echo "Execution role already exists"

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
    2>/dev/null || echo "Policy already attached"

# Create task role with Bedrock permissions
cat > /tmp/ecs-task-role-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-role \
    --role-name ecsTaskRole \
    --assume-role-policy-document file:///tmp/ecs-task-trust-policy.json \
    2>/dev/null || echo "Task role already exists"

aws iam put-role-policy \
    --role-name ecsTaskRole \
    --policy-name BedrockAccess \
    --policy-document file:///tmp/ecs-task-role-policy.json \
    2>/dev/null || echo "Policy already exists"

TASK_EXECUTION_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text)
TASK_ROLE_ARN=$(aws iam get-role --role-name ecsTaskRole --query 'Role.Arn' --output text)

# Step 3: Create VPC and Security Groups
echo "Setting up networking..."

VPC_ID=$(aws ec2 describe-vpcs --region $AWS_REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
SUBNET_IDS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text)

# Create security group for ALB
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name synthetic-audience-alb-sg \
    --description "Security group for Synthetic Audience ALB" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || aws ec2 describe-security-groups --region $AWS_REGION --filters "Name=group-name,Values=synthetic-audience-alb-sg" --query 'SecurityGroups[0].GroupId' --output text)

# Allow HTTP and HTTPS from anywhere
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "HTTP rule already exists"

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "HTTPS rule already exists"

# Create security group for ECS tasks
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name synthetic-audience-ecs-sg \
    --description "Security group for Synthetic Audience ECS tasks" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || aws ec2 describe-security-groups --region $AWS_REGION --filters "Name=group-name,Values=synthetic-audience-ecs-sg" --query 'SecurityGroups[0].GroupId' --output text)

# Allow traffic from ALB
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 3000 \
    --source-group $ALB_SG_ID \
    --region $AWS_REGION 2>/dev/null || echo "Frontend rule already exists"

aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8010 \
    --source-group $ALB_SG_ID \
    --region $AWS_REGION 2>/dev/null || echo "Backend rule already exists"

# Step 4: Create Application Load Balancer
echo "Creating Application Load Balancer..."

ALB_ARN=$(aws elbv2 create-load-balancer \
    --name $ALB_NAME \
    --subnets $SUBNET_IDS \
    --security-groups $ALB_SG_ID \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text 2>/dev/null || aws elbv2 describe-load-balancers --region $AWS_REGION --names $ALB_NAME --query 'LoadBalancers[0].LoadBalancerArn' --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

echo "ALB created: $ALB_DNS"

# Step 5: Create Target Groups
echo "Creating target groups..."

BACKEND_TG_ARN=$(aws elbv2 create-target-group \
    --name $TARGET_GROUP_BACKEND \
    --protocol HTTP \
    --port 8010 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null || aws elbv2 describe-target-groups --region $AWS_REGION --names $TARGET_GROUP_BACKEND --query 'TargetGroups[0].TargetGroupArn' --output text)

FRONTEND_TG_ARN=$(aws elbv2 create-target-group \
    --name $TARGET_GROUP_FRONTEND \
    --protocol HTTP \
    --port 3000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path / \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null || aws elbv2 describe-target-groups --region $AWS_REGION --names $TARGET_GROUP_FRONTEND --query 'TargetGroups[0].TargetGroupArn' --output text)

# Step 6: Create ALB Listeners (HTTP for now, HTTPS later with certificate)
echo "Creating ALB listeners..."

aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$FRONTEND_TG_ARN \
    --region $AWS_REGION 2>/dev/null || echo "HTTP listener already exists"

# Create listener rule for backend API
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --region $AWS_REGION \
    --query 'Listeners[0].ListenerArn' \
    --output text)

aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 1 \
    --conditions Field=path-pattern,Values='/api/*' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN \
    --region $AWS_REGION 2>/dev/null || echo "Backend rule already exists"

# Continue in next message due to length...
echo "Infrastructure setup complete. Creating task definitions..."
