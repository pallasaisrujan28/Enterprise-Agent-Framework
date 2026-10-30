# AWS Deployment - Quick Summary

## ✅ What's Been Created

### 1. Database Migration Scripts
- **[01-setup-rds.sh](aws-deployment/01-setup-rds.sh)** - Creates RDS PostgreSQL instance with pgvector
- **[02-export-database.sh](aws-deployment/02-export-database.sh)** - Exports local database to files
- **[03-import-to-rds.sh](aws-deployment/03-import-to-rds.sh)** - Imports database to RDS

### 2. Docker Configuration
- **[backend/.dockerignore](backend/.dockerignore)** - Excludes unnecessary files from backend image
- **[backend/Dockerfile](backend/Dockerfile)** - Multi-stage build for Python backend
- **[frontend/.dockerignore](frontend/.dockerignore)** - Excludes unnecessary files from frontend image
- **[frontend/Dockerfile](frontend/Dockerfile)** - Multi-stage build for Next.js frontend

### 3. AWS Deployment Scripts
- **[04-build-and-push-images.sh](aws-deployment/04-build-and-push-images.sh)** - Builds and pushes Docker images to ECR
- **[05-deploy-ecs.sh](aws-deployment/05-deploy-ecs.sh)** - Deploys complete ECS infrastructure

### 4. Documentation
- **[aws-deployment/README.md](aws-deployment/README.md)** - Comprehensive deployment guide
- **[aws-deployment/DEPLOYMENT_CHECKLIST.md](aws-deployment/DEPLOYMENT_CHECKLIST.md)** - Step-by-step checklist

---

## 🚀 Quick Start - Deploy in 5 Steps

### Prerequisites
```bash
# Verify you have all tools installed
aws --version
docker --version
psql --version
pg_dump --version
```

### Step 1: Create RDS Database
```bash
cd "/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment"
./01-setup-rds.sh
```
**⚠️ IMPORTANT**: Save the database password shown at the end!

### Step 2: Export Local Database
```bash
./02-export-database.sh
```

### Step 3: Import to RDS
```bash
./03-import-to-rds.sh
```

### Step 4: Build & Push Docker Images
```bash
./04-build-and-push-images.sh
```

### Step 5: Deploy to AWS
```bash
./05-deploy-ecs.sh
```

---

## 📋 What Gets Deployed

```
AWS Infrastructure Created:
├── RDS PostgreSQL 15.4 (with pgvector)
│   ├── Database: synthetic_personas
│   ├── Instance: db.t3.medium
│   └── Storage: 20GB (auto-scaling to 100GB)
│
├── ECR Repositories
│   ├── synthetic-audience-backend
│   └── synthetic-audience-frontend
│
├── ECS Fargate Cluster
│   ├── Backend Service (2 tasks)
│   └── Frontend Service (2 tasks)
│
├── Application Load Balancer
│   ├── HTTP Listener (Port 80)
│   ├── Frontend Target Group (Port 3000)
│   └── Backend Target Group (Port 8010)
│
├── Security Groups
│   ├── ALB Security Group (allows 80/443)
│   ├── ECS Security Group (allows from ALB)
│   └── RDS Security Group (allows from ECS)
│
└── IAM Roles
    ├── ECS Task Execution Role
    └── ECS Task Role (with Bedrock permissions)
```

---

## 🔗 Access Your Application

After deployment completes:

1. **Get your ALB DNS**:
   ```bash
   aws elbv2 describe-load-balancers \
       --names synthetic-audience-alb \
       --region us-west-2 \
       --query 'LoadBalancers[0].DNSName' \
       --output text
   ```

2. **Access your application**:
   - Frontend: `http://<alb-dns>/`
   - Backend API: `http://<alb-dns>/api/`
   - Health Check: `http://<alb-dns>/api/health`

3. **Test it works**:
   ```bash
   # Replace with your ALB DNS
   ALB_DNS="your-alb-dns-here"

   # Test frontend
   curl http://$ALB_DNS/

   # Test backend health
   curl http://$ALB_DNS/api/health

   # Test API
   curl http://$ALB_DNS/api/audience/personas
   ```

---

## 💰 Estimated Monthly Costs

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| RDS PostgreSQL | db.t3.medium, 20GB | ~$60 |
| ECS Fargate | 4 tasks (0.5 vCPU, 1GB) | ~$60 |
| Application Load Balancer | Standard | ~$20 |
| ECR Storage | ~1GB | ~$1 |
| **Total** | | **~$141/month** |

*Costs may vary based on usage, region, and data transfer*

---

## 🔒 Security Features

✅ All traffic encrypted in transit
✅ RDS encryption at rest enabled
✅ Security groups with minimal access
✅ IAM roles with least privilege
✅ Container image scanning enabled
✅ CloudWatch logging enabled

---

## 📊 Monitoring

View logs and metrics:

