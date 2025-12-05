#!/bin/bash

# Docker Build and Push Script for AWS ECR
# Run this after the infrastructure setup is complete

set -e

# Load configuration
source aws-infrastructure-config.txt

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME"

echo "🐳 Building and pushing Docker image to ECR..."
echo "ECR URI: $ECR_URI"

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t $ECR_REPOSITORY_NAME .

# Tag image for ECR
docker tag $ECR_REPOSITORY_NAME:latest $ECR_URI:latest

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

# Push image
echo "📤 Pushing image to ECR..."
docker push $ECR_URI:latest

echo "✅ Docker image pushed successfully!"
echo "Image URI: $ECR_URI:latest"

# Wait for RDS to be available
echo "⏳ Checking RDS database status..."
aws rds wait db-instance-available --db-instance-identifier $PROJECT_NAME-db --region $AWS_REGION
echo "✅ RDS database is now available!"

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $PROJECT_NAME-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text \
    --region $AWS_REGION)

echo "📍 RDS Endpoint: $RDS_ENDPOINT"

# Create Secrets Manager secrets
echo "🔐 Creating secrets in AWS Secrets Manager..."

# Database URL secret
DATABASE_URL="postgresql://$DB_USERNAME:$DB_PASSWORD@$RDS_ENDPOINT:5432/$DB_NAME"
aws secretsmanager create-secret \
    --name "$PROJECT_NAME-database-url" \
    --description "Database URL for $PROJECT_NAME" \
    --secret-string "$DATABASE_URL" \
    --region $AWS_REGION

# Secret key
SECRET_KEY=$(openssl rand -base64 32)
aws secretsmanager create-secret \
    --name "$PROJECT_NAME-secret-key" \
    --description "Flask secret key for $PROJECT_NAME" \
    --secret-string "$SECRET_KEY" \
    --region $AWS_REGION

echo "✅ Secrets created in AWS Secrets Manager"

# Create IAM roles for ECS
echo "👤 Creating IAM roles..."

# ECS Task Execution Role
cat > ecs-task-execution-role-trust-policy.json << EOF
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

aws iam create-role \
    --role-name $PROJECT_NAME-ecs-execution-role \
    --assume-role-policy-document file://ecs-task-execution-role-trust-policy.json \
    --region $AWS_REGION

aws iam attach-role-policy \
    --role-name $PROJECT_NAME-ecs-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
    --region $AWS_REGION

# ECS Task Role
aws iam create-role \
    --role-name $PROJECT_NAME-ecs-task-role \
    --assume-role-policy-document file://ecs-task-execution-role-trust-policy.json \
    --region $AWS_REGION

# Create policy for accessing secrets
cat > ecs-secrets-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:$AWS_REGION:$ACCOUNT_ID:secret:$PROJECT_NAME-database-url*",
                "arn:aws:secretsmanager:$AWS_REGION:$ACCOUNT_ID:secret:$PROJECT_NAME-secret-key*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name $PROJECT_NAME-secrets-policy \
    --policy-document file://ecs-secrets-policy.json \
    --region $AWS_REGION

aws iam attach-role-policy \
    --role-name $PROJECT_NAME-ecs-execution-role \
    --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/$PROJECT_NAME-secrets-policy \
    --region $AWS_REGION

echo "✅ IAM roles created"

# Create ECS task definition
echo "📋 Creating ECS task definition..."

cat > ecs-task-definition.json << EOF
{
  "family": "$PROJECT_NAME",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/$PROJECT_NAME-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/$PROJECT_NAME-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "geopolitical-backend",
      "image": "$ECR_URI:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        },
        {
          "name": "PORT",
          "value": "5000"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$ACCOUNT_ID:secret:$PROJECT_NAME-database-url"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$ACCOUNT_ID:secret:$PROJECT_NAME-secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$PROJECT_NAME",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:5000/api/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Create CloudWatch log group
aws logs create-log-group \
    --log-group-name "/ecs/$PROJECT_NAME" \
    --region $AWS_REGION

# Register task definition
TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition.json \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text \
    --region $AWS_REGION)

echo "✅ ECS task definition registered: $TASK_DEFINITION_ARN"

# Create ECS service
echo "🚀 Creating ECS service..."

aws ecs create-service \
    --cluster $ECS_CLUSTER_NAME \
    --service-name $ECS_SERVICE_NAME \
    --task-definition $TASK_DEFINITION_ARN \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNET_1,$PUBLIC_SUBNET_2],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=geopolitical-backend,containerPort=5000" \
    --region $AWS_REGION

echo "✅ ECS service created"

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query 'LoadBalancers[0].DNSName' \
    --output text \
    --region $AWS_REGION)

echo ""
echo "🎉 Backend Deployment Complete!"
echo "================================="
echo "Application Load Balancer DNS: $ALB_DNS"
echo "API Health Check: http://$ALB_DNS/api/health"
echo "API Root: http://$ALB_DNS/api/"
echo ""
echo "📋 Next Steps:"
echo "1. Test the API endpoints"
echo "2. Configure your custom domain to point to the ALB"
echo "3. Set up SSL certificate"
echo "4. Deploy the frontend"

# Update configuration file
cat >> aws-infrastructure-config.txt << EOF
RDS_ENDPOINT=$RDS_ENDPOINT
DATABASE_URL=$DATABASE_URL
ECR_URI=$ECR_URI
TASK_DEFINITION_ARN=$TASK_DEFINITION_ARN
ALB_DNS=$ALB_DNS
EOF

echo "💾 Configuration updated in aws-infrastructure-config.txt"

