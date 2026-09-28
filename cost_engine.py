import boto3
from botocore.exceptions import BotoCoreError, ClientError
import pandas as pd
import datetime
import random
import streamlit as st


def generate_mock_data(start_date_str: str, end_date_str: str) -> pd.DataFrame:
    """
    Generates realistic, deterministic mock AWS cost data for a given date range.
    Includes variance and weekday/weekend patterns.
    """
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        # Fallback to defaults if parsing fails
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=7)
        
    delta = end_date - start_date
    num_days = delta.days
    
    # Ensure there's at least 1 day in the range
    if num_days < 0:
        num_days = 0
    elif num_days == 0:
        num_days = 1
        
    services = {
        "Amazon Elastic Compute Cloud - Compute": {"base": 42.50, "var": 8.0, "weekend_drop": 0.25},
        "Amazon Relational Database Service": {"base": 24.80, "var": 2.0, "weekend_drop": 0.05},
        "Amazon Simple Storage Service": {"base": 14.20, "var": 1.0, "weekend_drop": 0.0},
        "Amazon DynamoDB": {"base": 6.50, "var": 1.5, "weekend_drop": 0.15},
        "AWS Lambda": {"base": 3.10, "var": 1.2, "weekend_drop": 0.40},
        "Amazon CloudFront": {"base": 5.40, "var": 1.8, "weekend_drop": 0.10},
        "NAT Gateway": {"base": 9.60, "var": 0.4, "weekend_drop": 0.0}
    }
    
    records = []
    # Seed the random number generator to provide consistent results for a given range
    rng = random.Random(hash(start_date_str + end_date_str) & 0xffffffff)
    
    for i in range(num_days):
        current_day = start_date + datetime.timedelta(days=i)
        day_str = current_day.strftime("%Y-%m-%d")
        is_weekend = current_day.weekday() >= 5
        
        for service, config in services.items():
            base = config["base"]
            variance = rng.uniform(-config["var"], config["var"])
            cost = base + variance
            
            if is_weekend:
                cost *= (1.0 - config["weekend_drop"])
                
            cost = max(0.01, round(cost, 2))
            credit = 0.0
            net_cost = cost

            records.append({
                'Date': day_str,
                'Service': service,
                'RecordType': 'Usage',
                'Cost': cost,
                'Credit': credit,
                'NetCost': net_cost,
                'UnblendedCost': cost,
                'NetUnblendedCost': net_cost
            })
            
    return pd.DataFrame(records)

