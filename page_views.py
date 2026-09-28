import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from ui_components import render_floating_chat
from ai_helper import generate_ollama_chat_response
import auth_manager

# High-contrast, visually distinct categorical palette suitable for light & dark themes
DISTINCT_FINOPS_PALETTE = [
    '#2563eb',  # Vibrant Royal Blue
    '#f97316',  # Bright Amber Orange
    '#10b981',  # Emerald Green
    '#8b5cf6',  # Purple
    '#06b6d4',  # Bright Cyan
    '#f43f5e',  # Crimson Rose
    '#eab308',  # Golden Yellow
    '#6366f1',  # Indigo
    '#14b8a6',  # Teal
    '#ec4899',  # Vivid Pink
]

# Backward compatibility alias
MODERN_PALETTE = DISTINCT_FINOPS_PALETTE

def apply_finops_chart_theme(fig, height: int = 520, margin_bottom: int = 100, legend_y: float = -0.25):
    """
    Applies a cohesive, modern FinOps theme and defensive spacing to Plotly figures.
    Dynamically adapts font families and light/dark/paper color tokens based on active theme settings.
    """
    theme = st.session_state.get('theme', {})
    is_paper = theme.get('theme_type') in ['paper', 'minimal']
    font_color = '#292524' if is_paper else '#e5e7eb'
    title_color = '#1c1917' if is_paper else '#ffffff'
    legend_color = '#44403c' if is_paper else '#d1d5db'
    hover_bg = '#fcfbf7' if is_paper else '#1c120e'
    hover_border = '#dcd3c4' if is_paper else 'rgba(249, 115, 22, 0.4)'

    font_choice = st.session_state.get('font_choice', 'Modern Sans-Serif (Plus Jakarta Sans)')
    if 'Outfit' in font_choice:
        font_family = 'Outfit, sans-serif'
    elif 'JetBrains' in font_choice:
        font_family = 'JetBrains Mono, monospace'
    else:
        font_family = 'Plus Jakarta Sans, sans-serif'

    fig.update_layout(
        height=height,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_family=font_family,
        font_color=font_color,
        title_font=dict(
            size=16,
            color=title_color,
            family=font_family
        ),
        margin=dict(t=60, b=margin_bottom, l=60, r=40),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=legend_y,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color=legend_color, family=font_family),
            bgcolor='rgba(0,0,0,0)',
            bordercolor='rgba(90, 75, 60, 0.1)' if is_paper else 'rgba(255,255,255,0.05)',
            borderwidth=1
        ),
        hoverlabel=dict(
            bgcolor=hover_bg,
            bordercolor=hover_border,
            font=dict(color=font_color, family=font_family, size=12)
        )
    )
    return fig

