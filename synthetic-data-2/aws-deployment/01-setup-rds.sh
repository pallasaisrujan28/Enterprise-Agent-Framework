#!/bin/bash

# AWS RDS PostgreSQL Setup Script with pgvector extension
# This script creates an RDS instance configured for the Synthetic Audience Platform

set -e

echo "======================================"
echo "AWS RDS PostgreSQL Setup"
echo "======================================"

# Configuration Variables
DB_INSTANCE_IDENTIFIER="synthetic-audience-db"
DB_INSTANCE_CLASS="db.t3.medium"  # Adjust based on your needs
DB_ENGINE="postgres"
DB_ENGINE_VERSION="15.15"  # pgvector is supported in Postgres 15+
DB_NAME="synthetic_personas"
DB_USERNAME="dbadmin"
DB_ALLOCATED_STORAGE="20"  # GB
DB_MAX_ALLOCATED_STORAGE="100"  # GB for autoscaling
DB_BACKUP_RETENTION="7"  # days
REGION="us-west-2"

# Security Group and VPC (you may need to adjust these)
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)

echo "Using VPC: $VPC_ID"

# Step 1: Create Security Group for RDS
echo "Creating security group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name synthetic-audience-rds-sg \
    --description "Security group for Synthetic Audience RDS instance" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || echo "exists")

if [ "$SG_ID" = "exists" ]; then
    SG_ID=$(aws ec2 describe-security-groups \
        --region $REGION \
        --filters "Name=group-name,Values=synthetic-audience-rds-sg" \
        --query 'SecurityGroups[0].GroupId' \
        --output text)
    echo "Security group already exists: $SG_ID"
else
    echo "Created security group: $SG_ID"

    # Allow PostgreSQL traffic from anywhere (you should restrict this in production)
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 5432 \
        --cidr 0.0.0.0/0 \
        --region $REGION

    echo "Added PostgreSQL inbound rule to security group"
fi

# Step 2: Create DB Subnet Group
echo "Creating DB subnet group..."
SUBNET_IDS=$(aws ec2 describe-subnets \
    --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[*].SubnetId' \
    --output text)

aws rds create-db-subnet-group \
    --db-subnet-group-name synthetic-audience-subnet-group \
    --db-subnet-group-description "Subnet group for Synthetic Audience RDS" \
    --subnet-ids $SUBNET_IDS \
    --region $REGION 2>/dev/null || echo "DB subnet group already exists"

# Step 3: Generate a secure password
DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 24)
echo "Generated database password (save this securely!): $DB_PASSWORD"

# Step 4: Create RDS Instance
echo "Creating RDS instance (this will take 5-10 minutes)..."
aws rds create-db-instance \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --db-instance-class $DB_INSTANCE_CLASS \
    --engine $DB_ENGINE \
    --engine-version $DB_ENGINE_VERSION \
    --master-username $DB_USERNAME \
    --master-user-password "$DB_PASSWORD" \
    --allocated-storage $DB_ALLOCATED_STORAGE \
    --max-allocated-storage $DB_MAX_ALLOCATED_STORAGE \
    --storage-type gp3 \
    --storage-encrypted \
    --db-name $DB_NAME \
    --vpc-security-group-ids $SG_ID \
    --db-subnet-group-name synthetic-audience-subnet-group \
    --backup-retention-period $DB_BACKUP_RETENTION \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "mon:04:00-mon:05:00" \
    --publicly-accessible \
    --enable-cloudwatch-logs-exports '["postgresql","upgrade"]' \
    --region $REGION \
    --tags "Key=Project,Value=SyntheticAudience" "Key=Environment,Value=Production"

echo "Waiting for RDS instance to become available..."
aws rds wait db-instance-available \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --region $REGION

# Step 5: Get RDS endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --region $REGION \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

echo "======================================"
echo "RDS Instance Created Successfully!"
echo "======================================"
echo "Endpoint: $DB_ENDPOINT"
echo "Port: 5432"
echo "Database: $DB_NAME"
echo "Username: $DB_USERNAME"
echo "Password: $DB_PASSWORD"
echo ""
echo "Connection string:"
echo "postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:5432/$DB_NAME"
echo ""
echo "IMPORTANT: Save these credentials securely!"
echo "You can store them in AWS Secrets Manager or Parameter Store"
echo ""

# Step 6: Save credentials to .env file
cat > /Users/Saisrujan/Downloads/Synthetic\ Data/backend/.env.rds << EOF
# AWS RDS Database Configuration
DATABASE_URL=postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:5432/$DB_NAME
DB_HOST=$DB_ENDPOINT
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USERNAME
DB_PASSWORD=$DB_PASSWORD
EOF

echo "Credentials saved to backend/.env.rds"
echo ""
echo "Next steps:"
echo "1. Install pgvector extension: psql -h $DB_ENDPOINT -U $DB_USERNAME -d $DB_NAME -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
echo "2. Export your local database: ./02-export-database.sh"
echo "3. Import to RDS: ./03-import-to-rds.sh"
