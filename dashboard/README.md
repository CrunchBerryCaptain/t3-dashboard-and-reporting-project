# Dashboard

Instructions for running the Streamlit dashboard both locally and via AWS ECS.

## How to Run

### Locally

If running locally, please follow these steps to set up and run the dashboard:

1. Create a venv and activate it:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the Streamlit dashboard on a specified port (e.g., 8501):

   ```bash
   streamlit run dashboard.py --server.port 8501
   ```

### Through AWS ECS

The Streamlit dashboard is hosted on AWS's Elastic Container Service and can be accessed via a web browser.

Simply go to the following URL in your browser:

```
http://18.130.208.234:8501/
``` 