FROM python:3.13-alpine

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy Python scripts
COPY dashboard.py .
COPY dashboard_helper.py .

# Run the streamlit dashboard
CMD streamlit run dashboard.py --server.port 8501