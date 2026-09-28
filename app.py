import streamlit as st
import pandas as pd
import datetime
import auth_manager
from cost_engine import get_aws_cost_data
from ui_components import inject_custom_css, inject_mascot_script

# 1. Main Page Configuration (Single source of truth for app setup)
st.set_page_config(
    page_title="AWS FinOps Cost Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Global Session State Initialization
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'theme' not in st.session_state or st.session_state.get('theme', {}).get('theme_type') == 'light':
    loaded_theme = auth_manager.load_anonymous_theme()
    if loaded_theme.get('theme_type') == 'light':
        loaded_theme = {
            "primary_accent": "#c25438",
            "sidebar_bg": "#ece5da",
            "main_bg_start": "#f7f4ee",
            "main_bg_end": "#ede6db",
            "font_color": "#292524",
            "card_bg": "#fcfbf7",
            "theme_type": "paper",
            "card_border": "1px solid #dcd3c4",
            "card_shadow": "0 2px 10px rgba(60, 50, 40, 0.04)"
        }
        auth_manager.save_anonymous_theme(loaded_theme)
    st.session_state['theme'] = loaded_theme

if 'aws_access_key' not in st.session_state:
    st.session_state['aws_access_key'] = ""
if 'aws_secret_key' not in st.session_state:
    st.session_state['aws_secret_key'] = ""
if 'aws_session_token' not in st.session_state:
    st.session_state['aws_session_token'] = ""
if 'aws_connected' not in st.session_state:
    st.session_state['aws_connected'] = False
if 'aws_account_id' not in st.session_state:
    st.session_state['aws_account_id'] = ""
if 'aws_arn' not in st.session_state:
    st.session_state['aws_arn'] = ""

if 'default_lookback_days' not in st.session_state:
    st.session_state['default_lookback_days'] = 30
if 'lookback_days' not in st.session_state:
    st.session_state['lookback_days'] = st.session_state['default_lookback_days']
if 'aggregation_level' not in st.session_state:
    st.session_state['aggregation_level'] = "Day"
if 'selected_region' not in st.session_state:
    st.session_state['selected_region'] = "US East (N. Virginia) - us-east-1"
if 'alert_threshold_pct' not in st.session_state:
    st.session_state['alert_threshold_pct'] = 80.0

if 'show_mascot' not in st.session_state:
    st.session_state['show_mascot'] = True

if 'mascot_shortcut_key' not in st.session_state:
    st.session_state['mascot_shortcut_key'] = 'h'

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [
        {"role": "assistant", "content": "Hello! I am your AI FinOps Assistant. How can I help you analyze or optimize your AWS costs today?"}
    ]

# Initialize persistent AI Model & Provider settings
if 'ai_settings_loaded' not in st.session_state:
    ai_settings = auth_manager.load_ai_settings()
    st.session_state['ai_provider'] = ai_settings.get('active_provider', 'Local Ollama')
    st.session_state['ai_provider_models'] = ai_settings.get('provider_models', auth_manager.DEFAULT_AI_SETTINGS['provider_models'])
    st.session_state['ai_provider_keys'] = ai_settings.get('provider_keys', auth_manager.DEFAULT_AI_SETTINGS['provider_keys'])
    st.session_state['ai_custom_endpoint'] = ai_settings.get('custom_endpoint', 'http://localhost:8000/v1/chat/completions')
    active_prov = st.session_state['ai_provider']
    st.session_state['ai_model_name'] = st.session_state['ai_provider_models'].get(active_prov, 'llama3.1:8b')
    st.session_state['ai_api_key'] = st.session_state['ai_provider_keys'].get(active_prov, '')
    st.session_state['ai_settings_loaded'] = True

# 3. Inject CSS styling
inject_custom_css()

# 4. Standardized st.navigation (Single source of truth for sidebar navigation)
pages = [
    st.Page("pages/profile.py", title="Profile", icon="👤", url_path="profile"),
    st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True, url_path="dashboard"),
    st.Page("pages/carbon_footprint.py", title="Carbon Footprint", icon="🌱", url_path="carbon_footprint"),
    st.Page("pages/analytics.py", title="Resources", icon="📦", url_path="analytics"),
    st.Page("pages/ai_assistant.py", title="AI Assistant", icon="🤖", url_path="ai_assistant"),
    st.Page("pages/settings.py", title="Settings", icon="⚙️", url_path="settings"),
    st.Page("pages/notifications.py", title="Alerts", icon="🔔", url_path="notifications"),
]