```bash
# View ECS task logs
aws logs tail /ecs/synthetic-audience-backend --follow --region us-west-2

# Check ECS service status
aws ecs describe-services \
    --cluster synthetic-audience-cluster \
    --services synthetic-audience-backend \
    --region us-west-2

# Check target health
aws elbv2 describe-target-health \
    --target-group-arn <tg-arn> \
    --region us-west-2
```

Or use AWS Console:
- **ECS**: https://console.aws.amazon.com/ecs/
- **CloudWatch**: https://console.aws.amazon.com/cloudwatch/
- **RDS**: https://console.aws.amazon.com/rds/

---

## 🆘 Troubleshooting

### Issue: ECS tasks keep restarting
**Solution**: Check CloudWatch logs for errors
```bash
aws logs tail /ecs/synthetic-audience-backend --follow --region us-west-2
```

### Issue: ALB returns 502/503
**Solution**: Check target group health
```bash
# Get target group ARN
TG_ARN=$(aws elbv2 describe-target-groups --names synthetic-audience-backend-tg --region us-west-2 --query 'TargetGroups[0].TargetGroupArn' --output text)

# Check health
aws elbv2 describe-target-health --target-group-arn $TG_ARN --region us-west-2
```

### Issue: Can't connect to database
**Solution**: Verify security group rules and RDS is publicly accessible

See [DEPLOYMENT_CHECKLIST.md](aws-deployment/DEPLOYMENT_CHECKLIST.md) for detailed troubleshooting.

---

## 🔄 Updating the Application

### Update Backend Code
```bash
# Make code changes
cd backend/

# Rebuild and push image
cd "/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment"
./04-build-and-push-images.sh

# Force new deployment
aws ecs update-service \
    --cluster synthetic-audience-cluster \
    --service synthetic-audience-backend \
    --force-new-deployment \
    --region us-west-2
```

### Update Frontend Code
```bash
# Make code changes
cd frontend/

# Rebuild and push image
cd "/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment"
./04-build-and-push-images.sh

# Force new deployment
aws ecs update-service \
    --cluster synthetic-audience-cluster \
    --service synthetic-audience-frontend \
    --force-new-deployment \
    --region us-west-2
```

---

## 🗑️ Clean Up (Delete Everything)

**WARNING**: This will delete all AWS resources and cannot be undone!

```bash
# Stop and delete ECS services
aws ecs update-service --cluster synthetic-audience-cluster --service synthetic-audience-backend --desired-count 0 --region us-west-2
aws ecs update-service --cluster synthetic-audience-cluster --service synthetic-audience-frontend --desired-count 0 --region us-west-2
aws ecs delete-service --cluster synthetic-audience-cluster --service synthetic-audience-backend --region us-west-2
aws ecs delete-service --cluster synthetic-audience-cluster --service synthetic-audience-frontend --region us-west-2

# Delete ECS cluster
aws ecs delete-cluster --cluster synthetic-audience-cluster --region us-west-2

# Delete ALB (get ARN first)
ALB_ARN=$(aws elbv2 describe-load-balancers --names synthetic-audience-alb --region us-west-2 --query 'LoadBalancers[0].LoadBalancerArn' --output text)
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN --region us-west-2

# Delete target groups
aws elbv2 delete-target-group --target-group-arn <backend-tg-arn> --region us-west-2
aws elbv2 delete-target-group --target-group-arn <frontend-tg-arn> --region us-west-2

# Delete RDS instance (⚠️ This deletes your data!)
aws rds delete-db-instance \
    --db-instance-identifier synthetic-audience-db \
    --skip-final-snapshot \
    --region us-west-2

# Delete ECR repositories
aws ecr delete-repository --repository-name synthetic-audience-backend --force --region us-west-2
aws ecr delete-repository --repository-name synthetic-audience-frontend --force --region us-west-2
```

---

## 📚 Additional Resources

- **Detailed Guide**: [aws-deployment/README.md](aws-deployment/README.md)
- **Checklist**: [aws-deployment/DEPLOYMENT_CHECKLIST.md](aws-deployment/DEPLOYMENT_CHECKLIST.md)
- **AWS ECS Documentation**: https://docs.aws.amazon.com/ecs/
- **AWS RDS Documentation**: https://docs.aws.amazon.com/rds/

---

## 🎯 Next Steps

1. ✅ Deploy to AWS using the scripts above
2. 🔐 Set up HTTPS with AWS Certificate Manager
3. 🌐 Configure custom domain
4. 📊 Set up CloudWatch alarms
5. 🚀 Set up CI/CD pipeline
6. 🔄 Configure auto-scaling
7. 💾 Set up automated RDS backups

---

**Need Help?**
- Check the [README](aws-deployment/README.md) for detailed instructions
- Review [DEPLOYMENT_CHECKLIST](aws-deployment/DEPLOYMENT_CHECKLIST.md) for troubleshooting
- Check CloudWatch logs for application errors

---

Last Updated: November 28, 2025
