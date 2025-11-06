FROM python:3.13-alpine

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Create the shared data directory
RUN mkdir -p data

# Copy Python scripts
COPY extract_and_upload_periodic.py .

# Set up the pipeline execution
CMD python extract_and_upload_periodic.py