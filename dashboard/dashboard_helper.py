# pylint: skip-file

""" Helper functions for the Streamlit dashboard """

import awswrangler as wr
import pandas as pd
import streamlit as st


def get_athena_query(query: str) -> pd.DataFrame:
    """ Execute an Athena query and return the results as a pandas DataFrame """

    DB_PATH = 'c20-muarij-t3-glue-db'

    df = wr.athena.read_sql_query(
        sql=query,
        database=DB_PATH,
        ctas_approach=False,
        workgroup="c20-muarij-t3-athena-workgroup"
    )

    return df


@st.cache_data(ttl=300)
def get_combined_data() -> pd.DataFrame:
    """ Get the combined data from S3 as a pandas DataFrame using awswrangler """

    sql_query = """
    SELECT
        transaction_id, 
        dt.truck_name, 
        dpm.payment_method, 
        total/100 AS total_pounds, 
        at, 
        has_card_reader,
        fsa_rating
    FROM transaction_table AS ft
    JOIN payment_table AS dpm
        ON ft.payment_method_id = dpm.payment_method_id 
    JOIN truck_table AS dt
        ON ft.truck_id = dt.truck_id
    """

    df = get_athena_query(sql_query)

    return df


def get_cumulative_totals_df(df: pd.DataFrame) -> pd.DataFrame:
    """ Get cumulative totals of revenue over time for each truck"""

    df['date'] = pd.to_datetime(df['at']).dt.date

    # Group by truck and date, sum the totals
    daily_totals = df.groupby(['truck_name', 'date'])[
        'total_pounds'].sum().reset_index()

    # Calculate cumulative sum for each truck
    # Sort by date first, then use groupby with cumsum()
    daily_totals = daily_totals.sort_values('date')
    daily_totals['cumulative_total_pounds'] = daily_totals.groupby('truck_name')[
        'total_pounds'].cumsum()

    daily_totals_cleaned = daily_totals[["truck_name", "date",
                                        "cumulative_total_pounds"]]

    return daily_totals_cleaned


def get_payment_method_distribution_df(df: pd.DataFrame) -> pd.DataFrame:
    """ Get the distribution of payment methods for each truck """

    payment_distribution_df = df.groupby(['truck_name', 'payment_method'])[
        'transaction_id'].count().reset_index()
    payment_distribution_df = payment_distribution_df.rename(
        columns={'transaction_id': 'count'})

    return payment_distribution_df


def get_best_performing_truck(df: pd.DataFrame) -> pd.DataFrame:
    """ Get the best performing truck based on total revenue """

    total_revenue = df.groupby('truck_name')[
        'total_pounds'].sum().reset_index()
    best_truck = total_revenue.loc[total_revenue['total_pounds'].idxmax()]

    return best_truck


def get_worst_performing_truck(df: pd.DataFrame) -> pd.DataFrame:
    """ Get the worst performing truck based on total revenue """

    total_revenue = df.groupby('truck_name')[
        'total_pounds'].sum().reset_index()
    worst_truck = total_revenue.loc[total_revenue['total_pounds'].idxmin()]

    return worst_truck


def get_average_truck_revenue(df: pd.DataFrame) -> float:
    """ Get the average total revenue across all trucks """

    total_revenue = df.groupby('truck_name')[
        'total_pounds'].sum().reset_index()
    average_revenue = total_revenue['total_pounds'].mean()

    return average_revenue


def get_percentage_difference(value_1: float, value_2: float) -> float:
    """ Calculate the percentage difference between two values """

    if value_2 == 0:
        return 0.0

    percentage_diff = ((value_1 - value_2) / value_2) * 100
    return percentage_diff


def get_average_transaction_amounts(df: pd.DataFrame) -> pd.DataFrame:
    """ Get the average transaction amounts for each truck, grouped by hour """

    average_amount = df.groupby(['truck_name', df['at'].dt.hour])[
        'total_pounds'].mean().reset_index()

    average_amount = average_amount.rename(
        columns={'total_pounds': 'average_transaction_amount',
                 'at': 'hour_of_day'})

    average_amount = average_amount.sort_values(
        by=['truck_name', 'hour_of_day'])

    return average_amount


if __name__ == "__main__":
    pass
