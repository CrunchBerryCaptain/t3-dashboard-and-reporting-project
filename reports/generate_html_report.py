import os
import pandas as pd
import awswrangler as wr
from datetime import datetime, timedelta


def get_combined_data() -> pd.DataFrame:
    """ Get all of yesterday's data from S3 as a pandas DataFrame using awswrangler """

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
    WHERE DATE(at) = CURRENT_DATE - INTERVAL '1' DAY;
    """

    df = run_athena_query(sql_query)

    return df


def run_athena_query(query: str) -> pd.DataFrame:
    """ Execute an Athena query on an AWS Glue Data Catalog 
    and return the results as a pandas DataFrame """

    DB_PATH = 'c20-muarij-t3-glue-db'

    df = wr.athena.read_sql_query(
        sql=query,
        database=DB_PATH,
        ctas_approach=False,
        workgroup="c20-muarij-t3-athena-workgroup"
    )

    return df


def get_best_performing_truck(df: pd.DataFrame) -> str:
    """ Get the best performing truck based on total revenue """

    total_revenue = df.groupby('truck_name')[
        'total_pounds'].sum().reset_index()
    best_truck = total_revenue.loc[total_revenue['total_pounds'].idxmax()]

    return best_truck['truck_name']


def get_worst_performing_truck(df: pd.DataFrame) -> str:
    """ Get the worst performing truck based on total revenue """

    total_revenue = df.groupby('truck_name')[
        'total_pounds'].sum().reset_index()
    worst_truck = total_revenue.loc[total_revenue['total_pounds'].idxmin()]

    return worst_truck['truck_name']


def get_revenue_for_truck(df: pd.DataFrame, truck_name: str) -> float:
    """ Get the total revenue for a specific truck """

    truck_revenue = df[df['truck_name'] == truck_name]['total_pounds'].sum()

    return truck_revenue


def get_total_daily_revenue(df: pd.DataFrame) -> float:
    """ Get the total daily revenue across all trucks """

    total_revenue = df['total_pounds'].sum()

    return total_revenue


# ==================== COST REDUCTION METRICS ====================

def get_underperforming_trucks(df: pd.DataFrame, threshold_percentile: int = 25) -> pd.DataFrame:
    """ Identify underperforming trucks below the specified percentile.
    Useful for identifying trucks that may need intervention or reallocation. """

    truck_performance = df.groupby('truck_name').agg({
        'total_pounds': 'sum',
        'transaction_id': 'count'
    }).reset_index()

    truck_performance['revenue_per_transaction'] = (
        truck_performance['total_pounds'] / truck_performance['transaction_id']
    )

    # Calculate threshold
    revenue_threshold = truck_performance['total_pounds'].quantile(
        threshold_percentile / 100)

    underperformers = truck_performance[
        truck_performance['total_pounds'] < revenue_threshold
    ].sort_values('total_pounds')

    return underperformers


# ==================== PROFIT OPTIMIZATION METRICS ====================

def get_transaction_velocity_by_truck(df: pd.DataFrame) -> pd.DataFrame:
    """ Calculate transactions per hour by truck to identify efficiency opportunities. """

    df_copy = df.copy()
    df_copy['hour'] = df_copy['at'].dt.hour

    velocity = df_copy.groupby(['truck_name', 'hour']).agg({
        'transaction_id': 'count',
        'total_pounds': 'sum'
    }).reset_index()

    # Calculate average velocity per truck
    avg_velocity = velocity.groupby('truck_name').agg({
        'transaction_id': 'mean',
        'total_pounds': 'mean'
    }).reset_index()

    avg_velocity = avg_velocity.rename(columns={
        'transaction_id': 'avg_transactions_per_hour',
        'total_pounds': 'avg_revenue_per_hour'
    })

    avg_velocity['revenue_per_transaction'] = (
        avg_velocity['avg_revenue_per_hour'] /
        avg_velocity['avg_transactions_per_hour']
    )

    return avg_velocity.sort_values('avg_revenue_per_hour', ascending=False)


# ==================== DEMAND ANALYSIS METRICS ====================

def get_price_point_segmentation(df: pd.DataFrame) -> pd.DataFrame:
    """ Segment transactions by price point to understand demand at different price levels.
    Low: £0-5, Medium: £5-10, High: £10+ """

    df_copy = df.copy()

    def categorize_price(price):
        if price <= 5.0:
            return 'Low (£0-5)'
        elif price <= 10.0:
            return 'Medium (£5-10)'
        else:
            return 'High (£10+)'

    df_copy['price_segment'] = df_copy['total_pounds'].apply(categorize_price)

    segmentation = df_copy.groupby('price_segment').agg({
        'transaction_id': 'count',
        'total_pounds': 'sum'
    }).reset_index()

    segmentation['percentage_of_transactions'] = (
        segmentation['transaction_id'] / segmentation['transaction_id'].sum()) * 100
    segmentation['percentage_of_revenue'] = (
        segmentation['total_pounds'] / segmentation['total_pounds'].sum()) * 100

    # Reorder by price level
    order = ['Low (£0-5)', 'Medium (£5-10)', 'High (£10+)']
    segmentation['price_segment'] = pd.Categorical(
        segmentation['price_segment'], categories=order, ordered=True)
    segmentation = segmentation.sort_values('price_segment')

    return segmentation


def generate_html_report(df: pd.DataFrame) -> str:
    """ Generate the report content as HTML with inline styles for email compatibility """

    # Get yesterday's date for the report
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Get metrics
    total_revenue = get_total_daily_revenue(df)
    best_truck = get_best_performing_truck(df)
    best_truck_revenue = get_revenue_for_truck(df, best_truck)
    worst_truck = get_worst_performing_truck(df)
    worst_truck_revenue = get_revenue_for_truck(df, worst_truck)

    price_seg = get_price_point_segmentation(df)
    most_demanded = price_seg.loc[price_seg['transaction_id'].idxmax()]

    underperformers = get_underperforming_trucks(df)
    velocity = get_transaction_velocity_by_truck(df)
    dominant_segment = price_seg.loc[price_seg['percentage_of_revenue'].idxmax()]

    # Email-compatible HTML with inline styles and table layouts
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
            <tr>
                <td align="center" style="padding: 20px;">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden;">

                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">🚚 T3 Food Truck Daily Report</h1>
                                <p style="color: #ffffff; margin: 10px 0 0 0; opacity: 0.9;">Report Date: {yesterday}</p>
                            </td>
                        </tr>

                        <!-- Executive Summary -->
                        <tr>
                            <td style="padding: 25px;">
                                <h2 style="color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin-top: 0;">Executive Summary</h2>

                                <table width="100%" cellpadding="10" cellspacing="0">
                                    <tr>
                                        <td width="50%" style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; vertical-align: top;">
                                            <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Total Daily Revenue</div>
                                            <div style="font-size: 24px; font-weight: bold; color: #333;">£{total_revenue:,.2f}</div>
                                        </td>
                                        <td width="50%" style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; vertical-align: top;">
                                            <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Most In-Demand Price Point</div>
                                            <div style="font-size: 20px; font-weight: bold; color: #333;">{most_demanded['price_segment']}</div>
                                            <div style="font-size: 11px; color: #888; margin-top: 5px;">{most_demanded['percentage_of_transactions']:.1f}% of transactions</div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td width="50%" style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; vertical-align: top;">
                                            <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Best Performing Truck</div>
                                            <div style="font-size: 20px; font-weight: bold; color: #28a745;">{best_truck}</div>
                                            <div style="font-size: 11px; color: #888; margin-top: 5px;">£{best_truck_revenue:,.2f}</div>
                                        </td>
                                        <td width="50%" style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; vertical-align: top;">
                                            <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Worst Performing Truck</div>
                                            <div style="font-size: 20px; font-weight: bold; color: #dc3545;">{worst_truck}</div>
                                            <div style="font-size: 11px; color: #888; margin-top: 5px;">£{worst_truck_revenue:,.2f}</div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Cost Reduction Opportunities -->
                        <tr>
                            <td style="padding: 25px; padding-top: 0;">
                                <h2 style="color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 10px;">Cost Reduction Opportunities</h2>
                                <h3 style="color: #764ba2; margin-top: 20px;">Underperforming Trucks (Bottom 25%)</h3>
    """

    if not underperformers.empty:
        html += """
                                <table width="100%" cellpadding="10" cellspacing="0" style="border-collapse: collapse; margin: 15px 0;">
                                    <tr style="background-color: #667eea;">
                                        <th style="color: white; padding: 12px; text-align: left; font-weight: 600;">Truck Name</th>
                                        <th style="color: white; padding: 12px; text-align: left; font-weight: 600;">Daily Revenue</th>
                                    </tr>
        """
        for _, row in underperformers.iterrows():
            html += f"""
                                    <tr style="border-bottom: 1px solid #e0e0e0;">
                                        <td style="padding: 12px;">{row['truck_name']}</td>
                                        <td style="padding: 12px;">£{row['total_pounds']:,.2f}</td>
                                    </tr>
            """
        html += """
                                </table>
                                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; border-radius: 4px;">
                                    <strong>💡 INSIGHT:</strong> These trucks may need menu optimization, repositioning, or operational review
                                </div>
        """
    else:
        html += '<p style="color: #28a745; font-weight: bold;">✓ No underperforming trucks identified</p>'

    html += """
                            </td>
                        </tr>

                        <!-- Profit Optimization Strategies -->
                        <tr>
                            <td style="padding: 25px; padding-top: 0;">
                                <h2 style="color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 10px;">Profit Optimization Strategies</h2>
                                <h3 style="color: #764ba2; margin-top: 20px;">Truck Efficiency - Revenue per Hour</h3>
                                <table width="100%" cellpadding="10" cellspacing="0" style="border-collapse: collapse; margin: 15px 0;">
                                    <tr style="background-color: #667eea;">
                                        <th style="color: white; padding: 12px; text-align: left; font-weight: 600;">Truck Name</th>
                                        <th style="color: white; padding: 12px; text-align: left; font-weight: 600;">Avg Revenue per Hour</th>
                                    </tr>
    """

    for _, row in velocity.iterrows():
        html += f"""
                                    <tr style="border-bottom: 1px solid #e0e0e0;">
                                        <td style="padding: 12px;">{row['truck_name']}</td>
                                        <td style="padding: 12px;">£{row['avg_revenue_per_hour']:.2f}/hour</td>
                                    </tr>
        """

    html += """
                                </table>
                                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; border-radius: 4px;">
                                    <strong>💡 INSIGHT:</strong> Lower revenue/hour trucks may benefit from menu simplification or repositioning for faster service
                                </div>
                            </td>
                        </tr>

                        <!-- Demand & Market Analysis -->
                        <tr>
                            <td style="padding: 25px; padding-top: 0;">
                                <h2 style="color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 10px;">Demand & Market Analysis</h2>
                                <h3 style="color: #764ba2; margin-top: 20px;">Price Point Demand Analysis</h3>
                                <table width="100%" cellpadding="10" cellspacing="0" style="border-collapse: collapse; margin: 15px 0;">
                                    <tr style="background-color: #667eea;">
                                        <th style="color: white; padding: 12px; text-align: left; font-weight: 600;">Price Segment</th>
                                        <th style="color: white; padding: 12px; text-align: left; font-weight: 600;">Revenue</th>
                                        <th style="color: white; padding: 12px; text-align: left; font-weight: 600;">% of Total Revenue</th>
                                    </tr>
    """

    for _, row in price_seg.iterrows():
        html += f"""
                                    <tr style="border-bottom: 1px solid #e0e0e0;">
                                        <td style="padding: 12px;">{row['price_segment']}</td>
                                        <td style="padding: 12px;">£{row['total_pounds']:,.2f}</td>
                                        <td style="padding: 12px;">{row['percentage_of_revenue']:.1f}%</td>
                                    </tr>
        """

    html += f"""
                                </table>
                                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; border-radius: 4px;">
                                    <strong>💡 INSIGHT:</strong> {dominant_segment['price_segment']} segment drives {dominant_segment['percentage_of_revenue']:.1f}% of revenue
                                </div>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="text-align: center; padding: 20px; color: #666; font-size: 12px; background-color: #f8f9fa;">
                                <p style="margin: 0;">Generated automatically by T3 Food Truck Analytics System</p>
                                <p style="margin: 5px 0 0 0;">&copy; {datetime.now().year} T3 Food Trucks | Business Intelligence Report</p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    return html


def lambda_handler(event, context):
    """
    AWS Lambda handler function for generating daily business intelligence report.

    Parameters:
    - event: AWS Lambda event object (not used but required by Lambda)
    - context: AWS Lambda context object (not used but required by Lambda)

    Returns:
    - dict: Response with statusCode and HTML report content
    """

    try:
        # Load yesterday's data
        df = get_combined_data()

        # Generate the HTML report
        html_report = generate_html_report(df)

        # Save to file with yesterday's date (Lambda only allows writing to /tmp/)
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        report_filename = f"t3_daily_report_{yesterday}.html"
        report_path = os.path.join('/tmp', report_filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_report)

        print(f"Report generated and saved to: {report_path}")

        return {
            'statusCode': 200,
            'body': html_report,
            'message': f'Report generated successfully: {report_filename}'
        }

    except Exception as e:
        error_message = f"Error generating report: {str(e)}"
        print(error_message)
        return {
            'statusCode': 500,
            'body': error_message,
            'message': 'Report generation failed'
        }


if __name__ == "__main__":
    # For local testing
    print("Generating HTML report...")
    result = lambda_handler(None, None)
    if result['statusCode'] == 200:
        print(f"\n✅ {result['message']}")
        print("You can now open the HTML file in your browser!")
    else:
        print(f"\n❌ Local test failed: {result['body']}")
