# AWS Deployment Checklist

## Pre-Deployment Setup

- [ ] AWS CLI installed and configured
  ```bash
  aws --version
  aws sts get-caller-identity  # Verify credentials
  ```

- [ ] Docker installed and running
  ```bash
  docker --version
  docker ps
  ```

- [ ] PostgreSQL client tools installed
  ```bash
  psql --version
  pg_dump --version
  ```

- [ ] Review and update AWS credentials in `backend/.env`
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_DEFAULT_REGION

## Step-by-Step Deployment

### 1. Create RDS Database ✓

```bash
cd "/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment"
./01-setup-rds.sh
```

**Verification**:
- [ ] Script completes without errors
- [ ] RDS endpoint is displayed
- [ ] Credentials saved to `backend/.env.rds`
- [ ] **IMPORTANT**: Copy and save database password securely!

**Expected output**:
```
RDS Instance Created Successfully!
Endpoint: synthetic-audience-db.<random>.us-west-2.rds.amazonaws.com
...
```

---

### 2. Export Local Database ✓

```bash
./02-export-database.sh
```

**Verification**:
- [ ] Script completes without errors
- [ ] Files created in `aws-deployment/db-export/`:
  - [ ] schema.sql
  - [ ] data.sql
  - [ ] complete_backup.dump
  - [ ] table_list.txt
  - [ ] table_stats.txt

**Check data**:
```bash
ls -lh aws-deployment/db-export/
```

---

### 3. Import to RDS ✓

```bash
./03-import-to-rds.sh
```

**Verification**:
- [ ] Connection to RDS successful
- [ ] pgvector extension installed
- [ ] Schema imported
- [ ] Data imported
- [ ] Table count matches local database
- [ ] Persona count matches local database

**Manual verification**:
```bash
# Connect to RDS
source backend/.env.rds
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Check tables
\dt

# Check persona count
SELECT COUNT(*) FROM personas;

# Exit
\q
```

---

### 4. Build and Push Docker Images ✓

```bash
./04-build-and-push-images.sh
```

**Verification**:
- [ ] ECR repositories created
- [ ] Backend image built successfully
- [ ] Frontend image built successfully
- [ ] Backend image pushed to ECR
- [ ] Frontend image pushed to ECR
- [ ] Image URIs saved to `image-uris.env`

**Manual verification**:
```bash
# List ECR repositories
aws ecr describe-repositories --region us-west-2

# List images in backend repo
aws ecr describe-images --repository-name synthetic-audience-backend --region us-west-2

# List images in frontend repo
aws ecr describe-images --repository-name synthetic-audience-frontend --region us-west-2
```

---

### 5. Deploy to ECS ✓

```bash
./05-deploy-ecs.sh
```

**Verification**:
- [ ] ECS cluster created
- [ ] IAM roles created
- [ ] Security groups configured
- [ ] Application Load Balancer created
- [ ] Target groups created
- [ ] ALB listeners configured
- [ ] Task definitions registered
- [ ] ECS services created and running

**Manual verification**:
```bash
# Check cluster
aws ecs describe-clusters --clusters synthetic-audience-cluster --region us-west-2

# Check services
aws ecs list-services --cluster synthetic-audience-cluster --region us-west-2

# Check tasks (should show RUNNING)
aws ecs list-tasks --cluster synthetic-audience-cluster --region us-west-2

# Get ALB DNS
aws elbv2 describe-load-balancers \
    --names synthetic-audience-alb \
    --region us-west-2 \
    --query 'LoadBalancers[0].DNSName' \
    --output text
```

**Test the deployment**:
```bash
# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers --names synthetic-audience-alb --region us-west-2 --query 'LoadBalancers[0].DNSName' --output text)

# Test frontend
curl http://$ALB_DNS/

# Test backend health
curl http://$ALB_DNS/api/health

# Test backend API
curl http://$ALB_DNS/api/audience/personas
```

---

### 6. Configure HTTPS (Optional but Recommended)

#### Option A: With Custom Domain

1. **Request SSL Certificate**:
   ```bash
   aws acm request-certificate \
       --domain-name yourdomain.com \
       --validation-method DNS \
       --region us-west-2
   ```

2. **Get certificate ARN** (after DNS validation):
   ```bash
   aws acm list-certificates --region us-west-2
   ```

