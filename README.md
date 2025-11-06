# T3 Dashboard and Reporting Project

A cloud-based business intelligence system for analyzing food truck performance data, built with AWS, Python, and Streamlit.

## Description

The T3 Dashboard and Reporting Project provides real-time analytics and automated reporting for food truck operations. The system extracts transactional data from a MySQL database, processes it through a data pipeline, stores it in a scalable data lake, and presents insights through an interactive web dashboard and daily email reports.

## Features

- **Interactive Dashboard**: Streamlit-based web interface with real-time data visualization
  - Multi-truck performance comparison
  - Cumulative revenue tracking
  - Payment method distribution (cash vs. card)
  - Hourly transaction analysis
  - Best/worst performing truck identification

- **Automated Data Pipeline**: Incremental data extraction and loading
  - Periodic refresh every 3 hours
  - Data validation and quality checks
  - Efficient Parquet storage with partitioning
  - State management via AWS Parameter Store

- **Daily Business Reports**: Comprehensive HTML reports via email
  - Executive summary with key metrics
  - Cost reduction analysis (underperforming trucks)
  - Profit optimization recommendations
  - Price point demand segmentation

- **Scalable AWS Architecture**:
  - S3 Data Lake for cost-effective storage
  - AWS Glue for automatic schema detection
  - Athena for SQL analytics
  - ECS Fargate for containerized deployments
  - Lambda for serverless report generation

## Installation

### Clone the Repository

```bash
git clone <repository-url>
cd "T3 Dashboard and Reporting Project"
```

### Set Up Environment Variables

Create `.env` files in the appropriate directories with the following configuration:

**For `pipeline/.env`, `pipeline_periodic/.env`, and `dashboard/.env`:**
```bash
AWS_REGION=eu-west-2
AWS_ACCOUNT_ID=<your-account-id>
DB_HOST=<your-rds-endpoint>
DB_USER=<database-username>
DB_PASSWORD=<database-password>
DB_NAME=<database-name>
DB_PORT=3306
```

**For `bash_scripts/.env`:**
```bash
AWS_REGION=eu-west-2
ECR_URL_DASHBOARD=<ecr-dashboard-repository-url>
ECR_URL_PERIODIC_PIPELINE=<ecr-pipeline-repository-url>
ECR_URL_REPORT_LAMBDA=<ecr-lambda-repository-url>
```

### Install Dependencies

**Option 1: Local Python Environment**
```bash
cd dashboard
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Note:** You'll need to create a `terraform.tfvars` file with your database credentials and email addresses:
```hcl
db_host                  = "your-rds-endpoint"
db_port                  = "3306"
db_name                  = "your-database"
db_user                  = "your-username"
db_password              = "your-password"
report_sender_email      = "sender@example.com"
report_recipient_email   = "recipient@example.com"
```

### Running the Dashboard Locally

```bash
cd dashboard
streamlit run dashboard.py --server.port 8501
```

Visit `http://localhost:8501` in your browser to view the dashboard.

**Access Deployed Dashboard:**

Once deployed via Terraform, the dashboard will be accessible at the ECS Fargate public IP on port 8501.

### Scheduled Operations

After deployment, the following operations run automatically:

- **Data Refresh**: Every 3 hours (00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00 UTC)
- **Glue Crawler**: Daily at 01:00 UTC (updates data catalog)
- **Business Reports**: Daily at 09:30 UTC (email delivery)

## Project Structure

```
T3 Dashboard and Reporting Project/
│
├── dashboard/                      # Interactive Streamlit web dashboard
│   ├── dashboard.py                # Main application entry point
│   ├── dashboard_helper.py         # Data access and Athena queries
│   ├── Dockerfile                  # Container configuration
│   ├── requirements.txt            # Python dependencies
│   └── .env                        # Environment variables
│
├── pipeline/                       # Initial data extraction pipeline
│   ├── extract_and_clean.py        # RDS data extraction and cleaning
│   ├── upload_to_s3.py             # Parquet conversion and S3 upload
│   ├── Dockerfile                  # Container configuration
│   ├── requirements.txt            # Python dependencies
│   └── data/                       # Local CSV storage (intermediate)
│
├── pipeline_periodic/              # Incremental data refresh pipeline
│   ├── extract_and_upload_periodic.py  # Fetch new transactions
│   ├── Dockerfile                  # Container configuration
│   ├── requirements.txt            # Python dependencies
│   └── .env                        # Environment variables
│
├── reports/                        # Daily business intelligence reports
│   ├── generate_html_report.py     # Lambda function for report generation
│   ├── Dockerfile                  # Lambda container image
│   └── requirements.txt            # Python dependencies
│
├── terraform/                      # Core infrastructure as code
│   ├── main.tf                     # S3, Glue, Athena, ECS, ECR configs
│   ├── terraform.tf                # Provider configuration
│   └── variables.tf                # Input variables
│
├── terraform_periodic/             # Scheduled jobs infrastructure
│   ├── main.tf                     # Lambda, EventBridge, Step Functions
│   ├── terraform.tf                # Provider configuration
│   └── variables.tf                # Input variables
│
├── bash_scripts/                   # Deployment automation scripts
│   ├── create_pipeline_image.bash
│   ├── create_dashboard_fargate_image.bash
│   ├── push_dashboard_image_to_ecr.bash
│   ├── push_periodic_pipeline_image.bash
│   ├── push_report_lambda_image.bash
│   └── .env                        # AWS credentials and ECR URLs
│
├── preliminary_analysis/           # Initial data insights
│   └── t3_recommendations.md       # Business recommendations
│
├── CLAUDE.md                       # AI assistant guidance
└── README.md                       # This file
```

## Requirements

### Software & Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.13+ | Application runtime |
| Docker | Latest | Containerization |
| Terraform | Latest | Infrastructure provisioning |
| AWS CLI | Latest | AWS resource management |
| Streamlit | Latest | Dashboard framework |

### AWS Services

- **Compute**: ECS Fargate, Lambda
- **Storage**: S3, RDS MySQL
- **Analytics**: Glue, Athena
- **Orchestration**: EventBridge, Step Functions
- **Networking**: VPC, Security Groups
- **Monitoring**: CloudWatch
- **Container Registry**: ECR
- **Email**: SES
- **Configuration**: Systems Manager Parameter Store

### Python Libraries

**Dashboard:**
- `streamlit` - Web application framework
- `pandas` - Data manipulation
- `plotly` - Interactive visualizations
- `awswrangler` - AWS data integration
- `boto3` - AWS SDK

**Pipeline:**
- `pandas` - Data processing
- `PyMySQL` - MySQL database connector
- `awswrangler` - S3 and Glue integration
- `python-dotenv` - Environment management

**Reports:**
- `pandas` - Data analysis
- `awswrangler` - Athena queries
- `boto3` - AWS SDK


## Acknowledgments

Built with modern cloud technologies and data engineering best practices. Special thanks to the AWS ecosystem for providing scalable, cost-effective infrastructure components.

---

**Live Dashboard**: `http://18.130.208.234:8501/` (when deployed)
