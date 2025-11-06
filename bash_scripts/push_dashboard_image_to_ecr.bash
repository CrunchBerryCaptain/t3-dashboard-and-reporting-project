source .env

# 1. Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL_DASHBOARD

# 2. Tag local image with the ECR repository URL
docker tag c20-muarij-t3-dashboard-fargate:latest $ECR_URL_DASHBOARD:latest

# 3. Push image to ECR
docker push $ECR_URL_DASHBOARD:latest