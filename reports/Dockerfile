# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.13

# Set working directory to Lambda task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the Lambda function code
COPY generate_html_report.py .

# Set the CMD to your handler
CMD ["generate_html_report.lambda_handler"]