3. **Create HTTPS listener**:
   ```bash
   # Get ALB ARN
   ALB_ARN=$(aws elbv2 describe-load-balancers --names synthetic-audience-alb --region us-west-2 --query 'LoadBalancers[0].LoadBalancerArn' --output text)

   # Get target group ARN
   FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups --names synthetic-audience-frontend-tg --region us-west-2 --query 'TargetGroups[0].TargetGroupArn' --output text)

   # Create HTTPS listener
   aws elbv2 create-listener \
       --load-balancer-arn $ALB_ARN \
       --protocol HTTPS \
       --port 443 \
       --certificates CertificateArn=<your-certificate-arn> \
       --default-actions Type=forward,TargetGroupArn=$FRONTEND_TG_ARN \
       --region us-west-2
   ```

4. **Update DNS** to point your domain to ALB

#### Option B: Without Custom Domain

Use ALB DNS directly: `http://<alb-dns>`

---

### 7. Set Up CloudFront (Optional)

```bash
# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers --names synthetic-audience-alb --region us-west-2 --query 'LoadBalancers[0].DNSName' --output text)

# Create CloudFront distribution
aws cloudfront create-distribution \
    --origin-domain-name $ALB_DNS \
    --default-root-object index.html \
    --enabled \
    --comment "Synthetic Audience Platform"
```

**Verification**:
- [ ] CloudFront distribution created
- [ ] Distribution status: Deployed
- [ ] Get CloudFront domain name for access

---

## Post-Deployment Checks

### Application Health

- [ ] Frontend accessible at ALB DNS or CloudFront domain
- [ ] Backend API responding at `/api/health`
- [ ] Can create new personas
- [ ] Can chat with personas
- [ ] Database queries working

### AWS Resources

- [ ] ECS tasks running (check in ECS console)
- [ ] ALB target groups healthy
- [ ] RDS instance available
- [ ] CloudWatch logs being created

### Monitoring Setup

- [ ] Set up CloudWatch alarms for:
  - [ ] ECS CPU/Memory utilization
  - [ ] ALB target health
  - [ ] RDS CPU/Connections
  - [ ] ECS service desired count

### Security

- [ ] Security groups properly configured
- [ ] Database credentials stored securely (consider Secrets Manager)
- [ ] IAM roles follow least privilege
- [ ] Enable RDS encryption
- [ ] Enable ALB access logs

---

## Troubleshooting

### If ECS tasks keep restarting:

1. Check CloudWatch logs:
   ```bash
   aws logs tail /ecs/synthetic-audience-backend --follow --region us-west-2
   ```

2. Check task definition environment variables

3. Verify database connection from ECS

### If ALB shows 502/503 errors:

1. Check target group health:
   ```bash
   aws elbv2 describe-target-health --target-group-arn <tg-arn> --region us-west-2
   ```

2. Verify security groups allow ALB → ECS traffic

3. Check application health endpoint

### If database connection fails:

1. Verify security group allows ECS → RDS traffic

2. Test connection from ECS task:
   ```bash
   # Execute into running task
   aws ecs execute-command \
       --cluster synthetic-audience-cluster \
       --task <task-id> \
       --container backend \
       --interactive \
       --command "/bin/bash"

   # Inside container
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME
   ```

---

## Rollback Plan

If deployment fails:

1. **Stop ECS services**:
   ```bash
   aws ecs update-service --cluster synthetic-audience-cluster --service synthetic-audience-backend --desired-count 0 --region us-west-2
   aws ecs update-service --cluster synthetic-audience-cluster --service synthetic-audience-frontend --desired-count 0 --region us-west-2
   ```

2. **Keep RDS instance** (has your data)

3. **Delete other resources** if needed (see README cleanup section)

4. **Investigate logs** in CloudWatch

5. **Fix issues** and redeploy

---

## Success Criteria

✅ **Deployment is successful when**:

1. ECS tasks are RUNNING and stable
2. ALB target groups show healthy targets
3. Frontend is accessible via browser
4. Backend API returns valid responses
5. Can perform all core functions:
   - Generate personas
   - Chat with personas
   - View persona details
   - Create audience groups

---

## Next Steps After Deployment

1. **Set up monitoring and alerts**
2. **Configure auto-scaling** for ECS services
3. **Set up CI/CD pipeline** for automated deployments
4. **Enable backups** for RDS
5. **Set up custom domain** and SSL certificate
6. **Configure CloudFront** for global distribution
7. **Implement cost optimization**:
   - Use Fargate Spot for non-critical tasks
   - Set up RDS snapshots retention policy
   - Enable S3 lifecycle policies for logs

---

## Support Contacts

- **AWS Support**: https://console.aws.amazon.com/support/
- **Documentation**: See README.md in this directory

---

**Deployment Date**: _________________

**Deployed By**: _________________

**Production URL**: _________________

**RDS Endpoint**: _________________

**CloudFront Domain**: _________________