@st.cache_data(ttl=3600, show_spinner=False)
def get_aws_cost_data(
    start_date: str, 
    end_date: str, 
    aws_access_key_id: str = None, 
    aws_secret_access_key: str = None, 
    aws_session_token: str = None
):
    """
    Attempts to fetch cost data using AWS Cost Explorer API.
    If credentials are provided and query fails or returns nothing:
      - If it is a DataUnavailableException or empty query result, returns status 'live' with empty data.
      - If it is an authentication/permission error, returns status 'error' with empty data.
    If no credentials are provided, falls back to generated mock data (status 'mock').
    """
    # If no credentials are provided at all, return mock data directly
    if not aws_access_key_id or not aws_secret_access_key:
        df_mock = generate_mock_data(start_date, end_date)
        return {
            'status': 'mock',
            'data': df_mock,
            'error_message': None
        }

    try:
        # Initialize AWS Cost Explorer client (defaulting to us-east-1 as it is the standard endpoint for CE)
        client_kwargs = {'region_name': 'us-east-1'}
        client_kwargs['aws_access_key_id'] = aws_access_key_id
        client_kwargs['aws_secret_access_key'] = aws_secret_access_key
        if aws_session_token:
            client_kwargs['aws_session_token'] = aws_session_token
            
        client = boto3.client('ce', **client_kwargs)
        
        # Query AWS Cost Explorer with both SERVICE and RECORD_TYPE to differentiate Usage vs Credits vs Discounts
        has_record_type = False
        try:
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost', 'NetUnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    },
                    {
                        'Type': 'DIMENSION',
                        'Key': 'RECORD_TYPE'
                    }
                ]
            )
            has_record_type = True
        except Exception:
            # Fallback if 2-dimensional GroupBy is restricted or fails
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost', 'NetUnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            has_record_type = False
        
        records = []
        for result in response.get('ResultsByTime', []):
            day_str = result['TimePeriod']['Start']
            groups = result.get('Groups', [])
            total_block = result.get('Total', {})
            total_unblended = float(total_block.get('UnblendedCost', {}).get('Amount', 0.0))
            total_net = float(total_block.get('NetUnblendedCost', {}).get('Amount', total_unblended))
            
            day_group_sum_credit = 0.0

            for group in groups:
                keys = group.get('Keys', [])
                service = keys[0] if len(keys) > 0 else "General AWS Service"
                record_type = keys[1] if (has_record_type and len(keys) > 1) else "Usage"
                
                unblended_val = float(group.get('Metrics', {}).get('UnblendedCost', {}).get('Amount', 0.0))
                net_val = float(group.get('Metrics', {}).get('NetUnblendedCost', {}).get('Amount', unblended_val))
                
                # Check for Credit records or negative amounts (credits / refunds)
                if record_type.lower() == 'credit' or unblended_val < 0 or net_val < 0:
                    credit_val = abs(min(unblended_val, net_val))
                    gross_val = 0.0
                    net_cost = -credit_val
                else:
                    # In standard usage records, difference between unblended and net is credits applied
                    applied_credit = max(0.0, unblended_val - net_val)
                    credit_val = applied_credit
                    gross_val = unblended_val
                    net_cost = net_val
                
                day_group_sum_credit += credit_val

                records.append({
                    'Date': day_str,
                    'Service': service,
                    'RecordType': record_type,
                    'Cost': gross_val,
                    'Credit': credit_val,
                    'NetCost': max(0.0, net_cost),
                    'UnblendedCost': unblended_val,
                    'NetUnblendedCost': net_val
                })

            # Check if there are overall account credits reflected in Total that were not allocated to a group
            account_level_credit = max(0.0, total_unblended - total_net) - day_group_sum_credit
            if account_level_credit > 0.001:
                records.append({
                    'Date': day_str,
                    'Service': 'AWS Cost Explorer',
                    'RecordType': 'Credit',
                    'Cost': 0.0,
                    'Credit': round(account_level_credit, 4),
                    'NetCost': 0.0,
                    'UnblendedCost': -round(account_level_credit, 4),
                    'NetUnblendedCost': 0.0
                })
        
        df = pd.DataFrame(records)
        if df.empty:
            df = pd.DataFrame(columns=['Date', 'Service', 'RecordType', 'Cost', 'Credit', 'NetCost', 'UnblendedCost', 'NetUnblendedCost'])
            
        return {
            'status': 'live',
            'data': df,
            'error_message': None
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        
        # DataUnavailableException indicates Cost Explorer has no data (e.g. no resources were used or it was just enabled)
        if error_code in ['DataUnavailableException', 'ResourceNotFoundException']:
            df_empty = pd.DataFrame(columns=['Date', 'Service', 'Cost'])
            return {
                'status': 'live',
                'data': df_empty,
                'error_message': f"DataUnavailableException: {error_msg}"
            }
        else:
            # Other errors like AccessDeniedException, UnrecognizedClientException, etc. are credential errors
            df_empty = pd.DataFrame(columns=['Date', 'Service', 'Cost'])
            return {
                'status': 'error',
                'data': df_empty,
                'error_message': f"{error_code}: {error_msg}"
            }
            
    except (BotoCoreError, Exception) as e:
        error_msg = str(e)
        df_empty = pd.DataFrame(columns=['Date', 'Service', 'Cost'])
        return {
            'status': 'error',
            'data': df_empty,
            'error_message': error_msg
        }


def test_aws_connection(aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str = None) -> dict:
    """
    Validates AWS credentials by trying to initialize a boto3 client and checking STS get_caller_identity.
    """
    try:
        client_kwargs = {'region_name': 'us-east-1'}
        client_kwargs['aws_access_key_id'] = aws_access_key_id
        client_kwargs['aws_secret_access_key'] = aws_secret_access_key
        if aws_session_token:
            client_kwargs['aws_session_token'] = aws_session_token
            
        sts = boto3.client('sts', **client_kwargs)
        identity = sts.get_caller_identity()
        
        return {
            'success': True,
            'account_id': identity.get('Account'),
            'arn': identity.get('Arn'),
            'error_message': None
        }
    except (BotoCoreError, ClientError, Exception) as e:
        error_msg = str(e)
        if isinstance(e, ClientError):
            error_msg = e.response.get('Error', {}).get('Message', str(e))
        return {
            'success': False,
            'account_id': None,
            'arn': None,
            'error_message': error_msg
        }


def get_account_credits(aws_connected: bool = False, credentials: dict = None) -> float:
    """
    Returns the currently available AWS promotional credits or prepaid account balance.

    NOTE FOR CLOUD/DEVOPS BEGINNERS:
    - AWS Cost Explorer API (ce.get_cost_and_usage) tracks historical spend and credits
      *applied* to past invoices, but does NOT expose an API for remaining available credit balances.
    - In a production environment, remaining promotional credit balances can be retrieved via:
        1. AWS Billing / Invoicing API or AWS Budgets API (with appropriate IAM permissions).
        2. AWS Support API (describe_services/describe_severity_levels, requires Business/Enterprise support).
        3. Configured manually in Settings or Profile (persisted locally).
    - If connected to live AWS (aws_connected=True) and no custom balance is set, this returns $0.00.
    - In Demo Mode (aws_connected=False), this returns $2,500.00 as a realistic demonstration placeholder.
    """
    try:
        # 1. Check if user configured a custom balance in session state
        if 'custom_credit_balance' in st.session_state and st.session_state['custom_credit_balance'] is not None:
            return float(st.session_state['custom_credit_balance'])

        # 2. Check locally persisted settings
        import auth_manager
        persisted = auth_manager.load_custom_credits()
        if persisted is not None:
            return persisted
    except Exception:
        pass

    # When connected to a real live AWS account, default to 0.00 unless configured
    if aws_connected:
        return 0.00

    # Default realistic promotional credit placeholder for Demo Mode
    return 2500.00


