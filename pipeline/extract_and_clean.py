""" Extract script to download data from the RDS database 
and save each table to its own csv file. """

import os
import pandas as pd
from pandas import DataFrame
import pymysql.cursors
from pymysql.connections import Connection
from dotenv import load_dotenv


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


def get_payment_table(connection: Connection) -> DataFrame:
    """ Get the "DIM_Payment_Method" table from the database as a pandas dataframe"""

    with connection.cursor() as cur:
        sql_query = """
        SELECT * FROM DIM_Payment_Method;
        """
        cur.execute(sql_query)
        payment_df = pd.DataFrame(cur.fetchall())

    return payment_df


def get_truck_table(connection: Connection) -> DataFrame:
    """ Get the "DIM_Truck" table from the database as a pandas dataframe"""

    with connection.cursor() as cur:
        sql_query = """
        SELECT * FROM DIM_Truck;
        """
        cur.execute(sql_query)
        truck_df = pd.DataFrame(cur.fetchall())

    return truck_df


def get_transaction_table(connection: Connection) -> DataFrame:
    """ Get the historical data from the "FACT_Transaction" 
    table from the database as a pandas dataframe"""

    HISTORICAL_CUTOFF_DATE = '2025-10-25 23:58:00'

    with connection.cursor() as cur:
        sql_query = f"""
        SELECT * FROM FACT_Transaction
        WHERE at <= '{HISTORICAL_CUTOFF_DATE}';
        """
        cur.execute(sql_query)
        transaction_df = pd.DataFrame(cur.fetchall())

    return transaction_df


def clean_transaction_data(df: DataFrame) -> DataFrame:
    """ Clean the transaction data using the following conditions:
        - total should be greater than 0
        - truck_id should be between 1 and 6 inclusive 
        - payment_method_id should be 1 or 2 """

    df_cleaned = df.dropna().drop_duplicates().reset_index(drop=True)
    df_cleaned = df_cleaned[(df_cleaned['total'] > 0) &
                            (df_cleaned['truck_id'].between(1, 6)) &
                            (df_cleaned['payment_method_id'].isin([1, 2]))].reset_index(drop=True)

    return df_cleaned


if __name__ == "__main__":

    conn = get_connection_to_db()

    payment_data = get_payment_table(conn)
    truck_data = get_truck_table(conn)

    transaction_data = get_transaction_table(conn)
    transaction_data_cleaned = clean_transaction_data(transaction_data)

    conn.close()

    PAYMENT_CSV_PATH = "./data/payment_data.csv"
    TRUCK_CSV_PATH = "./data/truck_data.csv"
    TRANSACTION_CSV_PATH = "./data/transaction_data.csv"

    if not os.path.exists("./data"):
        os.makedirs("./data")

    payment_data.to_csv(PAYMENT_CSV_PATH, index=False)
    print(f"Payment data extracted and saved to {PAYMENT_CSV_PATH}")

    truck_data.to_csv(TRUCK_CSV_PATH, index=False)
    print(f"Truck data extracted and saved to {TRUCK_CSV_PATH}")

    transaction_data_cleaned.to_csv(
        TRANSACTION_CSV_PATH, index=False)
    print(f"Transaction data extracted and saved to {TRANSACTION_CSV_PATH}")
