# pylint: disable=invalid-name

import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard_helper import (get_combined_data,
                              get_cumulative_totals_df,
                              get_best_performing_truck,
                              get_worst_performing_truck,
                              get_average_truck_revenue,
                              get_percentage_difference,
                              get_payment_method_distribution_df,
                              get_average_transaction_amounts)


def show_cumulative_totals_line_chart(data: pd.DataFrame, selected_trucks: list) -> None:
    """ Line chart showing cumulative total revenue over time for each truck """

    cumulative_totals_df = get_cumulative_totals_df(data)
    cumulative_totals_df = cumulative_totals_df[
        cumulative_totals_df['truck_name'].isin(selected_trucks)]
    cumulative_chart = px.line(cumulative_totals_df,
                               title="Cumulative Total Revenue by Truck Over Time",
                               x='date',
                               y='cumulative_total_pounds',
                               color='truck_name',
                               labels={'truck_name': 'Truck Name',
                                       'date': 'Date',
                                       'cumulative_total_pounds': 'Cumulative Total Revenue'
                                       }
                               )

    cumulative_chart.update_yaxes(tickformat=",", tickprefix="£")
    st.plotly_chart(cumulative_chart)


def show_average_revenue_line_chart(data: pd.DataFrame, selected_trucks: list) -> None:
    """ Line chart showing average transaction amount by hour for each truck """

    transaction_df = get_average_transaction_amounts(data)
    transaction_df = transaction_df[transaction_df['truck_name'].isin(
        selected_trucks)]
    transaction_chart = px.line(transaction_df,
                                title="Average Transaction Size by Truck per Hour",
                                x='hour_of_day',
                                y='average_transaction_amount',
                                color='truck_name',
                                labels={'truck_name': 'Truck Name',
                                        'hour_of_day': 'Hour of Day',
                                        'average_transaction_amount': 'Average Transaction Amount'
                                        }
                                )

    transaction_chart.update_yaxes(tickformat=",", tickprefix="£")
    st.plotly_chart(transaction_chart)


def show_kpi_metrics(data: pd.DataFrame) -> None:
    """ KPI Metrics showing the best and worst performing trucks, their total revenue,
    and how this compares to the average total revenue across all trucks
    """

    st.subheader("Total Revenue Metrics")

    average_truck_revenue = get_average_truck_revenue(data)

    best_truck = get_best_performing_truck(data)
    best_truck_name = best_truck['truck_name']
    best_truck_revenue = best_truck['total_pounds']

    worst_truck = get_worst_performing_truck(data)
    worst_truck_name = worst_truck['truck_name']
    worst_truck_revenue = worst_truck['total_pounds']

    col_1, col_2 = st.columns(2)
    with col_1:
        st.metric(
            label=f"Best Performing Truck: {best_truck_name}",
            value=f"£{best_truck_revenue:,.2f}",
            delta=f"{get_percentage_difference(best_truck_revenue, average_truck_revenue):.2f}% vs. Average Revenue"
        )

    with col_2:
        st.metric(
            label=f"Worst Performing Truck: {worst_truck_name}",
            value=f"£{worst_truck_revenue:,.2f}",
            delta=f"{get_percentage_difference(worst_truck_revenue, average_truck_revenue):.2f}% vs. Average Revenue"
        )


def show_payment_method_distribution_chart(data: pd.DataFrame, selected_trucks: list) -> None:
    """ Bar chart showing the distribution of payment methods used across each truck """

    payment_method_df = get_payment_method_distribution_df(data)
    payment_method_df = payment_method_df[payment_method_df['truck_name'].isin(
        selected_trucks)]
    payment_method_chart = px.bar(payment_method_df,
                                  title="Distribution of Payment Methods by Truck",
                                  x='truck_name',
                                  y='count',
                                  color='payment_method',
                                  labels={'truck_name': 'Truck Name',
                                          'count': 'Number of Transactions',
                                          'payment_method': 'Payment Method'
                                          }
                                  )
    st.plotly_chart(payment_method_chart)


def main():
    st.title("🚚 T3 Truck Performance Dashboard")

    # Load all data
    data = get_combined_data()

    with st.sidebar:
        st.header("Filters")
        selected_trucks = st.multiselect(
            label="Total Revenue Over Time by Truck - Select Trucks",
            options=data['truck_name'].unique(),
            default=data['truck_name'].unique()
        )

    show_kpi_metrics(data)

    show_cumulative_totals_line_chart(data, selected_trucks)

    show_payment_method_distribution_chart(data, selected_trucks)

    show_average_revenue_line_chart(data, selected_trucks)


if __name__ == "__main__":
    main()
