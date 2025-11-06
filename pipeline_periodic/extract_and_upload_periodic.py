""" Python script for AWS Lambda to extract new data from RDS using
Parameter Store, process it, upload to S3, and update Parameter Store. 
To keep track of which transactions have already been processed. """

import os
import boto3
import pymysql.cursors
import pandas as pd
from pymysql.connections import Connection
from dotenv import load_dotenv
import awswrangler as wr


def get_connection_to_db() -> Connection:
    """ Establish a connection to the RDS database using environment variables"""

    load_dotenv()

    config = os.environ
    connection = pymysql.connect(host=config.get("DB_HOST"),
                                 user=config.get("DB_USER"),
                                 password=config.get("DB_PASSWORD"),
                                 database=config.get("DB_NAME"),
                                 cursorclass=pymysql.cursors.DictCursor)

    return connection


def get_latest_transaction_date() -> str:
    """ Retrieve the latest processed transaction date from AWS Systems Manager Parameter Store """

    ssm = boto3.client('ssm')
    response = ssm.get_parameter(
        Name='c20-muarij-t3-pipeline-last-processed-timestamp')
    LATEST_TRANSACTION_DATE = response['Parameter']['Value']

    return LATEST_TRANSACTION_DATE


def get_latest_transaction_data(conn: Connection) -> pd.DataFrame:
    """ Get new transaction data from RDS newer than the last processed timestamp
        stored in Parameter Store """

    latest_transaction_date = get_latest_transaction_date()

    with conn.cursor() as cur:
        sql_query = f"""
        SELECT * FROM FACT_Transaction
        WHERE at > '{latest_transaction_date}';
        """
        cur.execute(sql_query)
        transaction_df = pd.DataFrame(cur.fetchall())

    return transaction_df


def upload_latest_transactions_to_s3(transaction_df: pd.DataFrame) -> None:
    """ Upload latest transactions data to S3 in Parquet format with partitioning """

    TRANSACTION_S3_PATH = 's3://c20-muarij-t3-data-lake/transaction_table/'

    transaction_df['at'] = pd.to_datetime(transaction_df['at'])

    # Extract date components for partitioning
    transaction_df['year'] = transaction_df['at'].dt.year
    transaction_df['month'] = transaction_df['at'].dt.month
    transaction_df['day'] = transaction_df['at'].dt.day

    # Write to S3 with partitioning, without overwriting entire file structure.
    wr.s3.to_parquet(
        df=transaction_df,
        path=TRANSACTION_S3_PATH,
        dataset=True,
        partition_cols=['year', 'month', 'day'],
        mode='append'
    )


def update_latest_transaction_date(transaction_df: pd.DataFrame) -> None:
    """ Update the latest processed transaction date in AWS Systems Manager Parameter Store """

    if not transaction_df.empty:
        new_date = transaction_df['at'].max().strftime('%Y-%m-%d %H:%M:%S')

        ssm = boto3.client('ssm')
        ssm.put_parameter(
            Name='c20-muarij-t3-pipeline-last-processed-timestamp',
            Value=new_date,
            Type='String',
            Overwrite=True
        )


if __name__ == "__main__":

    conn = get_connection_to_db()
    print("Connection to RDS established.")

    latest_transaction_data = get_latest_transaction_data(conn)
    print(
        f"Retrieved {len(latest_transaction_data)} new transaction records from RDS.")

    if not latest_transaction_data.empty:
        upload_latest_transactions_to_s3(latest_transaction_data)
        print("Uploaded latest transactions to S3.")
        update_latest_transaction_date(latest_transaction_data)
        print("Updated latest transaction date in Parameter Store.")

    conn.close()
    print("Connection to RDS closed.")
