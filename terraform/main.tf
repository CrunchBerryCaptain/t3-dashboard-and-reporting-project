provider "aws" {
  region = "eu-west-2"
}

# S3 Bucket for T3 Data Lake
resource "aws_s3_bucket" "data_bucket" {
  bucket = "c20-muarij-t3-data-lake"
  force_destroy = true
}

# Glue Catalog Database
resource "aws_glue_catalog_database" "t3_db" {
  name = "c20-muarij-t3-glue-db"
}

# IAM Role for Glue Crawler
resource "aws_iam_role" "glue_crawler_role" {
  name = "c20-muarij-t3-glue-crawler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

# Glue Crawler IAM Policy for S3 access
resource "aws_iam_role_policy" "glue_s3_policy" {
  name = "c20-muarij-t3-glue-s3-access"
  role = aws_iam_role.glue_crawler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::c20-muarij-t3-data-lake",
          "arn:aws:s3:::c20-muarij-t3-data-lake/*"
        ]
      }
    ]
  })
}

# Attach AWS managed policy for Glue
resource "aws_iam_role_policy_attachment" "glue_service_policy" {
  role       = aws_iam_role.glue_crawler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Glue Crawler
resource "aws_glue_crawler" "t3_crawler" {
  name          = "c20-muarij-t3-crawler"
  role          = aws_iam_role.glue_crawler_role.arn
  database_name = aws_glue_catalog_database.t3_db.name

  s3_target {
    path = "s3://c20-muarij-t3-data-lake/"
    exclusions = [
      "athena_output/**" # Exclude Athena output files
    ]
  }

  schedule = "cron(0 1 * * ? *)"  # Runs daily at 1:00 AM UTC
}

# Athena Workgroup
resource "aws_athena_workgroup" "primary" {
  name = "c20-muarij-t3-athena-workgroup"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_bucket.bucket}/athena_output/"
    }
  }
}

# ECR Repository for Streamlit Dashboard
resource "aws_ecr_repository" "dashboard_repo" {
  name                 = "c20-muarij-t3-streamlit-dashboard"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
}

output "ecr_repository_url" {
  value = aws_ecr_repository.dashboard_repo.repository_url
}

# ECS Cluster for Streamlit Dashboard (Where am I running my containers?)
resource "aws_ecs_cluster" "dashboard_cluster" {
  name = "c20-muarij-streamlit-dashboard-cluster"
}

# ECS Service for Streamlit Dashboard (How am I running my containers?)
resource "aws_ecs_service" "streamlit_service" {
  name            = "streamlit-service"
  cluster         = aws_ecs_cluster.dashboard_cluster.id
  task_definition = aws_ecs_task_definition.streamlit_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = ["subnet-0c47ef6fc81ba084a", "subnet-0c2e92c1b7b782543", "subnet-00c68b4e0ee285460"]
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }
}

# ECS Task Definition for Streamlit Dashboard (What is inside my container? How are the resources allocated?)
resource "aws_ecs_task_definition" "streamlit_task" {
  family                   = "c20-muarij-streamlit-dashboard"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"  # 0.25 vCPU
  memory                   = "512"  # 512 MB
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "c20-muarij-streamlit-container"
      image     = "${aws_ecr_repository.dashboard_repo.repository_url}:latest"
      essential = true
      
      portMappings = [
        {
          containerPort = 8501
          hostPort      = 8501
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "AWS_DEFAULT_REGION"
          value = "eu-west-2"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/c20-muarij-streamlit-dashboard"
          "awslogs-region"        = "eu-west-2"
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
        }
      }
    }
  ])
}

# ECS Task Execution Role (The hat that ECS wears when spinning up your task)
resource "aws_iam_role" "ecs_execution_role" {
  name = "c20-muarij-streamlit-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# Attach AWS managed policy for ECS task execution (What permissions am I giving to the person wearing the 'execution-role' hat?)
resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Policy for ECS Task Execution Role to allow CloudWatch Logs
resource "aws_iam_role_policy" "ecs_execution_logs" {
  name = "c20-muarij-ecs-task-execution-logs"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Role for ECS Task (The hat the task wears when running your container)
resource "aws_iam_role" "ecs_task_role" {
  name = "c20-muarij-streamlit-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# ECS Task IAM Policy with permissions (What permissions am I giving to the person wearing the 'task-role' hat?)
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "c20-muarij-streamlit-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution",
          "athena:GetWorkGroup"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::c20-muarij-t3-data-lake",
          "arn:aws:s3:::c20-muarij-t3-data-lake/*"
        ]
      }
    ]
  })
}

# Security Group for ECS tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "c20-muarij-streamlit-ecs-tasks"
  description = "Allow inbound traffic to Streamlit"
  vpc_id      = "vpc-01b7a51a09d27de04" # C20 Shared VPC

  ingress {
    description = "Streamlit port"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}