nav = st.navigation(pages)

# 5. Sidebar Connection Status Indicator (Filters relocated to Dashboard page)
st.sidebar.markdown("---")

is_connected = st.session_state.get('aws_connected', False)
if is_connected:
    st.sidebar.markdown("""
    <div class='status-badge status-live'>
        <span>●</span> Live AWS Connected
    </div>
    """, unsafe_allow_html=True)
else:
    st.sidebar.markdown("""
    <div class='status-badge status-demo'>
        <span>●</span> Demo / Mock Mode
    </div>
    """, unsafe_allow_html=True)

# 6. Time & Scope State Computation
lookback_days = int(st.session_state.get('lookback_days', 30))
aggregation_level = st.session_state.get('aggregation_level', 'Day')
selected_region = st.session_state.get('selected_region', 'US East (N. Virginia) - us-east-1')

end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=lookback_days)
st.session_state['start_date'] = start_date
st.session_state['end_date'] = end_date
start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")
st.session_state['start_str'] = start_str
st.session_state['end_str'] = end_str

REGION_COEFFS = {
    "US East (N. Virginia) - us-east-1": 0.37,
    "US West (Oregon) - us-west-2": 0.08,
    "EU (Ireland) - eu-west-1": 0.25,
    "Asia Pacific (Singapore) - ap-southeast-1": 0.41
}
grid_coeff = REGION_COEFFS.get(selected_region, 0.37)
st.session_state['grid_coeff'] = grid_coeff

# 7. Fetch & Prepare Data (Cached via @st.cache_data in cost_engine.py)
if is_connected:
    result = get_aws_cost_data(
        start_str,
        end_str,
        aws_access_key_id=st.session_state['aws_access_key'],
        aws_secret_access_key=st.session_state['aws_secret_key'],
        aws_session_token=st.session_state['aws_session_token'] if st.session_state['aws_session_token'] else None
    )
else:
    result = get_aws_cost_data(start_str, end_str)

df_raw = result['data']
status = result['status']
error_msg = result['error_message']

df = df_raw.copy()
df['Date_parsed'] = pd.to_datetime(df['Date'])

if 'Cost' not in df.columns:
    df['Cost'] = 0.0
if 'NetCost' not in df.columns:
    df['NetCost'] = df['Cost']

gross_spend = float(df['Cost'].sum())
net_spend = float(df['NetCost'].sum())

num_days = df['Date'].nunique()
daily_avg = gross_spend / num_days if num_days > 0 else 0.0
annual_projection = daily_avg * 365.25

agg_cols = [c for c in ['Cost', 'NetCost'] if c in df.columns]
if aggregation_level == "Day":
    df_agg = df.groupby(['Date', 'Service'])[agg_cols].sum().reset_index()
    df_agg.rename(columns={'Date': 'Period'}, inplace=True)
elif aggregation_level == "Week":
    df['Week'] = df['Date_parsed'].dt.to_period('W').astype(str)
    df_agg = df.groupby(['Week', 'Service'])[agg_cols].sum().reset_index()
    df_agg.rename(columns={'Week': 'Period'}, inplace=True)
else:
    df['Month'] = df['Date_parsed'].dt.to_period('M').astype(str)
    df_agg = df.groupby(['Month', 'Service'])[agg_cols].sum().reset_index()
    df_agg.rename(columns={'Month': 'Period'}, inplace=True)

# Store in session state for child pages
st.session_state['df'] = df
st.session_state['df_agg'] = df_agg
st.session_state['gross_spend'] = gross_spend
st.session_state['net_spend'] = net_spend
st.session_state['num_days'] = num_days
st.session_state['daily_avg'] = daily_avg
st.session_state['annual_projection'] = annual_projection

# 8. Execute the current selected page
nav.run()

# 9. Mascot Script
inject_mascot_script()
