provider "aws" {
  region = "eu-west-2"
}

resource "aws_ecr_repository" "etl_pipeline" {
  name                 = "c20-muarij-t3-pipeline-periodic"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true  # Optional: scans for vulnerabilities
  }
}

# Output the repository URL so you know where to push
output "ecr_repository_url" {
  value = aws_ecr_repository.etl_pipeline.repository_url
}

# ECS Task Definition for Periodic Upload (What is inside my container? How are the resources allocated?)
resource "aws_ecs_task_definition" "etl_task" {
  family                   = "c20-muarij-t3-pipeline-periodic"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"  # 0.25 vCPU
  memory                   = "512"  # 512 MB
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "c20-muarij-t3-pipeline-container"
      image     = "${aws_ecr_repository.etl_pipeline.repository_url}:latest"
      essential = true
      
      environment = [
        {
          name  = "AWS_DEFAULT_REGION"
          value = "eu-west-2"
        },
        {
          name  = "DB_HOST"
          value = var.db_host
        },
        {
          name  = "DB_PORT"
          value = var.db_port
        },
        {
          name  = "DB_NAME"
          value = var.db_name
        },
        {
          name  = "DB_USER"
          value = var.db_user
        },
        {
          name  = "DB_PASSWORD"
          value = var.db_password
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/c20-muarij-t3-pipeline-periodic"
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
  name = "c20-muarij-t3-periodic-pipeline-ecs-execution-role"

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

# IAM Policy for ECS Execution Role to allow ECR access
resource "aws_iam_role_policy" "ecs_execution_ecr" {
  name = "c20-muarij-etl-ecr-access"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
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
  name = "c20-muarij-t3-periodic-pipeline-ecs-task-role"

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
  name = "c20-muarij-t3-pipeline-periodic-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter"
        ]
        Resource = "arn:aws:ssm:eu-west-2:129033205317:parameter/c20-muarij-t3-pipeline-last-processed-timestamp"
      }
    ]
  })
}

# Security Group for ECS tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "c20-muarij-t3-pipeline-periodic-sg"
  description = "Allow outbound traffic for ECS tasks"
  vpc_id      = "vpc-01b7a51a09d27de04" # C20 Shared VPC

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# EventBridge Scheduler - triggers every 3 hours
resource "aws_scheduler_schedule" "etl_pipeline_schedule" {
  name       = "c20-muarij-etl-pipeline-schedule"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(0 */3 * * ? *)"

  target {
    arn      = "arn:aws:ecs:eu-west-2:129033205317:cluster/c20-muarij-streamlit-dashboard-cluster"
    role_arn = aws_iam_role.scheduler_ecs_role.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.etl_task.arn
      launch_type         = "FARGATE"
      task_count          = 1
      
      network_configuration {
        subnets          = ["subnet-0c2e92c1b7b782543", "subnet-00c68b4e0ee285460", "subnet-0c47ef6fc81ba084a"]
        security_groups  = [aws_security_group.ecs_tasks.id]
        assign_public_ip = true
      }
    }
  }
}

# IAM Role for Scheduler to invoke ECS
resource "aws_iam_role" "scheduler_ecs_role" {
  name = "c20-muarij-scheduler-ecs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Scheduler to run ECS tasks
resource "aws_iam_role_policy" "scheduler_ecs_policy" {
  name = "c20-muarij-scheduler-ecs-policy"
  role = aws_iam_role.scheduler_ecs_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = aws_ecs_task_definition.etl_task.arn
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_execution_role.arn,
          aws_iam_role.ecs_task_role.arn
        ]
      }
    ]
  })
}

# ==================== LAMBDA REPORT FUNCTION ====================

# ECR Repository for Lambda Report Function
resource "aws_ecr_repository" "report_lambda" {
  name                 = "c20-muarij-t3-report-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Output the Lambda ECR repository URL
output "lambda_ecr_repository_url" {
  value = aws_ecr_repository.report_lambda.repository_url
}

# Output SES email verification status
output "ses_email_verification_status" {
  value = "Please check both emails (${var.report_sender_email} and ${var.report_recipient_email}) and click the verification links from AWS SES to complete email verification."
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_execution_role" {
  name = "c20-muarij-t3-report-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach AWS managed policy for Lambda basic execution (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM Policy for Lambda to access Athena, S3, and Glue
resource "aws_iam_role_policy" "lambda_data_access" {
  name = "c20-muarij-t3-report-lambda-data-access"
  role = aws_iam_role.lambda_execution_role.id

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

# Lambda Function using Container Image
resource "aws_lambda_function" "report_generator" {
  function_name = "c20-muarij-t3-report-generator"
  role          = aws_iam_role.lambda_execution_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.report_lambda.repository_url}:latest"

  timeout     = 120  # 2 minutes
  memory_size = 1024 # 1 GB
}

# SES Email Identity Verification for Sender
resource "aws_ses_email_identity" "report_sender" {
  email = var.report_sender_email
}

# SES Email Identity Verification for Recipient
resource "aws_ses_email_identity" "report_recipient" {
  email = var.report_recipient_email
}

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions_role" {
  name = "c20-muarij-t3-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Step Functions to invoke Lambda and SES
resource "aws_iam_role_policy" "step_functions_policy" {
  name = "c20-muarij-t3-step-functions-policy"
  role = aws_iam_role.step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.report_generator.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
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

# Step Functions State Machine
resource "aws_sfn_state_machine" "report_workflow" {
  name     = "c20-muarij-t3-report-workflow"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = jsonencode({
    Comment = "Daily report generation and email workflow"
    StartAt = "GenerateReport"
    States = {
      GenerateReport = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.report_generator.function_name
          Payload = {
            "input.$" = "$"
          }
        }
        ResultSelector = {
          "reportBody.$" = "$.Payload.body"
          "statusCode.$" = "$.Payload.statusCode"
        }
        Next = "SendEmailNotification"
      }
      SendEmailNotification = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:ses:sendEmail"
        Parameters = {
          Destination = {
            ToAddresses = [var.report_recipient_email]
          }
          Message = {
            Body = {
              Html = {
                "Data.$" = "$.reportBody"
                Charset  = "UTF-8"
              }
            }
            Subject = {
              Data = "T3 Food Truck Daily Business Intelligence Report"
            }
          }
          Source = var.report_sender_email
        }
        End = true
      }
    }
  })
}

# EventBridge Rule - triggers Step Function daily at 9:30 AM UTC
resource "aws_cloudwatch_event_rule" "daily_report_workflow" {
  name                = "c20-muarij-daily-report-workflow-schedule"
  description         = "Trigger Step Function to generate and email daily report"
  schedule_expression = "cron(30 9 * * ? *)"
}

# EventBridge Target - Step Functions State Machine
resource "aws_cloudwatch_event_target" "step_function_target" {
  rule      = aws_cloudwatch_event_rule.daily_report_workflow.name
  target_id = "ReportWorkflowStepFunction"
  arn       = aws_sfn_state_machine.report_workflow.arn
  role_arn  = aws_iam_role.eventbridge_step_functions_role.arn
}

# IAM Role for EventBridge to invoke Step Functions
resource "aws_iam_role" "eventbridge_step_functions_role" {
  name = "c20-muarij-eventbridge-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for EventBridge to start Step Functions execution
resource "aws_iam_role_policy" "eventbridge_step_functions_policy" {
  name = "c20-muarij-eventbridge-step-functions-policy"
  role = aws_iam_role.eventbridge_step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.report_workflow.arn
      }
    ]
  })
}