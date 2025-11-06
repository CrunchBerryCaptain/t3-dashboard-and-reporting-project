# pylint: disable=invalid-name

""" Upload script that uses AWS Wrangler to upload 
CSV data to time-partitioned S3 buckets in Parquet format. """

import pandas as pd
import awswrangler as wr

PAYMENT_DATA_LOCAL_PATH = './data/payment_data.csv'
TRANSACTION_DATA_LOCAL_PATH = './data/transaction_data.csv'
TRUCK_DATA_LOCAL_PATH = './data/truck_data.csv'

TRANSACTION_S3_PATH = 's3://c20-muarij-t3-data-lake/transaction_table/'
ROOT_S3_PATH = 's3://c20-muarij-t3-data-lake/'


def upload_transactions_to_s3():
    """ Upload transactions data to S3 in Parquet format with partitioning """

    transaction_df = pd.read_csv(TRANSACTION_DATA_LOCAL_PATH)
    transaction_df['at'] = pd.to_datetime(transaction_df['at'])

    # Extract date components for partitioning
    transaction_df['year'] = transaction_df['at'].dt.year
    transaction_df['month'] = transaction_df['at'].dt.month
    transaction_df['day'] = transaction_df['at'].dt.day

    # Write to S3 with partitioning
    wr.s3.to_parquet(
        df=transaction_df,
        path=TRANSACTION_S3_PATH,
        dataset=True,
        partition_cols=['year', 'month', 'day'],
        mode='overwrite'
    )


def upload_dimensions_to_s3():
    """ Upload dimensions data (Truck data + Payment data) 
    to S3 in Parquet format without partitioning """

    truck_df = pd.read_csv(TRUCK_DATA_LOCAL_PATH)

    # Write truck data to S3 without partitioning
    wr.s3.to_parquet(
        df=truck_df,
        path=ROOT_S3_PATH + 'truck_table/',
        dataset=True,
        mode='overwrite'
    )

    payment_df = pd.read_csv(PAYMENT_DATA_LOCAL_PATH)

    # Write payment data to S3 without partitioning
    wr.s3.to_parquet(
        df=payment_df,
        path=ROOT_S3_PATH + 'payment_table/',
        dataset=True,
        mode='overwrite'
    )


if __name__ == "__main__":
    upload_transactions_to_s3()
    print("Uploaded transactions data to S3.")
    upload_dimensions_to_s3()
    print("Uploaded dimensions data to S3.")
