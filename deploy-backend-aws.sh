#!/bin/bash

# AWS Backend Deployment Script for Geo-Political Data Platform
# This script sets up the complete AWS infrastructure for the backend

set -e  # Exit on any error

# Configuration - UPDATE THESE VALUES
AWS_REGION="us-east-1"
PROJECT_NAME="geopolitical-data-platform"
DB_NAME="geopolitical_data"
DB_USERNAME="geoadmin"
DB_PASSWORD="Lumpcrab$2005"  # Change this!
ECR_REPOSITORY_NAME="geopolitical-backend"
ECS_CLUSTER_NAME="geopolitical-cluster"
ECS_SERVICE_NAME="geopolitical-service"

echo "🚀 Starting AWS Backend Deployment for Geo-Political Data Platform"
echo "Region: $AWS_REGION"
echo "Project: $PROJECT_NAME"

# Step 1: Create VPC and networking
echo "🌐 Creating VPC and networking infrastructure..."

VPC_ID=$(aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$PROJECT_NAME-vpc}]" \
    --query 'Vpc.VpcId' \
    --output text \
    --region $AWS_REGION)

echo "Created VPC: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames --region $AWS_REGION

# Create Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
    --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$PROJECT_NAME-igw}]" \
    --query 'InternetGateway.InternetGatewayId' \
    --output text \
    --region $AWS_REGION)

aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID --region $AWS_REGION

# Create public subnets
PUBLIC_SUBNET_1=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone ${AWS_REGION}a \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public-1}]" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

PUBLIC_SUBNET_2=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.2.0/24 \
    --availability-zone ${AWS_REGION}b \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public-2}]" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

# Create private subnets for database
PRIVATE_SUBNET_1=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.3.0/24 \
    --availability-zone ${AWS_REGION}a \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private-1}]" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

PRIVATE_SUBNET_2=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.4.0/24 \
    --availability-zone ${AWS_REGION}b \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private-2}]" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

# Create route table for public subnets
ROUTE_TABLE_ID=$(aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=$PROJECT_NAME-public-rt}]" \
    --query 'RouteTable.RouteTableId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID --region $AWS_REGION
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_1 --route-table-id $ROUTE_TABLE_ID --region $AWS_REGION
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_2 --route-table-id $ROUTE_TABLE_ID --region $AWS_REGION

echo "✅ VPC and networking setup complete"

# Step 2: Create security groups
echo "🔒 Creating security groups..."

# ALB Security Group
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name $PROJECT_NAME-alb-sg \
    --description "Security group for Application Load Balancer" \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$PROJECT_NAME-alb-sg}]" \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION

# ECS Security Group
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name $PROJECT_NAME-ecs-sg \
    --description "Security group for ECS tasks" \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$PROJECT_NAME-ecs-sg}]" \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 5000 \
    --source-group $ALB_SG_ID \
    --region $AWS_REGION

# RDS Security Group
RDS_SG_ID=$(aws ec2 create-security-group \
    --group-name $PROJECT_NAME-rds-sg \
    --description "Security group for RDS database" \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$PROJECT_NAME-rds-sg}]" \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $ECS_SG_ID \
    --region $AWS_REGION

echo "✅ Security groups created"

# Step 3: Create RDS subnet group and database
echo "🗄️ Creating RDS database..."

#aws rds create-db-subnet-group \
    #--db-subnet-group-name $PROJECT_NAME-db-subnet-group \
    #--db-subnet-group-description "Subnet group for $PROJECT_NAME database" \
    #--subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
    #--tags Key=Name,Value=$PROJECT_NAME-db-subnet-group \
    #--region $AWS_REGION

aws rds create-db-instance \
    --db-instance-identifier $PROJECT_NAME-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.7 \
    --master-username $DB_USERNAME \
    --master-user-password $DB_PASSWORD \
    --allocated-storage 20 \
    --vpc-security-group-ids $RDS_SG_ID \
    --db-subnet-group-name $PROJECT_NAME-db-subnet-group \
    --db-name $DB_NAME \
    --backup-retention-period 7 \
    --storage-encrypted \
    --tags Key=Name,Value=$PROJECT_NAME-database \
    --region $AWS_REGION

echo "⏳ RDS database creation initiated (this may take 10-15 minutes)..."

# Step 4: Create ECR repository
echo "📦 Creating ECR repository..."

aws ecr create-repository \
    --repository-name $ECR_REPOSITORY_NAME \
    --region $AWS_REGION

# Get ECR login token
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

echo "✅ ECR repository created"

# Step 5: Create ECS cluster
echo "🐳 Creating ECS cluster..."

aws ecs create-cluster \
    --cluster-name $ECS_CLUSTER_NAME \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    --tags key=Name,value=$PROJECT_NAME-cluster \
    --region $AWS_REGION

echo "✅ ECS cluster created"

# Step 6: Create Application Load Balancer
echo "⚖️ Creating Application Load Balancer..."

ALB_ARN=$(aws elbv2 create-load-balancer \
    --name $PROJECT_NAME-alb \
    --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 \
    --security-groups $ALB_SG_ID \
    --tags Key=Name,Value=$PROJECT_NAME-alb \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text \
    --region $AWS_REGION)

# Create target group
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name $PROJECT_NAME-tg \
    --protocol HTTP \
    --port 5000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /api/health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --tags Key=Name,Value=$PROJECT_NAME-target-group \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text \
    --region $AWS_REGION)

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
    --region $AWS_REGION

echo "✅ Application Load Balancer created"

# Output important information
echo ""
echo "🎉 AWS Infrastructure Setup Complete!"
echo "================================================"
echo "VPC ID: $VPC_ID"
echo "Public Subnets: $PUBLIC_SUBNET_1, $PUBLIC_SUBNET_2"
echo "Private Subnets: $PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2"
echo "ALB Security Group: $ALB_SG_ID"
echo "ECS Security Group: $ECS_SG_ID"
echo "RDS Security Group: $RDS_SG_ID"
echo "ECR Repository: $ECR_REPOSITORY_NAME"
echo "ECS Cluster: $ECS_CLUSTER_NAME"
echo "Target Group ARN: $TARGET_GROUP_ARN"
echo ""
echo "📋 Next Steps:"
echo "1. Wait for RDS database to be available (check AWS console)"
echo "2. Build and push Docker image to ECR"
echo "3. Create ECS task definition and service"
echo "4. Configure environment variables with database connection"
echo ""
echo "💡 Save these values for the next deployment steps!"

# Save configuration to file
cat > aws-infrastructure-config.txt << EOF
VPC_ID=$VPC_ID
PUBLIC_SUBNET_1=$PUBLIC_SUBNET_1
PUBLIC_SUBNET_2=$PUBLIC_SUBNET_2
PRIVATE_SUBNET_1=$PRIVATE_SUBNET_1
PRIVATE_SUBNET_2=$PRIVATE_SUBNET_2
ALB_SG_ID=$ALB_SG_ID
ECS_SG_ID=$ECS_SG_ID
RDS_SG_ID=$RDS_SG_ID
ECR_REPOSITORY_NAME=$ECR_REPOSITORY_NAME
ECS_CLUSTER_NAME=$ECS_CLUSTER_NAME
TARGET_GROUP_ARN=$TARGET_GROUP_ARN
ALB_ARN=$ALB_ARN
DB_NAME=$DB_NAME
DB_USERNAME=$DB_USERNAME
AWS_REGION=$AWS_REGION
PROJECT_NAME=$PROJECT_NAME
EOF

echo "💾 Configuration saved to aws-infrastructure-config.txt"

