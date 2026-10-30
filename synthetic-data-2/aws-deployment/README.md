# AWS Deployment Guide for Synthetic Audience Platform

This guide will help you deploy the Synthetic Audience Platform to AWS using RDS, ECS, ALB, and CloudFront.

## Prerequisites

1. AWS CLI installed and configured with your credentials
2. Docker installed on your local machine
3. PostgreSQL client tools (`psql`, `pg_dump`) installed
4. Sufficient AWS permissions to create:
   - RDS instances
   - ECS clusters and services
   - ECR repositories
   - Application Load Balancers
   - CloudFront distributions
   - IAM roles and policies

## Deployment Steps

### Step 1: Create RDS PostgreSQL Instance

```bash
cd "/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment"
chmod +x *.sh
./01-setup-rds.sh
```

This script will:
- Create an RDS PostgreSQL 15.4 instance with pgvector support
- Set up security groups
- Configure backups and monitoring
- Generate secure credentials
- Save connection details to `backend/.env.rds`

**Important**: Save the database credentials displayed at the end!

### Step 2: Export Local Database

```bash
./02-export-database.sh
```

This script will:
- Export your local PostgreSQL schema
- Export all data
- Create a complete backup
- Generate table statistics

All exports are saved to `aws-deployment/db-export/`

### Step 3: Import to RDS

```bash
./03-import-to-rds.sh
```

This script will:
- Connect to your new RDS instance
- Install the pgvector extension
- Import the schema
- Import all data
- Verify the import
- Run ANALYZE to update statistics

### Step 4: Build and Push Docker Images

```bash
./04-build-and-push-images.sh
```

This script will:
- Create ECR repositories for frontend and backend
- Build Docker images for both services
- Tag images with timestamps and latest
- Push images to ECR
- Save image URIs for ECS deployment

### Step 5: Deploy to ECS

```bash
./05-deploy-ecs.sh
```

This script will:
- Create an ECS Fargate cluster
- Set up VPC, security groups, and networking
- Create Application Load Balancer
- Create target groups for frontend and backend
- Set up ALB listeners and routing rules
- Create IAM roles with Bedrock permissions
- Register ECS task definitions
- Create and start ECS services

### Step 6: Configure HTTPS (Manual Step)

After the ALB is created, you'll need to:

1. **Request an SSL/TLS Certificate** (if you have a domain):
   ```bash
   aws acm request-certificate \
       --domain-name yourdomain.com \
       --validation-method DNS \
       --region us-west-2
   ```

2. **Update ALB to use HTTPS**:
   ```bash
   aws elbv2 create-listener \
       --load-balancer-arn <your-alb-arn> \
       --protocol HTTPS \
       --port 443 \
       --certificates CertificateArn=<your-cert-arn> \
       --default-actions Type=forward,TargetGroupArn=<frontend-tg-arn>
   ```

### Step 7: Set Up CloudFront (Optional but Recommended)

Create a CloudFront distribution:

```bash
aws cloudfront create-distribution \
    --origin-domain-name <your-alb-dns> \
    --default-root-object index.html
```

CloudFront provides:
- Global CDN caching
- DDoS protection
- SSL/TLS termination
- Custom domain support

## Environment Variables

### Backend (.env)

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-west-2

# Bedrock Model
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Database (from RDS)
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/synthetic_personas
```

### Frontend Environment

The frontend will connect to the backend via the ALB:
- Local: `http://localhost:8010`
- Production: `http://<alb-dns>/api` or `https://yourdomain.com/api`

## Architecture

```
┌─────────────┐
│  CloudFront │ (Optional CDN)
└──────┬──────┘
       │
┌──────▼──────┐
│     ALB     │ (Application Load Balancer)
│  Port 80/443│
└──────┬──────┘
       │
       ├───────────────┬───────────────┐
       │               │               │
┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  Frontend   │ │  Backend   │ │  Backend   │
│    ECS      │ │    ECS     │ │    ECS     │
│  (Fargate)  │ │  (Fargate) │ │  (Fargate) │
└─────────────┘ └──────┬─────┘ └──────┬─────┘
                       │               │
                ┌──────▼───────────────▼─────┐
                │    RDS PostgreSQL 15.4     │
                │    with pgvector extension │
                └────────────────────────────┘
```

## Cost Estimation

Approximate monthly costs (us-west-2):

- **RDS db.t3.medium**: ~$60/month
- **ECS Fargate** (2 tasks, 0.5 vCPU, 1GB each): ~$30/month
- **Application Load Balancer**: ~$20/month
- **CloudFront**: ~$10-50/month (depending on traffic)
- **ECR Storage**: ~$1/month
- **Data Transfer**: Variable based on usage

**Total**: ~$120-170/month

## Monitoring

- **CloudWatch Logs**: ECS task logs automatically sent to CloudWatch
- **ALB Metrics**: Monitor request count, latency, error rates
- **RDS Metrics**: Monitor CPU, connections, storage

## Troubleshooting

### RDS Connection Issues
- Check security group allows traffic from ECS security group
- Verify RDS is publicly accessible (or use VPC peering)
- Test connection: `psql -h <rds-endpoint> -U dbadmin -d synthetic_personas`

### ECS Task Not Starting
- Check CloudWatch Logs for task errors
- Verify IAM roles have correct permissions
- Ensure Docker images are in ECR
- Check task definition environment variables

### ALB 502/503 Errors
- Verify target groups are healthy
- Check ECS task health checks
- Ensure security groups allow ALB → ECS traffic
- Review application logs in CloudWatch

## Cleanup

To delete all AWS resources:

```bash
# Delete ECS services
aws ecs update-service --cluster synthetic-audience-cluster --service <service-name> --desired-count 0
aws ecs delete-service --cluster synthetic-audience-cluster --service <service-name>

# Delete ECS cluster
aws ecs delete-cluster --cluster synthetic-audience-cluster

# Delete ALB
aws elbv2 delete-load-balancer --load-balancer-arn <alb-arn>

# Delete target groups
aws elbv2 delete-target-group --target-group-arn <tg-arn>

# Delete RDS instance
aws rds delete-db-instance --db-instance-identifier synthetic-audience-db --skip-final-snapshot

# Delete ECR repositories
aws ecr delete-repository --repository-name synthetic-audience-backend --force
aws ecr delete-repository --repository-name synthetic-audience-frontend --force
```

## Security Best Practices

1. **Use Secrets Manager** for database credentials instead of environment variables
2. **Enable WAF** on CloudFront/ALB for additional security
3. **Restrict security groups** to minimum required access
4. **Enable RDS encryption** at rest and in transit
5. **Use private subnets** for ECS tasks (with NAT Gateway)
6. **Enable CloudTrail** for audit logging
7. **Set up CloudWatch Alarms** for critical metrics

## Support

For issues or questions:
1. Check CloudWatch Logs for application errors
2. Review AWS documentation
3. Contact support

---

Last updated: 2025-11-28