def render_dashboard_view(df: pd.DataFrame, df_agg: pd.DataFrame, aggregation_level: str, num_days: int, start_str: str, end_str: str):
    """Renders the main Dashboard view with relocated filters, metrics, charts, and raw details."""
    
    # Relocated Time & Scope Filters (Replaces the former Graph View Mode toggle)
    st.markdown("<div data-section='filters' class='metric-card' style='margin-bottom: 20px; padding: 18px 24px;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='margin:0 0 14px 0; font-size:1.02rem; font-weight:700; color:var(--font-color, #f3f4f6);'>⚙️ Dashboard Time Scope & Filters</h4>", unsafe_allow_html=True)
    
    col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1, 1.3, 1])
    
    with col_f1:
        curr_lookback = st.session_state.get('lookback_days', 30)
        new_lookback = st.slider(
            "📅 Lookback Window (Days):",
            min_value=7,
            max_value=90,
            value=curr_lookback,
            step=1,
            key="dashboard_lookback_slider",
            help="Adjust the historical billing analysis window."
        )
        if new_lookback != curr_lookback:
            st.session_state['lookback_days'] = new_lookback
            st.rerun()

    with col_f2:
        curr_agg = st.session_state.get('aggregation_level', 'Day')
        agg_options = ["Day", "Week", "Month"]
        new_agg = st.selectbox(
            "Analyze spend by:",
            options=agg_options,
            index=agg_options.index(curr_agg) if curr_agg in agg_options else 0,
            key="dashboard_aggregation_selector"
        )
        if new_agg != curr_agg:
            st.session_state['aggregation_level'] = new_agg
            st.rerun()

    with col_f3:
        regions_list = [
            "US East (N. Virginia) - us-east-1",
            "US West (Oregon) - us-west-2",
            "EU (Ireland) - eu-west-1",
            "Asia Pacific (Singapore) - ap-southeast-1"
        ]
        curr_region = st.session_state.get('selected_region', regions_list[0])
        new_region = st.selectbox(
            "Target AWS Region:",
            options=regions_list,
            index=regions_list.index(curr_region) if curr_region in regions_list else 0,
            key="dashboard_region_selector"
        )
        if new_region != curr_region:
            st.session_state['selected_region'] = new_region
            st.rerun()

    with col_f4:
        metric_choice = st.selectbox(
            "Cost Metric to Visualize:",
            options=["Gross Usage ($)", "Net Spend ($)"],
            index=0,
            key="dashboard_metric_selector"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Determine metric to plot (credits completely removed)
    if df.empty or df_agg.empty or 'Cost' not in df.columns:
        st.info("ℹ️ No active billing data found for the selected lookback range. Please adjust the lookback window above or connect your AWS account.")
        return

    if metric_choice == "Net Spend ($)":
        plot_metric = 'NetCost' if 'NetCost' in df_agg.columns else 'Cost'
        metric_label = "Net Out-of-Pocket Spend"
    else:
        plot_metric = 'Cost' if 'Cost' in df_agg.columns else (df_agg.columns[-1] if len(df_agg.columns) > 0 else 'Cost')
        metric_label = "Gross Usage Spend"
    
    # Format periods cleanly for Day, Week, and Month to prevent label collision
    df_plot_agg = df_agg.copy()
    is_day = aggregation_level == "Day"
    is_week = aggregation_level == "Week"
    is_month = aggregation_level == "Month"

    if 'Period' in df_plot_agg.columns:
        if is_day:
            try:
                sample_dates = pd.to_datetime(df_plot_agg['Period'].dropna().unique())
                multi_year = len(set(sample_dates.year)) > 1
            except Exception:
                multi_year = False

            def format_day_period(val):
                try:
                    if isinstance(val, (datetime.date, datetime.datetime)):
                        return val.strftime("%b %d, '%y") if multi_year else val.strftime("%b %d")
                    val_str = str(val).strip()
                    d = pd.to_datetime(val_str)
                    return d.strftime("%b %d, '%y") if multi_year else d.strftime("%b %d")
                except Exception:
                    return str(val)

            df_plot_agg['Period'] = df_plot_agg['Period'].apply(format_day_period)

        elif is_week:
            def format_week_period(val):
                val_str = str(val)
                if '/' in val_str:
                    parts = val_str.split('/')
                    try:
                        d1 = datetime.datetime.strptime(parts[0].strip(), "%Y-%m-%d")
                        d2 = datetime.datetime.strptime(parts[1].strip(), "%Y-%m-%d")
                        return f"{d1.strftime('%b %d')} - {d2.strftime('%b %d')}"
                    except Exception:
                        return val_str
                return val_str

            df_plot_agg['Period'] = df_plot_agg['Period'].apply(format_week_period)

        elif is_month:
            def format_month_period(val):
                try:
                    d = pd.to_datetime(str(val).strip())
                    return d.strftime('%b %Y')
                except Exception:
                    return str(val)

            df_plot_agg['Period'] = df_plot_agg['Period'].apply(format_month_period)

    # Preserve strict chronological category ordering
    ordered_periods = list(dict.fromkeys(df_plot_agg['Period'].tolist())) if not df_plot_agg.empty else []
    n_periods = len(ordered_periods)

    # Determine tick spacing to avoid horizontal collisions
    if is_day:
        if n_periods <= 14:
            step = 1
            calc_angle = -25
        elif n_periods <= 31:
            step = 2
            calc_angle = -30
        elif n_periods <= 60:
            step = 4
            calc_angle = -35
        else:
            step = 7
            calc_angle = -35
        tickvals = ordered_periods[::step]
        if ordered_periods and ordered_periods[-1] not in tickvals:
            tickvals.append(ordered_periods[-1])
        calc_fontsize = 10 if n_periods > 25 else 11
    elif is_week:
        step = 1 if n_periods <= 10 else 2
        calc_angle = -28
        tickvals = ordered_periods[::step]
        if ordered_periods and ordered_periods[-1] not in tickvals:
            tickvals.append(ordered_periods[-1])
        calc_fontsize = 10 if n_periods > 6 else 11
    else:  # Month
        step = 1
        calc_angle = 0
        tickvals = ordered_periods
        calc_fontsize = 11

    chart_height = 620
    margin_bottom = 195
    legend_y = -0.36
    
    # 1. Spend Trend Bar Chart Setup
    fig_bar = px.bar(
        df_plot_agg,
        x='Period',
        y=plot_metric,
        color='Service',
        title=f'{metric_label} by Service (Aggregated by {aggregation_level})',
        labels={plot_metric: f'{metric_label}', 'Period': aggregation_level},
        color_discrete_sequence=DISTINCT_FINOPS_PALETTE
    )
    # Tooltip and defensive axis layout
    fig_bar.update_traces(
        hovertemplate='<b>%{fullData.name}</b><br>' + f'{aggregation_level}: ' + '%{x}<br>Spend: $%{y:,.2f}<extra></extra>'
    )
    apply_finops_chart_theme(fig_bar, height=chart_height, margin_bottom=margin_bottom, legend_y=legend_y)
    
    theme = st.session_state.get('theme', {})
    is_paper = theme.get('theme_type') in ['paper', 'minimal']
    axis_color = '#78716c' if is_paper else '#9ca3af'
    grid_color = 'rgba(90, 75, 60, 0.08)' if is_paper else 'rgba(255,255,255,0.06)'

    fig_bar.update_layout(
        xaxis=dict(
            showgrid=False, 
            color=axis_color,
            tickangle=calc_angle,
            automargin=False,
            type='category',
            categoryorder='array',
            categoryarray=ordered_periods,
            tickmode='array',
            tickvals=tickvals,
            ticktext=tickvals,
            tickfont=dict(size=calc_fontsize),
            title=dict(text="")  # Eliminates collision between x-axis title and legend
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor=grid_color, 
            color=axis_color,
            automargin=True,
            tickprefix="$"
        )
    )

    # 2. Donut Chart Setup
    df_donut = df.groupby('Service')[plot_metric].sum().reset_index()
    df_donut_active = df_donut[df_donut[plot_metric] > 0].copy()
    if df_donut_active.empty:
        df_donut_active = df_donut.copy()

    # Defensive fix for overlapping text: Fold minor slices (< 4% of total) into "Other Services"
    total_pie_val = df_donut_active[plot_metric].sum()
    if total_pie_val > 0:
        threshold = total_pie_val * 0.04  # 4% threshold
        major_slices = df_donut_active[df_donut_active[plot_metric] >= threshold].copy()
        minor_slices = df_donut_active[df_donut_active[plot_metric] < threshold]
        
        if not minor_slices.empty:
            other_sum = minor_slices[plot_metric].sum()
            other_row = pd.DataFrame([{
                'Service': f'Other Services ({len(minor_slices)} services < 4%)',
                plot_metric: other_sum
            }])
            df_donut_processed = pd.concat([major_slices, other_row], ignore_index=True)
        else:
            df_donut_processed = major_slices
    else:
        df_donut_processed = df_donut_active

    fig_donut = px.pie(
        df_donut_processed,
        values=plot_metric,
        names='Service',
        hole=0.48,
        title=f'{metric_label} Distribution by AWS Service',
        color_discrete_sequence=MODERN_PALETTE
    )
    # Only show percentage inside slices to prevent external label collisions; rich tooltip on hover
    fig_donut.update_traces(
        textinfo='percent', 
        textposition='inside',
        textfont=dict(size=12, color='#ffffff', family='Plus Jakarta Sans'),
        insidetextorientation='horizontal',
        hovertemplate='<b>%{label}</b><br>Spend: $%{value:,.2f}<br>Share: %{percent:.1%}<extra></extra>'
    )
    apply_finops_chart_theme(fig_donut, height=520, margin_bottom=100)

    # Render charts simultaneously
    st.markdown("<div class='chart-container' style='margin-bottom: 32px;'>", unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns([1.2, 1])
    with col_chart1:
        st.markdown("<div data-section='spend-chart'>", unsafe_allow_html=True)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_chart2:
        st.markdown("<div data-section='donut-chart'>", unsafe_allow_html=True)
        st.plotly_chart(fig_donut, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Tabular Details Section (Clean of credit columns)
    st.markdown("<div data-section='details-table'>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='font-size: 1.5rem; font-weight: 700; color: var(--font-color, #ffffff); margin-bottom: 0.8rem;'>Granular Details ({metric_label})</h3>", unsafe_allow_html=True)
    
    if not df_agg.empty:
        df_pivot = df_agg.pivot(index='Period', columns='Service', values=plot_metric).fillna(0.0)
        df_pivot['Total'] = df_pivot.sum(axis=1)
        
        formatted_pivot = df_pivot.copy()
        for col in formatted_pivot.columns:
            formatted_pivot[col] = formatted_pivot[col].map('${:,.2f}'.format)
        
        st.dataframe(formatted_pivot, use_container_width=True)
        
        csv_data = df_agg.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Aggregated Costs CSV",
            data=csv_data,
            file_name=f"aws_costs_{start_str}_to_{end_str}_by_{aggregation_level}.csv",
            mime="text/csv",
            key="btn_download_cost_csv"
        )
    else:
        st.info("No cost details to display in a pivot table.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Floating chat widget
    render_floating_chat(key_suffix="cost", df=df)

def render_analytics_view(df: pd.DataFrame):
    """Renders the AWS Cloud Resources & Services page showing active services from the dataset."""
    st.markdown("<div data-section='service-catalog'>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9ca3af; margin-top: -10px; margin-bottom: 1.5rem;'>Explore active AWS cloud resources and service cost allocations discovered in your account billing records.</p>", unsafe_allow_html=True)
    
    if df.empty or 'Service' not in df.columns or df['Cost'].sum() == 0:
        st.info("ℹ️ No active AWS resources or spend recorded for the selected lookback period. Connect your AWS credentials or adjust the lookback window on the Dashboard.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Filter Controls
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        search_query = st.text_input("🔍 Search Active AWS Resources & Services...", value="", placeholder="Type resource/service name or code (e.g. EC2, RDS, S3)", key="catalog_search_input")
    with col_f2:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Catalog", key="btn_sync_catalog", use_container_width=True):
            st.toast("Service catalog refreshed from billing data!", icon="🟢")
            st.rerun()
            
    # Map known service name patterns to display codes and descriptions
    SERVICE_MAP = {
        "Amazon Elastic Compute Cloud - Compute": {
            "name": "Amazon Elastic Compute Cloud (EC2)",
            "code": "EC2",
            "desc": "Virtual servers in the cloud. Check for idle running instances and optimize node sizes."
        },
        "Amazon Relational Database Service": {
            "name": "Amazon Relational Database Service (RDS)",
            "code": "RDS",
            "desc": "Managed relational databases. Optimize memory parameters and check reserved instance coverage."
        },
        "Amazon Simple Storage Service": {
            "name": "Amazon Simple Storage Service (S3)",
            "code": "S3",
            "desc": "Object storage built to retrieve any amount of data. Add lifecycle rules to transition old objects."
        },
        "Amazon DynamoDB": {
            "name": "Amazon DynamoDB (DynamoDB)",
            "code": "DynamoDB",
            "desc": "Serverless key-value NoSQL database. Review capacity mode settings and tables index usage."
        },
        "AWS Lambda": {
            "name": "AWS Lambda (Lambda)",
            "code": "Lambda",
            "desc": "Serverless server function execution. Optimize execution duration limits."
        },
        "Amazon CloudFront": {
            "name": "Amazon CloudFront (CloudFront)",
            "code": "CloudFront",
            "desc": "Global content delivery network (CDN). Monitor regional edge caches utilization."
        },
        "NAT Gateway": {
            "name": "VPC NAT Gateway",
            "code": "NAT Gateway",
            "desc": "Managed network translation gate. Route private traffic to local VPC endpoints."
        }
    }

    # Build catalog list dynamically from real active dataset
    services = []
    for raw_svc in df['Service'].unique():
        spend = float(df[df['Service'] == raw_svc]['Cost'].sum())
        if spend > 0:
            if raw_svc in SERVICE_MAP:
                map_info = SERVICE_MAP[raw_svc]
                services.append({
                    "name": map_info["name"],
                    "code": map_info["code"],
                    "status": "Active Spend",
                    "desc": map_info["desc"],
                    "spend": spend
                })
            else:
                services.append({
                    "name": raw_svc,
                    "code": raw_svc.split(" ")[-1] if " " in raw_svc else raw_svc,
                    "status": "Active Spend",
                    "desc": "AWS service actively billing in your cloud environment.",
                    "spend": spend
                })

    # Sort services by spend descending
    services.sort(key=lambda s: s["spend"], reverse=True)

    # Filter list by search query
    filtered_services = []
    for svc in services:
        if search_query.lower() in svc["name"].lower() or search_query.lower() in svc["code"].lower():
            filtered_services.append(svc)

    # Top summary metrics
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(
            f"""
            <div class='metric-card' style='padding: 16px 20px; margin-bottom: 16px;'>
                <p style='margin:0; font-size:0.8rem; color:#9ca3af; text-transform:uppercase;'>Active Resources / Services</p>
                <h3 style='margin:6px 0 0 0; font-size:1.8rem; font-weight:800; color:#38bdf8;'>{len(services)}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_m2:
        tot_spend = sum(s["spend"] for s in services)
        st.markdown(
            f"""
            <div class='metric-card' style='padding: 16px 20px; margin-bottom: 16px;'>
                <p style='margin:0; font-size:0.8rem; color:#9ca3af; text-transform:uppercase;'>Total Resource Spend</p>
                <h3 style='margin:6px 0 0 0; font-size:1.8rem; font-weight:800; color:var(--primary-accent);'>${tot_spend:,.2f}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_m3:
        top_svc = services[0]["name"] if services else "None"
        st.markdown(
            f"""
            <div class='metric-card' style='padding: 16px 20px; margin-bottom: 16px;'>
                <p style='margin:0; font-size:0.8rem; color:#9ca3af; text-transform:uppercase;'>Highest Spend Resource</p>
                <h3 style='margin:6px 0 0 0; font-size:1.2rem; font-weight:700; color:#10b981; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>{top_svc}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

    if not filtered_services:
        st.info("No AWS services matched your search filter.")
    else:
        for i in range(0, len(filtered_services), 3):
            cols = st.columns(3)
            chunk = filtered_services[i:i+3]
            for idx, svc in enumerate(chunk):
                with cols[idx]:
                    st.markdown(
                        f"""
                        <div class='metric-card' style='margin-bottom: 14px; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;'>
                            <div>
                                <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; gap: 8px;'>
                                    <h4 style='margin:0; font-size: 0.95rem; color: var(--font-color, #ffffff); line-height: 1.2;'>{svc['name']}</h4>
                                    <span style='color: #34d399; font-weight: 700; font-size: 0.72rem; white-space: nowrap;'>● {svc['status']}</span>
                                </div>
                                <p style='color: #9ca3af; font-size: 0.76rem; line-height: 1.3; margin-bottom: 10px;'>{svc['desc']}</p>
                            </div>
                            <div style='display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;'>
                                <span style='color: #6366f1; font-weight: 700; font-size: 0.78rem;'>{svc['code']}</span>
                                <span style='font-size: 1.05rem; font-weight: 800; color: var(--font-color, #ffffff);'>${svc['spend']:,.2f}</span>
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
    st.markdown("</div>", unsafe_allow_html=True)


def generate_mock_machine_carbon_data(start_str: str, end_str: str, grid_coeff: float = 0.37) -> pd.DataFrame:
    """
    [MOCK DATA PLACEHOLDER] Generates realistic per-machine/instance carbon footprint telemetry.
    Real per-machine carbon footprint data is not natively provided by AWS Cost Explorer API.
    This mock function models energy consumption (kWh) and carbon emissions (kg CO2e) per EC2
    instance across the selected date range.
    """
    try:
        start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
    except Exception:
        end_dt = datetime.date.today()
        start_dt = end_dt - datetime.timedelta(days=30)

    machines = [
        {"id": "i-0a81b2c3d4e01", "name": "prod-api-cluster", "type": "c6i.2xlarge", "base_kwh": 14.5},
        {"id": "i-0b92c3d4e5f02", "name": "prod-db-primary", "type": "r6i.4xlarge", "base_kwh": 28.0},
        {"id": "i-0c03d4e5f6a03", "name": "worker-queue-node", "type": "c6g.xlarge", "base_kwh": 8.2},
        {"id": "i-0d14e5f6a7b04", "name": "analytics-spark-master", "type": "m6i.4xlarge", "base_kwh": 22.4},
        {"id": "i-0e25f6a7b8c05", "name": "staging-k8s-ingress", "type": "t4g.xlarge", "base_kwh": 4.8}
    ]

    records = []
    curr_dt = start_dt
    day_idx = 0
    while curr_dt <= end_dt:
        dt_str = curr_dt.strftime("%Y-%m-%d")
        for m in machines:
            # Deterministic variation based on day and machine
            seed_val = (day_idx * 17 + hash(m["id"])) % 100
            factor = 0.85 + (seed_val / 100.0) * 0.35  # between 0.85 and 1.20
            daily_kwh = round(m["base_kwh"] * factor, 2)
            co2_kg = round(daily_kwh * grid_coeff, 3)
            
            records.append({
                "InstanceId": f"{m['id']} ({m['name']})",
                "MachineId": m["id"],
                "MachineName": m["name"],
                "InstanceType": m["type"],
                "Date": dt_str,
                "DateTime": f"{dt_str} 00:00:00",
                "Energy_kWh": daily_kwh,
                "CarbonFootprint_kg": co2_kg
            })
        curr_dt += datetime.timedelta(days=1)
        day_idx += 1

    return pd.DataFrame(records)

def render_carbon_view(df: pd.DataFrame, grid_coeff: float):
    """Renders the Carbon Footprint page with per-workload Plotly time-series charts."""
    is_connected = st.session_state.get('aws_connected', False)
    selected_region = st.session_state.get('selected_region', 'US East (N. Virginia) - us-east-1')
    start_str = st.session_state.get('start_str', (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d"))
    end_str = st.session_state.get('end_str', datetime.date.today().strftime("%Y-%m-%d"))

    if is_connected:
        st.markdown("<p style='color: #9ca3af; margin-top: -10px; margin-bottom: 1.5rem;'>Greenhouse gas emissions telemetry and energy utilization calculated from your connected AWS account usage.</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='color: #9ca3af; margin-top: -10px; margin-bottom: 1.5rem;'>Greenhouse gas emissions telemetry and energy utilization breakdown per cloud workload (Demo Mode).</p>", unsafe_allow_html=True)

    if is_connected:
        if df.empty or 'Cost' not in df.columns or df['Cost'].sum() == 0:
            st.info("ℹ️ No active cloud spend or emissions recorded for the selected lookback window in your connected AWS account. Once your AWS services (EC2, RDS, S3, etc.) record usage, their carbon footprint telemetry will appear here.")
            return

        # Power intensity factors (kWh per dollar of spend) mapped by AWS service category
        SERVICE_POWER_MAP = {
            "Amazon Elastic Compute Cloud - Compute": {"code": "EC2", "alias": "Amazon Elastic Compute Cloud (EC2)", "category": "Cloud Compute", "kwh_factor": 2.50},
            "Amazon Relational Database Service": {"code": "RDS", "alias": "Amazon Relational Database Service (RDS)", "category": "Managed Database", "kwh_factor": 1.85},
            "Amazon Simple Storage Service": {"code": "S3", "alias": "Amazon Simple Storage Service (S3)", "category": "Object Storage", "kwh_factor": 0.40},
            "Amazon DynamoDB": {"code": "DynamoDB", "alias": "Amazon DynamoDB", "category": "NoSQL Database", "kwh_factor": 1.40},
            "AWS Lambda": {"code": "Lambda", "alias": "AWS Lambda", "category": "Serverless Compute", "kwh_factor": 2.20},
            "Amazon CloudFront": {"code": "CloudFront", "alias": "Amazon CloudFront", "category": "Global CDN", "kwh_factor": 0.55},
            "NAT Gateway": {"code": "NAT", "alias": "AWS VPC NAT Gateway", "category": "Networking", "kwh_factor": 0.50},
        }

        records = []
        df_daily_svc = df.groupby(['Date', 'Service'])['Cost'].sum().reset_index()
        for _, row in df_daily_svc.iterrows():
            dt_str = str(row['Date'])
            raw_svc = str(row['Service'])
            cost = float(row['Cost'])
            if cost <= 0:
                continue

            cfg = SERVICE_POWER_MAP.get(raw_svc, {
                "code": raw_svc.split(" ")[-1] if " " in raw_svc else raw_svc[:8],
                "alias": raw_svc,
                "category": "AWS Cloud Service",
                "kwh_factor": 0.85
            })

            daily_kwh = round(cost * cfg["kwh_factor"], 2)
            daily_co2 = round(daily_kwh * grid_coeff, 3)

            records.append({
                "InstanceId": cfg["alias"],
                "MachineId": cfg["code"],
                "MachineName": cfg["alias"],
                "InstanceType": cfg["category"],
                "Date": dt_str,
                "DateTime": f"{dt_str} 00:00:00",
                "Energy_kWh": daily_kwh,
                "CarbonFootprint_kg": daily_co2
            })

        df_machines = pd.DataFrame(records)
    else:
        # Generate demo simulated workload telemetry
        df_machines = generate_mock_machine_carbon_data(start_str, end_str, grid_coeff)

    if df_machines.empty:
        st.info("No carbon telemetry available for the selected period.")
        return
        
    tot_co2 = df_machines['CarbonFootprint_kg'].sum()
    tot_kwh = df_machines['Energy_kWh'].sum()
    unique_instances = df_machines['InstanceId'].nunique()
    
    # Top emitting workload
    top_machine_row = df_machines.groupby('InstanceId')['CarbonFootprint_kg'].sum().reset_index().sort_values(by='CarbonFootprint_kg', ascending=False).iloc[0]
    top_machine_name = top_machine_row['InstanceId'].split(' (')[0] if ' (' in top_machine_row['InstanceId'] else top_machine_row['InstanceId']
    top_machine_co2 = top_machine_row['CarbonFootprint_kg']
    
    # KPI Metric Cards
    st.markdown("<div data-section='carbon-kpis'>", unsafe_allow_html=True)
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.markdown(
            f"""
            <div class='metric-card'>
                <p style='margin:0; font-size:0.85rem; color:#9ca3af; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>Total Carbon Emissions</p>
                <h3 style='margin:10px 0 0 0; font-size:2.1rem; font-weight:800; color:#10b981;'>{tot_co2:,.2f} <span style='font-size:1.1rem; font-weight:500;'>kg CO2e</span></h3>
                <p style='margin:6px 0 0 0; font-size:0.8rem; color:#9ca3af;'>Grid factor: {grid_coeff} kg/kWh ({selected_region.split(' - ')[0]})</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_c2:
        st.markdown(
            f"""
            <div class='metric-card'>
                <p style='margin:0; font-size:0.85rem; color:#9ca3af; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>Highest Emitting Workload</p>
                <h3 style='margin:10px 0 0 0; font-size:2.1rem; font-weight:800; color:#f97316;'>{top_machine_co2:,.2f} <span style='font-size:1.1rem; font-weight:500;'>kg</span></h3>
                <p style='margin:6px 0 0 0; font-size:0.8rem; color:#9ca3af; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>Workload: <code>{top_machine_name}</code></p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_c3:
        st.markdown(
            f"""
            <div class='metric-card'>
                <p style='margin:0; font-size:0.85rem; color:#9ca3af; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>Monitored Workloads</p>
                <h3 style='margin:10px 0 0 0; font-size:2.1rem; font-weight:800; color:#38bdf8;'>{unique_instances} <span style='font-size:1.1rem; font-weight:500;'>workloads</span></h3>
                <p style='margin:6px 0 0 0; font-size:0.8rem; color:#9ca3af;'>Total power: {tot_kwh:,.1f} kWh</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    
    # Filter by specific workload if desired
    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        all_workloads = ["All Workloads"] + sorted(list(df_machines['InstanceId'].unique()))
        selected_workload = st.selectbox("Filter Chart by Workload / Service:", options=all_workloads, key="carbon_machine_filter")
    with col_m2:
        chart_type = st.radio("Chart Style:", options=["Time-Series Line", "Grouped Bar"], horizontal=True, key="carbon_chart_style")

    df_chart = df_machines if selected_workload == "All Workloads" else df_machines[df_machines['InstanceId'] == selected_workload]

    # Plotly Chart
    if chart_type == "Time-Series Line":
        fig = px.line(
            df_chart,
            x='Date',
            y='CarbonFootprint_kg',
            color='InstanceId',
            markers=True,
            title=f'Carbon Footprint (kg CO2e) per Workload over Time (Grid Intensity: {grid_coeff} kg/kWh)',
            labels={'CarbonFootprint_kg': 'Carbon Footprint (kg CO2e)', 'Date': 'Date of Usage', 'InstanceId': 'Workload / Service'},
            color_discrete_sequence=MODERN_PALETTE
        )
        fig.update_traces(
            hovertemplate='<b>%{fullData.name}</b><br>Usage Date: %{x}<br>Carbon Footprint: %{y:.2f} kg CO2e<extra></extra>',
            line=dict(width=2.5),
            marker=dict(size=6)
        )
    else:
        fig = px.bar(
            df_chart,
            x='Date',
            y='CarbonFootprint_kg',
            color='InstanceId',
            barmode='group',
            title=f'Carbon Footprint (kg CO2e) per Workload over Time (Grouped)',
            labels={'CarbonFootprint_kg': 'Carbon Footprint (kg CO2e)', 'Date': 'Date of Usage', 'InstanceId': 'Workload / Service'},
            color_discrete_sequence=MODERN_PALETTE
        )
        fig.update_traces(
            hovertemplate='<b>%{fullData.name}</b><br>Usage Date: %{x}<br>Carbon Footprint: %{y:.2f} kg CO2e<extra></extra>'
        )

    apply_finops_chart_theme(fig, height=520, margin_bottom=110)
    c_theme = st.session_state.get('theme', {})
    c_is_paper = c_theme.get('theme_type') in ['paper', 'minimal']
    c_axis_color = '#78716c' if c_is_paper else '#9ca3af'
    c_grid_color = 'rgba(90, 75, 60, 0.08)' if c_is_paper else 'rgba(255,255,255,0.06)'
    
    fig.update_layout(
        xaxis=dict(
            showgrid=False,
            color=c_axis_color,
            tickangle=-45,
            automargin=True,
            tickfont=dict(size=11, family='Plus Jakarta Sans')
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=c_grid_color,
            color=c_axis_color,
            automargin=True,
            tickfont=dict(size=11, family='Plus Jakarta Sans'),
            ticksuffix=" kg"
        )
    )

    st.markdown("<div data-section='carbon-chart' class='chart-container'>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Granular Breakdown Table
    st.markdown("<div data-section='carbon-table'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 1.35rem; font-weight: 700; color: var(--font-color, #ffffff); margin-bottom: 0.8rem;'>Cloud Workload Carbon Footprint Summary</h3>", unsafe_allow_html=True)
    
    summary_df = df_machines.groupby(['MachineId', 'MachineName', 'InstanceType']).agg(
        Total_kWh=('Energy_kWh', 'sum'),
        Total_CO2_kg=('CarbonFootprint_kg', 'sum'),
        Daily_Avg_CO2_kg=('CarbonFootprint_kg', 'mean')
    ).reset_index()
    
    summary_df['Total_kWh'] = summary_df['Total_kWh'].map('{:,.2f} kWh'.format)
    summary_df['Total_CO2_kg'] = summary_df['Total_CO2_kg'].map('{:,.2f} kg CO2e'.format)
    summary_df['Daily_Avg_CO2_kg'] = summary_df['Daily_Avg_CO2_kg'].map('{:,.3f} kg/day'.format)
    summary_df.rename(columns={
        'MachineId': 'Resource Code',
        'MachineName': 'Workload Name',
        'InstanceType': 'Service Category',
        'Total_kWh': 'Total Energy',
        'Total_CO2_kg': 'Total Carbon Footprint',
        'Daily_Avg_CO2_kg': 'Daily Avg CO2e'
    }, inplace=True)
    
    st.dataframe(summary_df, use_container_width=True)
    if is_connected:
        st.caption(f"🌱 *Live AWS Telemetry: Carbon emissions calculated using GHG Protocol Scope 2/3 standard power modeling based on active AWS service usage and {selected_region.split(' - ')[0]} regional grid carbon intensity ({grid_coeff} kg CO2e/kWh).*")
    else:
        st.caption("ℹ️ *Demo Mode: Simulated emissions telemetry based on demo AWS workload models.*")
    st.markdown("</div>", unsafe_allow_html=True)

    # Floating chat widget
    render_floating_chat(key_suffix="carbon", df=df)

def render_chat_view(df: pd.DataFrame):
    """Renders the AI chat window with persistent sessions, New/Delete chat controls, and API configuration."""
    from ai_helper import (
        generate_ai_chat_response,
        load_all_chat_sessions,
        save_all_chat_sessions,
        create_new_chat_session,
        get_default_chat_session
    )

    # 1. Initialize persistent chat sessions
    if 'chat_sessions' not in st.session_state:
        st.session_state['chat_sessions'] = load_all_chat_sessions()
        
    chat_sessions = st.session_state['chat_sessions']
    if not chat_sessions:
        default_sess = get_default_chat_session()
        chat_sessions[default_sess["id"]] = default_sess
        st.session_state['chat_sessions'] = chat_sessions

    if 'active_chat_id' not in st.session_state or st.session_state['active_chat_id'] not in chat_sessions:
        st.session_state['active_chat_id'] = list(chat_sessions.keys())[0]

    active_id = st.session_state['active_chat_id']
    active_session = chat_sessions[active_id]

    import streamlit.components.v1 as components
    components.html("""
    <script>
    (function() {
        try {
            const parentWin = window.parent || window;
            const starter = parentWin.sessionStorage.getItem('finops_mascot_starter');
            if (starter) {
                parentWin.sessionStorage.removeItem('finops_mascot_starter');
                const url = new URL(parentWin.location.href);
                url.searchParams.set('starter', starter);
                parentWin.location.href = url.toString();
            }
        } catch(e) {}
    })();
    </script>
    """, height=0, width=0)

    # Check for incoming mascot starter prompt via query parameter
    starter_prompt = st.query_params.get("starter", None)
    if starter_prompt:
        st.query_params.clear()
        active_session["messages"].append({"role": "user", "content": starter_prompt})
        with st.spinner("Analyzing context via FinOps AI..."):
            reply = generate_ai_chat_response(starter_prompt, df, active_session["messages"])
        active_session["messages"].append({"role": "assistant", "content": reply})
        if len(active_session["messages"]) <= 3:
            active_session["title"] = starter_prompt[:28] + ("..." if len(starter_prompt) > 28 else "")
        save_all_chat_sessions(chat_sessions)
        st.rerun()

    st.markdown("<div data-section='ai-chat'>", unsafe_allow_html=True)
    # 2. Header & Session Control Bar
    col_session_select, col_new, col_del = st.columns([3, 1, 1])
    
    session_options = list(chat_sessions.keys())
    session_labels = {sid: chat_sessions[sid].get("title", f"Chat {sid}") for sid in session_options}
    
    with col_session_select:
        selected_session = st.selectbox(
            "Conversations:",
            options=session_options,
            index=session_options.index(active_id) if active_id in session_options else 0,
            format_func=lambda sid: f"💬 {session_labels.get(sid, sid)}",
            key="chat_session_selector"
        )
        if selected_session != active_id:
            st.session_state['active_chat_id'] = selected_session
            st.rerun()

    with col_new:
        st.write("")
        if st.button("➕ New Chat", key="btn_new_chat_session", use_container_width=True):
            new_sess = create_new_chat_session()
            chat_sessions[new_sess["id"]] = new_sess
            st.session_state['active_chat_id'] = new_sess["id"]
            save_all_chat_sessions(chat_sessions)
            st.toast("Started a new chat session!", icon="✨")
            st.rerun()

    with col_del:
        st.write("")
        if st.button("🗑️ Delete", key="btn_delete_chat_session", use_container_width=True):
            if len(chat_sessions) > 1:
                del chat_sessions[active_id]
                new_active = list(chat_sessions.keys())[0]
                st.session_state['active_chat_id'] = new_active
                save_all_chat_sessions(chat_sessions)
                st.toast("Conversation deleted.", icon="🗑️")
            else:
                fresh_sess = get_default_chat_session()
                st.session_state['chat_sessions'] = {fresh_sess["id"]: fresh_sess}
                st.session_state['active_chat_id'] = fresh_sess["id"]
                save_all_chat_sessions(st.session_state['chat_sessions'])
                st.toast("Chat reset to clean state.", icon="🔄")
            st.rerun()

    # 3. Collapsible AI Provider & Key Settings
    with st.expander("⚙️ Configure AI Model & API Key (OpenAI, Gemini, Claude, Ollama, Custom)", expanded=False):
        col_prov, col_mod = st.columns([1.5, 1.5])
        
        provider_options = [
            "Local Ollama",
            "Google Gemini",
            "OpenAI",
            "Anthropic Claude",
            "Custom Endpoint"
        ]
        default_models = {
            "Local Ollama": "llama3.1:8b",
            "Google Gemini": "gemini-3.6-flash",
            "OpenAI": "gpt-4o-mini",
            "Anthropic Claude": "claude-3-5-sonnet-20241022",
            "Custom Endpoint": "default"
        }
        
        if 'ai_provider_models' not in st.session_state:
            st.session_state['ai_provider_models'] = dict(default_models)
        if 'ai_provider_keys' not in st.session_state:
            st.session_state['ai_provider_keys'] = {}

        curr_prov = st.session_state.get('ai_provider', "Local Ollama")
        
        with col_prov:
            new_prov = st.selectbox(
                "AI Provider / Engine:",
                options=provider_options,
                index=provider_options.index(curr_prov) if curr_prov in provider_options else 0,
                key="chat_provider_select"
            )
            # Detect provider change and instantly update model identifier & API key
            if new_prov != st.session_state.get('prev_ai_provider', curr_prov):
                st.session_state['prev_ai_provider'] = new_prov
                st.session_state['ai_provider'] = new_prov
                target_model = st.session_state['ai_provider_models'].get(new_prov, default_models.get(new_prov, "default"))
                st.session_state['ai_model_name'] = target_model
                st.session_state['chat_model_input'] = target_model
                target_key = st.session_state['ai_provider_keys'].get(new_prov, '')
                st.session_state['ai_api_key'] = target_key
                st.session_state['chat_api_key_input'] = target_key
                auth_manager.save_ai_settings({"active_provider": new_prov})
                st.rerun()

        with col_mod:
            active_model = st.session_state['ai_provider_models'].get(new_prov, default_models.get(new_prov, "default"))
            if 'chat_model_input' not in st.session_state:
                st.session_state['chat_model_input'] = active_model
            new_model = st.text_input("Model Identifier:", value=active_model, key="chat_model_input")
            if new_model != active_model:
                st.session_state['ai_provider_models'][new_prov] = new_model
                st.session_state['ai_model_name'] = new_model
                auth_manager.save_ai_settings({
                    "provider_models": st.session_state['ai_provider_models'],
                    "active_provider": new_prov
                })

        if new_prov in ["Google Gemini", "OpenAI", "Anthropic Claude", "Custom Endpoint"]:
            col_k1, col_k2 = st.columns([2, 1])
            with col_k1:
                saved_key = st.session_state['ai_provider_keys'].get(new_prov, '')
                if 'chat_api_key_input' not in st.session_state:
                    st.session_state['chat_api_key_input'] = saved_key
                new_key = st.text_input(
                    f"{new_prov} API Key:",
                    value=saved_key,
                    type="password",
                    placeholder=f"Enter your {new_prov} API key (saved permanently to vault)",
                    key="chat_api_key_input"
                )
                if new_key != saved_key:
                    st.session_state['ai_provider_keys'][new_prov] = new_key
                    st.session_state['ai_api_key'] = new_key
                    auth_manager.save_ai_settings({
                        "provider_keys": st.session_state['ai_provider_keys'],
                        "active_provider": new_prov
                    })
            with col_k2:
                if new_prov == "Custom Endpoint":
                    curr_ep = st.session_state.get('ai_custom_endpoint', 'http://localhost:8000/v1/chat/completions')
                    new_ep = st.text_input("Endpoint URL:", value=curr_ep, key="chat_custom_endpoint_input")
                    if new_ep != curr_ep:
                        st.session_state['ai_custom_endpoint'] = new_ep
                        auth_manager.save_ai_settings({"custom_endpoint": new_ep})
                else:
                    if saved_key:
                        st.markdown("<p style='color: #10b981; font-weight: 600; font-size: 0.82rem; margin-top: 28px;'>✅ Saved permanently to vault</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color: #9ca3af; font-size: 0.82rem; margin-top: 28px;'>🔒 API key will be saved permanently once entered.</p>", unsafe_allow_html=True)
        elif new_prov == "Local Ollama":
            from ai_helper import ensure_ollama_running
            col_ol1, col_ol2 = st.columns([2.2, 1.2])
            with col_ol1:
                is_running, status_txt = ensure_ollama_running(timeout_seconds=0.8)
                if is_running:
                    st.markdown(f"<p style='color: #10b981; font-weight: 600; font-size: 0.84rem; margin-top: 10px;'>🟢 {status_txt}</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p style='color: #f59e0b; font-weight: 600; font-size: 0.84rem; margin-top: 10px;'>🟡 Ollama daemon is currently stopped. It will auto-start in the background on your next question.</p>", unsafe_allow_html=True)
            with col_ol2:
                if st.button("🚀 Start / Wake Ollama Now", key="chat_wake_ollama", use_container_width=True):
                    with st.spinner("Starting Ollama background daemon..."):
                        ok, msg = ensure_ollama_running(timeout_seconds=8.0)
                        if ok:
                            st.toast(msg, icon="🟢")
                        else:
                            st.error(msg)
                    st.rerun()

        col_save_btn, col_blank = st.columns([1.5, 2])
        with col_save_btn:
            if st.button("💾 Save AI Configuration", key="btn_save_ai_cfg", use_container_width=True):
                auth_manager.save_ai_settings({
                    "active_provider": new_prov,
                    "provider_models": st.session_state['ai_provider_models'],
                    "provider_keys": st.session_state['ai_provider_keys'],
                    "custom_endpoint": st.session_state.get('ai_custom_endpoint', '')
                })
                st.toast(f"Configuration & API key for {new_prov} saved permanently!", icon="✅")

    st.write("")

    # 4. Render Active Chat Conversation
    chat_container = st.container()
    with chat_container:
        for msg in active_session.get("messages", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    # 5. User Chat Input
    if user_input := st.chat_input("Ask about costs, anomalies, reserved instances, or cloud optimization...", key="full_chat_input"):
        active_session["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        active_provider = st.session_state.get('ai_provider', 'AI')
        with st.spinner(f"Analyzing cloud environment via {active_provider}..."):
            response = generate_ai_chat_response(user_input, df, active_session["messages"])
            
        active_session["messages"].append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

        # Set title from first user query if default
        if len(active_session["messages"]) <= 3 or "Conversation" in active_session.get("title", ""):
            active_session["title"] = user_input[:28] + ("..." if len(user_input) > 28 else "")

        save_all_chat_sessions(chat_sessions)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

