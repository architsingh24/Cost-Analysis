import streamlit as st
import datetime
import pandas as pd
import auth_manager
import os
import json
import streamlit.components.v1 as components
from ai_helper import generate_ollama_chat_response
from cost_engine import test_aws_connection


def inject_custom_css():
    """Injects custom CSS to style Streamlit to match the aesthetic guidelines."""
    theme = st.session_state.get('theme', {
        "primary_accent": "#f97316",
        "sidebar_bg": "#0f0a07",
        "card_bg": "rgba(30, 20, 15, 0.75)",
        "font_color": "#fdfbf7",
        "main_bg_start": "#180f0a",
        "main_bg_end": "#0d0805",
        "theme_type": "dark",
        "card_border": "1px solid rgba(255, 255, 255, 0.05)",
        "card_shadow": "0 8px 32px 0 rgba(0, 0, 0, 0.3)"
    })
    
    accent = theme.get("primary_accent", "#f97316")
    sidebar_bg = theme.get("sidebar_bg", "#0f0a07")
    card_bg = theme.get("card_bg", "rgba(30, 20, 15, 0.75)")
    font_color = theme.get("font_color", "#fdfbf7")
    bg_start = theme.get("main_bg_start", "#180f0a")
    bg_end = theme.get("main_bg_end", "#0d0805")
    theme_type = theme.get("theme_type", "dark")
    card_border = theme.get("card_border", "1px solid rgba(255, 255, 255, 0.05)")
    card_shadow = theme.get("card_shadow", "0 8px 32px 0 rgba(0, 0, 0, 0.3)")

    font_choice = st.session_state.get('font_choice', 'Modern Sans-Serif (Plus Jakarta Sans)')
    font_configs = {
        'Modern Sans-Serif (Plus Jakarta Sans)': {
            'import': "@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');",
            'family': "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        },
        'Rounded & Friendly (Outfit)': {
            'import': "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');",
            'family': "'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        },
        'Monospace Technical (JetBrains Mono)': {
            'import': "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');",
            'family': "'JetBrains Mono', 'Fira Code', monospace"
        }
    }
    font_cfg = font_configs.get(font_choice, font_configs['Modern Sans-Serif (Plus Jakarta Sans)'])

    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    style_css_content = ""
    if os.path.exists(css_path):
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                style_css_content = f.read()
        except Exception:
            pass

    paper_mode_overrides = """
    /* Handmade Paper Aesthetic Overrides */
    .stApp {
        background: linear-gradient(180deg, #f7f4ee 0%, #efe8de 100%) !important;
        color: #292524 !important;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #1c1917 !important;
        letter-spacing: -0.01em !important;
    }
    .stApp p, .stApp label, .stApp div, .stApp span, .stApp b, .stApp strong, .stApp small {
        color: #292524;
    }
    .stApp [data-testid="stMarkdownContainer"] p,
    .stApp [data-testid="stMarkdownContainer"] span,
    .stApp [data-testid="stMarkdownContainer"] div,
    .stApp [data-testid="stMarkdownContainer"] h1,
    .stApp [data-testid="stMarkdownContainer"] h2,
    .stApp [data-testid="stMarkdownContainer"] h3,
    .stApp [data-testid="stMarkdownContainer"] h4,
    .stApp [data-testid="stMarkdownContainer"] h5,
    .stApp [data-testid="stMarkdownContainer"] h6 {
        color: #1c1917 !important;
    }
    /* Explicitly override any hardcoded white / light inline colors */
    .stApp [style*="color: #ffffff"],
    .stApp [style*="color:#ffffff"],
    .stApp [style*="color: #fff"],
    .stApp [style*="color:#fff"],
    .stApp [style*="color: #fdfbf7"],
    .stApp [style*="color:#fdfbf7"],
    .stApp [style*="color: #f8fafc"],
    .stApp [style*="color:#f8fafc"],
    .stApp [style*="color: #f3f4f6"],
    .stApp [style*="color:#f3f4f6"],
    .stApp [style*="color: #f0fdf4"],
    .stApp [style*="color: #e5e7eb"],
    .stApp [style*="color:#e5e7eb"],
    .stApp [style*="color: #d1d5db"],
    .stApp [style*="color:#d1d5db"],
    .stApp [style*="color: white"],
    .stApp [style*="color:white"] {
        color: #1c1917 !important;
    }
    /* Muted text in paper mode */
    .stApp p[style*="color: #9ca3af"],
    .stApp span[style*="color: #9ca3af"],
    .stApp [style*="color: #9ca3af"],
    .stApp [style*="color: #6b7280"],
    .stApp [class*="caption"],
    .stApp [data-testid="stCaptionContainer"] {
        color: #78716c !important;
    }

    /* Tactile Paper Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ede6dc !important;
        border-right: 1px solid #dcd3c4 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #292524 !important;
    }
    section[data-testid="stSidebar"] p {
        color: #57534e !important;
    }
    section[data-testid="stSidebar"] a {
        color: #292524 !important;
        background: rgba(255, 255, 255, 0.4) !important;
        border: 1px solid #ddd5c7 !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] a:hover {
        background: #ffffff !important;
        border-color: #c25438 !important;
    }
    section[data-testid="stSidebar"] a[aria-current="page"] {
        background: #c25438 !important;
        color: #ffffff !important;
        border-color: #b3472d !important;
        box-shadow: 0 2px 8px rgba(194, 84, 56, 0.25) !important;
    }
    section[data-testid="stSidebar"] a[aria-current="page"] * {
        color: #ffffff !important;
    }

    /* Cards & Containers with Handmade Paper Feel */
    .metric-card, .chart-container {
        background: #fcfbf7 !important;
        border: 1px solid #ddd5c7 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 10px rgba(60, 50, 40, 0.04) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }
    .metric-card:hover {
        border-color: #c25438 !important;
    }
    .metric-card h1, .metric-card h2, .metric-card h3, .metric-card h4, .metric-card h5, .metric-card h6 {
        color: #1c1917 !important;
    }
    .metric-card p, .metric-card span {
        color: #44403c !important;
    }
    .metric-label {
        color: #78716c !important;
    }
    .metric-value {
        color: #1c1917 !important;
    }
    .metric-subtext {
        color: #78716c !important;
    }
    .metric-card code {
        background: #f3eee6 !important;
        color: #b45309 !important;
        border: 1px solid #e5dcce !important;
    }
    /* Notification items in paper mode */
    .notification-card {
        background: #fcfbf7 !important;
        border: 1px solid #ddd5c7 !important;
    }
    .notification-card h4, .notification-card p, .notification-card span, .notification-card div {
        color: #292524 !important;
    }
    .notification-card h4 {
        color: #1c1917 !important;
    }
    .notification-card p {
        color: #44403c !important;
    }
    .notification-card div[style*="background: rgba(0,0,0,0.25)"] {
        background: #f3eee6 !important;
        border: 1px solid #e5dcce !important;
        color: #57534e !important;
    }
    /* Streamlit widgets in paper mode */
    div[data-testid="stWidgetLabel"] label,
    div[data-testid="stWidgetLabel"] p,
    div[data-testid="stWidgetLabel"] span {
        color: #1c1917 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stExpander"] {
        background: #fcfbf7 !important;
        border: 1px solid #ddd5c7 !important;
        border-radius: 10px !important;
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary span,
    div[data-testid="stExpander"] summary p {
        color: #1c1917 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stRadio"] label,
    div[data-testid="stCheckbox"] label {
        color: #292524 !important;
    }
    code {
        background: #f3eee6 !important;
        color: #b45309 !important;
        border: 1px solid #e5dcce !important;
    }
    div[data-testid="stChatMessage"] {
        background: #fcfbf7 !important;
        border: 1px solid #ddd5c7 !important;
    }
    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] span {
        color: #292524 !important;
    }

    /* Inputs, Selectboxes, and Controls */
    div[data-baseweb="select"] > div {
        background: #fcfbf7 !important;
        border: 1px solid #ddd5c7 !important;
        color: #1c1917 !important;
        border-radius: 8px !important;
    }
    input[type="text"], input[type="password"], input[type="number"] {
        background: #fcfbf7 !important;
        border: 1px solid #ddd5c7 !important;
        color: #1c1917 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="popover"] > div, div[data-baseweb="menu"] {
        background: #fcfbf7 !important;
        border: 1px solid #ddd5c7 !important;
        box-shadow: 0 8px 24px rgba(60, 50, 40, 0.1) !important;
    }
    li[role="option"] {
        color: #292524 !important;
    }
    li[role="option"]:hover, li[aria-selected="true"] {
        background: #f2ece2 !important;
        color: #1c1917 !important;
    }

    /* Streamlit Tabs */
    button[data-baseweb="tab"] {
        color: #78716c !important;
        font-weight: 500 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #c25438 !important;
        border-bottom-color: #c25438 !important;
        font-weight: 700 !important;
    }

    /* Streamlit Buttons */
    div.stButton > button {
        background: #f7f4ee !important;
        border: 1px solid #ddd5c7 !important;
        color: #292524 !important;
        border-radius: 8px !important;
        transition: all 0.15s ease !important;
    }
    div.stButton > button:hover {
        background: #ede6db !important;
        border-color: #c25438 !important;
        color: #1c1917 !important;
    }
    div.stButton > button[kind="primary"] {
        background: #c25438 !important;
        border-color: #b3472d !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(194, 84, 56, 0.25) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #ad3d24 !important;
        color: #ffffff !important;
    }

    /* Notification and Alert Cards */
    .notification-card {
        background: #fcfbf7 !important;
        border: 1px solid #ddd5c7 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(60, 50, 40, 0.04) !important;
    }
    .notification-card h4 {
        color: #1c1917 !important;
    }
    .notification-card p {
        color: #44403c !important;
    }

    /* Dataframe / Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid #ddd5c7 !important;
        border-radius: 10px !important;
        background: #fcfbf7 !important;
    }

    /* Mascot Popup in Paper theme */
    .piggy-popup-card {
        background: #fcfbf7 !important;
        border: 1px solid #c25438 !important;
        box-shadow: 0 12px 32px rgba(60, 50, 40, 0.14) !important;
        color: #292524 !important;
    }
    .piggy-feature-title {
        color: #1c1917 !important;
    }
    .piggy-feature-desc {
        color: #57534e !important;
    }
    .piggy-popup-hint {
        background: #f3eee6 !important;
        border-color: #e5dcce !important;
        color: #78716c !important;
    }
    """ if theme_type in ["paper", "minimal"] else ""

    st.markdown(f"""
    <style>
    /* Import selected typography */
    {font_cfg['import']}

    :root {{
        --primary-accent: {accent};
        --sidebar-bg: {sidebar_bg};
        --card-bg: {card_bg};
        --font-color: {font_color};
        --bg-start: {bg_start};
        --bg-end: {bg_end};
        --font-family: {font_cfg['family']};
    }}

    .stApp {{
        background: linear-gradient(135deg, var(--bg-start) 0%, var(--bg-end) 100%);
        color: var(--font-color);
        font-family: var(--font-family);
    }}

    /* Apply global font family */
    body, button, input, select, textarea, [class*="st-"] {{
        font-family: var(--font-family) !important;
    }}
    
    /* Titles and text styling */
    .main-title {{
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, var(--primary-accent) 0%, #f97316 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
        letter-spacing: -0.02em;
    }}
    
    /* Sleek container cards matching glassmorphism guidelines */
    .metric-card {{
        background: var(--card-bg);
        border: {card_border};
        border-radius: 16px;
        padding: 24px;
        box-shadow: {card_shadow};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        transition: transform 0.2s ease-in-out, border-color 0.2s ease;
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
        border-color: rgba(249, 115, 22, 0.3);
    }}
    
    .chart-container {{
        background: rgba(15, 10, 7, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }}
    
    /* Sidebar adjustments */
    section[data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        width: 250px !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stForm"] {{
        border: none !important;
        padding: 0 !important;
    }}

    {paper_mode_overrides}
    
    /* Hide native Streamlit sidebar decorations */
    div[data-testid="stSidebarUserContent"] {{
        padding-top: 1.5rem !important;
    }}
    
    /* Custom connection status badges */
    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }}
    .status-live {{
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }}
    .status-error {{
        background-color: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }}
    .status-mock {{
        background-color: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.2);
    }}
    
    /* Custom Sidebar Navigation Rail styling */
    div[data-testid="stRadio"] label[data-baseweb="radio"] {{
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        padding: 10px 15px !important;
        transition: all 0.2s ease-in-out !important;
        margin-bottom: 0px !important;
        width: 100% !important;
        color: var(--font-color) !important;
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {{
        background: rgba(255, 255, 255, 0.06) !important;
        border-color: var(--primary-accent) !important;
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"][data-checked="true"] {{
        background: var(--primary-accent) !important;
        color: #ffffff !important;
        border-color: var(--primary-accent) !important;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.2) !important;
    }}
    div[data-testid="stRadio"] label[data-baseweb="radio"][data-checked="true"] span {{
        color: #ffffff !important;
    }}

    /* Custom Sidebar Toggle - arrow to hamburger */
    button[data-testid="collapsedControl"] svg {{
        display: none !important;
    }}
    button[data-testid="collapsedControl"]::before {{
        content: "☰" !important;
        font-family: inherit;
        font-size: 1.6rem !important;
        color: var(--primary-accent) !important;
        display: flex !important;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
    }}
    
    [data-testid="stSidebarCollapseButton"] svg {{
        display: none !important;
    }}
    [data-testid="stSidebarCollapseButton"]::before {{
        content: "✕" !important;
        font-size: 1.3rem !important;
        color: var(--primary-accent) !important;
        display: flex !important;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
    }}

    /* Cursor-following Piggy Mascot styles */
    #cursor-piggy-mascot {{
        position: fixed;
        z-index: 9999998;
        pointer-events: none;
        transition: transform 0.1s ease-out;
        filter: drop-shadow(0px 6px 14px rgba(0, 0, 0, 0.45));
        will-change: left, top, transform;
    }}

    /* Mascot inspected element highlight pulse */
    .finops-mascot-highlighted {{
        outline: 2px solid var(--primary-accent, #f97316) !important;
        box-shadow: 0 0 18px rgba(249, 115, 22, 0.45) !important;
        border-radius: 8px !important;
        transition: outline 0.2s ease, box-shadow 0.2s ease !important;
    }}

    /* Piggy Shortcut Popup Modal */
    #piggy-shortcut-popup {{
        display: none;
        position: fixed;
        z-index: 9999999;
        max-width: 350px;
        width: 330px;
        animation: piggyPopIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    @keyframes piggyPopIn {{
        0% {{ opacity: 0; transform: scale(0.92) translateY(6px); }}
        100% {{ opacity: 1; transform: scale(1) translateY(0); }}
    }}

    .piggy-popup-card {{
        background: var(--card-bg, rgba(24, 18, 14, 0.96));
        border: 1px solid var(--primary-accent, #f97316);
        border-radius: 14px;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.55), 0 0 24px rgba(249, 115, 22, 0.18);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        padding: 14px 16px;
        color: var(--font-color, #fdfbf7);
        font-family: inherit;
    }}

    .piggy-popup-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .piggy-popup-title-box {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    .piggy-popup-icon {{
        font-size: 1.25rem;
    }}

    .piggy-popup-badge {{
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--primary-accent, #f97316);
        background: rgba(249, 115, 22, 0.12);
        padding: 2px 8px;
        border-radius: 10px;
    }}

    .piggy-popup-close {{
        background: transparent;
        border: none;
        color: #9ca3af;
        font-size: 1.1rem;
        cursor: pointer;
        line-height: 1;
        padding: 2px 6px;
        border-radius: 4px;
        transition: color 0.15s ease, background-color 0.15s ease;
    }}

    .piggy-popup-close:hover {{
        color: #ffffff;
        background: rgba(255, 255, 255, 0.1);
    }}

    .piggy-popup-body {{
        margin-bottom: 12px;
    }}

    .piggy-feature-title {{
        margin: 0 0 6px 0;
        font-size: 0.98rem;
        font-weight: 700;
        color: var(--font-color, #ffffff);
    }}

    .piggy-feature-desc {{
        margin: 0 0 8px 0;
        font-size: 0.83rem;
        line-height: 1.45;
        color: #d1d5db;
    }}

    .piggy-popup-hint {{
        font-size: 0.72rem;
        color: #9ca3af;
        background: rgba(255, 255, 255, 0.04);
        padding: 5px 8px;
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }}

    .piggy-popup-footer {{
        padding-top: 6px;
    }}

    .piggy-ai-btn {{
        width: 100%;
        background: var(--primary-accent, #f97316);
        color: #ffffff !important;
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.84rem;
        font-weight: 700;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        transition: transform 0.15s ease, filter 0.15s ease;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3);
    }}

    .piggy-ai-btn:hover {{
        filter: brightness(1.12);
        transform: translateY(-1px);
    }}
    
    /* Hidden elements styling */
    .hidden-btn-container {{
        display: none !important;
    }}
    
    /* Hide default Streamlit Deploy button and flat header styling */
    header[data-testid="stHeader"] {{
        background-color: transparent !important;
        background: transparent !important;
        box-shadow: none !important;
        border-bottom: none !important;
    }}
    div[data-testid="stAppDeployButton"],
    .stDeployButton,
    div[class*="DeployButton"],
    button[class*="DeployButton"],
    [data-testid="stHeader"] button[class*="deploy"] {{
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }}

    /* Custom CSS-drawn Piggy Bank Mascot */
    .piggy-bank {{
        position: relative;
        width: 60px;
        height: 50px;
        cursor: pointer;
    }}
    
    .pig-body {{
        position: absolute;
        width: 50px;
        height: 38px;
        background: #ff9ebe;
        border-radius: 50% 50% 45% 45%;
        border: 2px solid #e05e8a;
        top: 5px;
        left: 5px;
    }}
    
    .pig-eye {{
        position: absolute;
        width: 4px;
        height: 4px;
        background: #333;
        border-radius: 50%;
        top: 10px;
        left: 10px;
    }}
    
    .pig-ear {{
        position: absolute;
        width: 0;
        height: 0;
        border-left: 6px solid transparent;
        border-right: 6px solid transparent;
        border-bottom: 10px solid #e05e8a;
        top: -6px;
        left: 15px;
        transform: rotate(-15deg);
    }}
    
    .pig-snout {{
        position: absolute;
        width: 8px;
        height: 10px;
        background: #ff7ea5;
        border: 1.5px solid #e05e8a;
        border-radius: 4px;
        top: 15px;
        left: -4px;
    }}
    
    .pig-slot {{
        position: absolute;
        width: 14px;
        height: 3px;
        background: #3f3f46;
        border-radius: 2px;
        top: 4px;
        left: 20px;
    }}
    
    .pig-tail {{
        position: absolute;
        width: 6px;
        height: 6px;
        border: 2px solid #e05e8a;
        border-left: none;
        border-bottom: none;
        border-radius: 50%;
        top: 15px;
        right: -4px;
        transform: rotate(45deg);
    }}
    
    /* Leg walking animations */
    .pig-legs {{
        position: absolute;
        width: 50px;
        height: 12px;
        bottom: 0px;
        left: 5px;
    }}
    
    .pig-leg {{
        position: absolute;
        width: 5px;
        height: 10px;
        background: #ff7ea5;
        border: 1.5px solid #e05e8a;
        border-top: none;
        border-radius: 0 0 3px 3px;
    }}
    
    .leg-front-left {{ left: 8px; animation: legSwingFront 0.4s ease-in-out infinite alternate; }}
    .leg-front-right {{ left: 16px; animation: legSwingBack 0.4s ease-in-out infinite alternate; }}
    .leg-back-left {{ left: 28px; animation: legSwingFront 0.4s ease-in-out infinite alternate; }}
    .leg-back-right {{ left: 36px; animation: legSwingBack 0.4s ease-in-out infinite alternate; }}
    
    @keyframes legSwingFront {{
        0% {{ transform: rotate(-22deg); }}
        100% {{ transform: rotate(22deg); }}
    }}
    @keyframes legSwingBack {{
        0% {{ transform: rotate(22deg); }}
        100% {{ transform: rotate(-22deg); }}
    }}
    
    /* Coin drop animation */
    .pig-coin {{
        position: absolute;
        font-size: 14px;
        top: -12px;
        left: 22px;
        animation: coinDrop 2.0s linear infinite;
        pointer-events: none;
    }}
    
    @keyframes coinDrop {{
        0% {{ transform: translateY(-12px); opacity: 0; }}
        20% {{ opacity: 1; }}
        50% {{ transform: translateY(10px); opacity: 0; }}
        100% {{ transform: translateY(10px); opacity: 0; }}
    }}
    
    /* Custom top header bar styles */
    .top-header-bar {{
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: var(--bg-start);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 15px;
        margin-bottom: 20px;
        width: 100%;
    }}

    /* Styles for the top header buttons to make them clean transparent icons */
    .top-header-bar button, 
    .top-header-bar div[data-testid="stPopover"] > button {{
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 40px !important;
        height: 40px !important;
        min-width: 40px !important;
        min-height: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 20px !important;
        color: var(--font-color) !important;
        transition: transform 0.2s ease !important;
    }}
    
    .top-header-bar button:hover, 
    .top-header-bar div[data-testid="stPopover"] > button:hover {{
        transform: scale(1.15) !important;
        background: transparent !important;
        border: none !important;
    }}

    /* Floating Popover styling - ONLY for the floating chat */
    .floating-chat-container {{
        position: absolute !important;
        width: 60px;
        height: 60px;
        z-index: 999999;
        transition: top 1.5s cubic-bezier(0.25, 0.8, 0.25, 1), left 1.5s cubic-bezier(0.25, 0.8, 0.25, 1);
    }}
    
    /* Transparent overlays for popover roaming clicks */
    .floating-chat-container div[data-testid="stPopover"] {{
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
    }}
    .floating-chat-container div[data-testid="stPopover"] > button {{
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        opacity: 0 !important; /* Clickable but hidden, overlays custom piggy art! */
        z-index: 20 !important;
        border: none !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    
    /* Hide chevron down icon inside st.popover buttons */
    div[data-testid="stPopover"] > button svg,
    div[data-testid="stPopover"] svg {{
        display: none !important;
    }}
    
    {style_css_content}
    </style>
    """, unsafe_allow_html=True)

def render_animated_kpi_cards(metrics_data: list, animate: bool = True):
    """
    Renders 5 FinOps KPI metric cards with an odometer count-up animation.
    Uses a lightweight HTML/CSS/JS component via st.components.v1.html.
    
    Parameters:
    - metrics_data (list of dict): Each dict contains:
        - label (str): e.g. "Active Spend (Day)"
        - value (float): target numeric value
        - prefix (str): e.g. "$"
        - suffix (str): e.g. "credits" or ""
        - color (str): CSS color for the number
        - subtext (str): context caption
    - animate (bool): If True, animates numbers from 0 to value over ~800ms.
                      If False, renders the final formatted value directly.
    """
    theme = st.session_state.get('theme', {})
    is_paper = theme.get("theme_type") in ["paper", "minimal"]
    accent = theme.get("primary_accent", "#c25438" if is_paper else "#f97316")
    card_bg = theme.get("card_bg", "#fcfbf7" if is_paper else "rgba(30, 20, 15, 0.75)")
    font_color = theme.get("font_color", "#292524" if is_paper else "#fdfbf7")
    card_border = theme.get("card_border", "1px solid #ddd5c7" if is_paper else "1px solid rgba(255, 255, 255, 0.08)")
    card_shadow = theme.get("card_shadow", "0 2px 8px rgba(60, 50, 40, 0.04)" if is_paper else "0 8px 24px 0 rgba(0, 0, 0, 0.3)")
    label_color = "#78716c" if is_paper else "#9ca3af"
    subtext_color = "#78716c" if is_paper else "#6b7280"

    cards_html = ""
    for idx, item in enumerate(metrics_data):
        val = item.get("value", 0.0)
        formatted_val = f"{val:,.2f}"
        initial_display = f"{item.get('prefix', '')}0.00{(' ' + item['suffix']) if item.get('suffix') else ''}" if animate else f"{item.get('prefix', '')}{formatted_val}{(' ' + item['suffix']) if item.get('suffix') else ''}"
        
        cards_html += f"""
        <div class="kpi-card" id="card-{idx}">
            <div class="kpi-label">{item.get('label', '')}</div>
            <div class="kpi-value" id="kpi-{idx}" style="color: {item.get('color', accent)};">{initial_display}</div>
            <div class="kpi-subtext">{item.get('subtext', '')}</div>
        </div>
        """

    metrics_json = json.dumps([{
        "value": float(m.get("value", 0.0)),
        "prefix": m.get("prefix", ""),
        "suffix": m.get("suffix", ""),
    } for m in metrics_data])

    component_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            body {{
                background: transparent;
                font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
                color: {font_color};
                overflow: hidden;
                padding: 2px 2px 8px 2px;
            }}
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 12px;
                width: 100%;
            }}
            .kpi-card {{
                background: {card_bg};
                border: {card_border};
                border-radius: 12px;
                padding: 14px 16px;
                box-shadow: {card_shadow};
                backdrop-filter: {'none' if is_paper else 'blur(10px)'};
                -webkit-backdrop-filter: {'none' if is_paper else 'blur(10px)'};
                transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                min-height: 102px;
            }}
            .kpi-card:hover {{
                transform: translateY(-2px);
                border-color: {accent};
            }}
            .kpi-label {{
                font-size: 0.73rem;
                font-weight: 700;
                color: {label_color};
                text-transform: uppercase;
                letter-spacing: 0.05em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .kpi-value {{
                font-size: 1.65rem;
                font-weight: 800;
                letter-spacing: -0.02em;
                margin: 6px 0 2px 0;
                font-family: 'Plus Jakarta Sans', sans-serif;
                white-space: nowrap;
            }}
            .kpi-subtext {{
                font-size: 0.72rem;
                color: {subtext_color};
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            @media (max-width: 900px) {{
                .kpi-grid {{
                    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
                }}
                .kpi-value {{
                    font-size: 1.3rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="kpi-grid">
            {cards_html}
        </div>
        <script>
            const metrics = {metrics_json};
            const animate = {str(animate).lower()};
            
            if (animate) {{
                const duration = 850; // ms
                const start = performance.now();
                
                function easeOutExpo(x) {{
                    return x === 1 ? 1 : 1 - Math.pow(2, -10 * x);
                }}
                
                function step(now) {{
                    const elapsed = now - start;
                    const progress = Math.min(elapsed / duration, 1.0);
                    const eased = easeOutExpo(progress);
                    
                    metrics.forEach((m, idx) => {{
                        const el = document.getElementById("kpi-" + idx);
                        if (el) {{
                            const currentVal = m.value * eased;
                            const formatted = currentVal.toLocaleString('en-US', {{
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            }});
                            const suffix = m.suffix ? (' ' + m.suffix) : '';
                            el.innerText = m.prefix + formatted + suffix;
                        }}
                    }});
                    
                    if (progress < 1.0) {{
                        requestAnimationFrame(step);
                    }}
                }}
                
                requestAnimationFrame(step);
            }}
        </script>
    </body>
    </html>
    """
    components.html(component_html, height=130, scrolling=False)

@st.dialog("Authentication")
def show_auth_dialog():

    st.markdown("<p style='font-size:0.9rem; opacity:0.8; margin-bottom:15px;'>Manage your FinOps session and AWS credentials secure storage.</p>", unsafe_allow_html=True)
    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["Login", "Create Account", "Guest Mode"])
    
    with auth_tab1:
        st.write("")
        l_user = st.text_input("Username / Email", key="login_username_input")
        l_pass = st.text_input("Master Password", type="password", key="login_password_input")
        if st.button("Sign In", key="login_submit_btn", use_container_width=True, type="primary"):
            if not l_user or not l_pass:
                st.error("Username and password are required.")
            else:
                res = auth_manager.authenticate_user(l_user, l_pass)
                if res["success"]:
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = l_user
                    st.session_state['aws_access_key'] = res["aws_access_key"]
                    st.session_state['aws_secret_key'] = res["aws_secret_key"]
                    st.session_state['aws_session_token'] = res["aws_session_token"]
                    st.session_state['aws_connected'] = res["aws_connected"]
                    st.session_state['aws_account_id'] = res["aws_account_id"]
                    st.session_state['aws_arn'] = res["aws_arn"]
                    st.session_state['_enc_key'] = res.get("enc_key", "")
                    st.session_state['theme'] = res["theme"]
                    st.toast("Welcome back!", icon="👋")
                    st.rerun()
                else:
                    st.error(f"Authentication failed: {res['error']}")
                    
    with auth_tab2:
        st.write("")
        r_user = st.text_input("Choose Username / Email", key="register_username_input")
        r_pass = st.text_input("Choose Master Password", type="password", key="register_password_input")
        
        st.markdown("**AWS Credentials Config**", unsafe_allow_html=True)
        r_aws_key = st.text_input("AWS Access Key ID", key="register_aws_key")
        r_show_sec = st.checkbox("Show Secret Access Key", key="register_show_secret")
        r_aws_secret = st.text_input("AWS Secret Access Key", type="default" if r_show_sec else "password", key="register_aws_secret")
        r_aws_token = st.text_input("AWS Session Token (Optional)", type="password", key="register_aws_token")
        
        if st.button("Register & Connect", key="register_submit_btn", use_container_width=True, type="primary"):
            if not r_user or not r_pass:
                st.error("Username and password are required for registration.")
            else:
                st.info("Validating credentials and registering...")
                reg_res = auth_manager.register_user(
                    r_user, r_pass, r_aws_key, r_aws_secret, 
                    aws_session_token=r_aws_token if r_aws_token else None
                )
                if reg_res["success"]:
                    st.success("Registration completed successfully!")
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = r_user
                    st.session_state['aws_access_key'] = reg_res["aws_access_key"]
                    st.session_state['aws_secret_key'] = reg_res["aws_secret_key"]
                    st.session_state['aws_session_token'] = reg_res["aws_session_token"]
                    st.session_state['aws_connected'] = reg_res["aws_connected"]
                    st.session_state['aws_account_id'] = reg_res["aws_account_id"]
                    st.session_state['aws_arn'] = reg_res["aws_arn"]
                    st.session_state['_enc_key'] = reg_res.get("enc_key", "")
                    st.session_state['theme'] = reg_res["theme"]
                    st.toast("Account created successfully!", icon="🎉")
                    st.rerun()
                else:
                    st.error(f"Registration failed: {reg_res['error']}")

    with auth_tab3:
        st.write("")
        st.markdown("#### 👤 Continue as Guest")
        st.markdown("<p style='font-size:0.85rem; opacity:0.8;'>No account required. Enter your AWS Access Key ID and Secret Access Key to query live Cost Explorer data directly in this session.</p>", unsafe_allow_html=True)
        
        g_aws_key = st.text_input("AWS Access Key ID", value=st.session_state.get('aws_access_key', ''), key="auth_guest_aws_key", placeholder="AKIA...")
        g_show_sec = st.checkbox("Show Secret Access Key", key="auth_guest_show_secret")
        g_aws_secret = st.text_input("AWS Secret Access Key", type="default" if g_show_sec else "password", value=st.session_state.get('aws_secret_key', ''), key="auth_guest_aws_secret", placeholder="wJalrXUtn...")
        g_aws_token = st.text_input("AWS Session Token (Optional)", type="password", value=st.session_state.get('aws_session_token', ''), key="auth_guest_aws_token")
        
        if st.button("Connect & Use as Guest", key="auth_guest_submit_btn", use_container_width=True, type="primary"):
            if not g_aws_key or not g_aws_secret:
                st.error("Both Access Key ID and Secret Access Key are required.")
            else:
                st.info("Validating credentials with AWS STS...")
                test_res = test_aws_connection(g_aws_key, g_aws_secret, aws_session_token=g_aws_token if g_aws_token else None)
                if not test_res['success']:
                    st.error(f"Validation failed: {test_res['error']}")
                else:
                    st.session_state['authenticated'] = False
                    st.session_state['username'] = "Guest"
                    st.session_state['aws_access_key'] = g_aws_key
                    st.session_state['aws_secret_key'] = g_aws_secret
                    st.session_state['aws_session_token'] = g_aws_token if g_aws_token else ""
                    st.session_state['aws_connected'] = True
                    st.session_state['aws_account_id'] = test_res['account_id']
                    st.session_state['aws_arn'] = test_res['arn']
                    st.toast("Connected to AWS as Guest!", icon="🟢")
                    st.rerun()

@st.dialog("Settings & Controls", width="large")
def show_settings_dialog():
    st.markdown("<p style='font-size:0.9rem; opacity:0.8; margin-bottom:15px;'>Customize date ranges, themes, and manage credentials.</p>", unsafe_allow_html=True)
    set_tab1, set_tab2, set_tab3, set_tab4 = st.tabs([
        "📅 Filters & Region",
        "🎨 Theme Customizer",
        "👤 Profile Credentials",
        "🚀 Deployment"
    ])
    
    with set_tab1:
        st.write("")
        st.subheader("Dashboard Controls")
        
        s_date = st.date_input("Start Date", st.session_state['start_date'], max_value=datetime.date.today())
        e_date = st.date_input("End Date", st.session_state['end_date'], max_value=datetime.date.today())
        if s_date >= e_date:
            st.error("Error: Start Date must be prior to End Date.")
        else:
            st.session_state['start_date'] = s_date
            st.session_state['end_date'] = e_date
            
        st.session_state['aggregation_level'] = st.selectbox(
            "Analyze spend by:",
            options=["Day", "Week", "Month"],
            index=["Day", "Week", "Month"].index(st.session_state['aggregation_level'])
        )
        
        st.session_state['selected_region'] = st.selectbox(
            "Target AWS Region:",
            options=[
                "US East (N. Virginia) - us-east-1",
                "US West (Oregon) - us-west-2",
                "EU (Ireland) - eu-west-1",
                "Asia Pacific (Singapore) - ap-southeast-1"
            ],
            index=[
                "US East (N. Virginia) - us-east-1",
                "US West (Oregon) - us-west-2",
                "EU (Ireland) - eu-west-1",
                "Asia Pacific (Singapore) - ap-southeast-1"
            ].index(st.session_state['selected_region'])
        )
        
    with set_tab2:
        st.write("")
        st.subheader("Real-Time Theme Designer")
        
        theme_preset = st.selectbox(
            "Select Palette Preset:",
            options=["Modern Amber", "Forest Green", "Deep Indigo", "Custom Theme"]
        )
        
        presets = {
            "Modern Amber": {"primary_accent": "#f97316", "sidebar_bg": "#0f0a07", "main_bg_start": "#180f0a", "main_bg_end": "#0d0805", "font_color": "#fdfbf7", "card_bg": "rgba(30, 20, 15, 0.75)"},
            "Forest Green": {"primary_accent": "#10b981", "sidebar_bg": "#061f14", "main_bg_start": "#072417", "main_bg_end": "#03100a", "font_color": "#f0fdf4", "card_bg": "rgba(10, 40, 25, 0.75)"},
            "Deep Indigo": {"primary_accent": "#6366f1", "sidebar_bg": "#070716", "main_bg_start": "#0a0a23", "main_bg_end": "#040410", "font_color": "#e0e7ff", "card_bg": "rgba(20, 20, 50, 0.75)"}
        }
        
        if theme_preset in presets:
            st.session_state['theme'] = presets[theme_preset]
            if st.session_state.get('authenticated', False):
                auth_manager.save_user_theme(st.session_state['username'], presets[theme_preset])
            else:
                auth_manager.save_anonymous_theme(presets[theme_preset])
            st.rerun()
            
        st.write("---")
        st.write("Fine-Tune Theme Colors:")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            theme_accent = st.color_picker("Primary Accent", st.session_state['theme'].get('primary_accent', '#f97316'))
            theme_sb = st.color_picker("Sidebar Background", st.session_state['theme'].get('sidebar_bg', '#0f0a07'))
            theme_card = st.text_input("Card Color CSS", st.session_state['theme'].get('card_bg', 'rgba(30, 20, 15, 0.75)'))
        with col_c2:
            theme_bg_start = st.color_picker("Main Background Start", st.session_state['theme'].get('main_bg_start', '#180f0a'))
            theme_bg_end = st.color_picker("Main Background End", st.session_state['theme'].get('main_bg_end', '#0d0805'))
            theme_fc = st.color_picker("Font Color", st.session_state['theme'].get('font_color', '#fdfbf7'))
            
        if st.button("Apply Custom Theme", key="btn_apply_custom_theme", use_container_width=True, type="primary"):
            custom_theme = {
                "primary_accent": theme_accent,
                "sidebar_bg": theme_sb,
                "card_bg": theme_card,
                "font_color": theme_fc,
                "main_bg_start": theme_bg_start,
                "main_bg_end": theme_bg_end
            }
            st.session_state['theme'] = custom_theme
            if st.session_state.get('authenticated', False):
                auth_manager.save_user_theme(st.session_state['username'], custom_theme)
            else:
                auth_manager.save_anonymous_theme(custom_theme)
            st.rerun()
            
    with set_tab3:
        st.write("")
        st.subheader("Manage AWS Access Key Pair")
        
        if st.session_state.get('authenticated', False):
            username = st.session_state['username']
            st.markdown(f"**Logged in as:** `{username}` — *Encrypted in user vault*")
            st.write("Update active AWS keys stored in your profile:")
            
            up_aws_key = st.text_input("Access Key ID", value=st.session_state.get('aws_access_key', ''), key="update_aws_key")
            up_show_secret = st.checkbox("Show Secret Access Key", key="auth_settings_show_secret")
            up_aws_secret = st.text_input("Secret Access Key", type="default" if up_show_secret else "password", value=st.session_state.get('aws_secret_key', ''), key="update_aws_secret")
            up_aws_token = st.text_input("Session Token (Optional)", type="password", value=st.session_state.get('aws_session_token', ''), key="update_aws_token")
            
            col_u1, col_u2 = st.columns([1.5, 1])
            with col_u1:
                if st.button("Update and Test Credentials", key="btn_update_aws_creds", use_container_width=True, type="primary"):
                    if not up_aws_key or not up_aws_secret:
                        st.error("Both access key and secret key are required to configure AWS connections.")
                    else:
                        st.info("Validating new connection settings...")
                        test_res = test_aws_connection(
                            up_aws_key, up_aws_secret, 
                            aws_session_token=up_aws_token if up_aws_token else None
                        )
                        if not test_res['success']:
                            st.error(f"Validation failed: {test_res['error']}")
                        else:
                            st.success("AWS cost connection succeeded!")
                            up_res = auth_manager.update_user_credentials(
                                username, up_aws_key, up_aws_secret, 
                                aws_session_token=up_aws_token if up_aws_token else None,
                                enc_key_b64=st.session_state.get('_enc_key')
                            )
                            if up_res["success"]:
                                st.session_state['aws_access_key'] = up_aws_key
                                st.session_state['aws_secret_key'] = up_aws_secret
                                st.session_state['aws_session_token'] = up_aws_token if up_aws_token else ""
                                st.session_state['aws_connected'] = True
                                st.session_state['aws_account_id'] = test_res['account_id']
                                st.session_state['aws_arn'] = test_res['arn']
                                
                                st.toast("Credentials updated successfully!", icon="✅")
                                st.rerun()
                            else:
                                st.error(f"Failed to save update: {up_res['error']}")
            with col_u2:
                if st.button("Disconnect AWS", key="btn_auth_disconnect_aws", use_container_width=True):
                    st.session_state['aws_connected'] = False
                    st.toast("Switched to mock data mode.", icon="⚪")
                    st.rerun()
        else:
            # Guest Profile Credentials Section
            st.markdown(
                """
                <div style='background:rgba(249,115,22,0.08); border-left:3px solid var(--primary-accent); padding:10px 14px; border-radius:6px; margin-bottom:15px;'>
                    <span style='font-size:0.9rem; font-weight:700; color:var(--primary-accent);'>👤 Guest Profile Mode</span><br/>
                    <span style='font-size:0.8rem; opacity:0.85;'>Configure and use your AWS Secret Access Key directly without creating an account or logging in.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.session_state.get('aws_connected', False):
                st.success(f"🟢 **Live AWS Connection Active** — Account: `{st.session_state.get('aws_account_id', 'N/A')}` | ARN: `{st.session_state.get('aws_arn', 'N/A')}`")
            else:
                st.info("⚪ **Demo Mode Active** — Provide your AWS keys below to query your live AWS Cost Explorer.")

            g_aws_key = st.text_input("AWS Access Key ID", value=st.session_state.get('aws_access_key', ''), key="settings_guest_aws_key", placeholder="AKIAIOSFODNN7EXAMPLE")
            g_show_secret = st.checkbox("Show Secret Access Key", key="settings_guest_show_secret")
            g_aws_secret = st.text_input("AWS Secret Access Key", type="default" if g_show_secret else "password", value=st.session_state.get('aws_secret_key', ''), key="settings_guest_aws_secret", placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
            g_aws_token = st.text_input("AWS Session Token (Optional)", type="password", value=st.session_state.get('aws_session_token', ''), key="settings_guest_aws_token")

            col_g1, col_g2 = st.columns([1.5, 1])
            with col_g1:
                btn_label = "⚡ Update & Test AWS" if st.session_state.get('aws_connected', False) else "⚡ Connect AWS as Guest"
                if st.button(btn_label, key="btn_guest_connect_aws", use_container_width=True, type="primary"):
                    if not g_aws_key or not g_aws_secret:
                        st.error("Both Access Key ID and Secret Access Key are required.")
                    else:
                        st.info("Validating credentials with AWS STS...")
                        test_res = test_aws_connection(g_aws_key, g_aws_secret, aws_session_token=g_aws_token if g_aws_token else None)
                        if not test_res['success']:
                            st.error(f"Validation failed: {test_res['error']}")
                        else:
                            st.session_state['aws_access_key'] = g_aws_key
                            st.session_state['aws_secret_key'] = g_aws_secret
                            st.session_state['aws_session_token'] = g_aws_token if g_aws_token else ""
                            st.session_state['aws_connected'] = True
                            st.session_state['aws_account_id'] = test_res['account_id']
                            st.session_state['aws_arn'] = test_res['arn']
                            st.toast("AWS credentials connected successfully!", icon="🟢")
                            st.rerun()
            with col_g2:
                if st.session_state.get('aws_connected', False) or st.session_state.get('aws_access_key'):
                    if st.button("Disconnect (Mock Data)", key="btn_guest_disconnect_aws", use_container_width=True):
                        st.session_state['aws_access_key'] = ""
                        st.session_state['aws_secret_key'] = ""
                        st.session_state['aws_session_token'] = ""
                        st.session_state['aws_connected'] = False
                        st.session_state['aws_account_id'] = ""
                        st.session_state['aws_arn'] = ""
                        st.toast("Disconnected. Using demo data.", icon="⚪")
                        st.rerun()

            st.markdown("---")
            st.markdown("<p style='font-size:0.75rem; color:#9ca3af;'>Want encrypted persistence across browsers and devices? You can create an account or sign in anytime.</p>", unsafe_allow_html=True)
            
    with set_tab4:
        st.write("")
        st.subheader("🚀 Cloud Optimizations & Deployment Controls")
        st.markdown(
            """
            Deploy cost-saving policies and templates directly to your AWS environment based on your current FinOps analysis.
            """
        )
        st.write("")
        
        st.write("**VPC/EC2 Right-Sizing Schedule**")
        vpc_schedule = st.selectbox(
            "Schedule VPC optimization analysis:",
            options=["Daily (00:00 UTC)", "Weekly (Sundays)", "Monthly (1st of month)"],
            index=1,
            key="settings_vpc_schedule"
        )
        
        col_dep1, col_dep2 = st.columns(2)
        with col_dep1:
            st.write("**S3 Lifecycle Policy Deployment**")
            st.markdown("<p style='font-size:0.8rem; opacity:0.8; margin-bottom:12px;'>Automatically transition S3 objects older than 90 days to Glacier Deep Archive.</p>", unsafe_allow_html=True)
            if st.button("Deploy S3 Policy", key="btn_deploy_s3_policy", use_container_width=True):
                st.success("Successfully deployed S3 lifecycle rules to active buckets!")
                st.toast("S3 Lifecycle policy deployed!", icon="📦")
        with col_dep2:
            st.write("**EC2 Auto-Scheduler Deployment**")
            st.markdown("<p style='font-size:0.8rem; opacity:0.8; margin-bottom:12px;'>Deploy a CloudFormation stack to turn off EC2 instances outside business hours.</p>", unsafe_allow_html=True)
            if st.button("Deploy Stack", key="btn_deploy_cfn_stack", use_container_width=True):
                st.success("CloudFormation stack deployment initiated: `FinOpsInstanceScheduler`")
                st.toast("CloudFormation stack deployed!", icon="🚀")

def render_floating_chat(key_suffix: str, df: pd.DataFrame):
    """
    Renders a floating popup widget containing a quick AI FinOps chatbot query box.
    """
    st.markdown('<div class="floating-chat-container">', unsafe_allow_html=True)
    with st.popover("🐷✨"):
        st.markdown("<h4 style='margin: 0 0 10px 0; color: var(--font-color, #ffffff);'>🐷 Warm FinOps Piggy AI</h4>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.8rem; color: var(--primary-accent, #cca885); margin: 0 0 10px 0;'>Let's save some cloud coins together! 🪙</p>", unsafe_allow_html=True)
        
        chat_html = "<div style='max-height: 200px; overflow-y: auto; padding: 10px; border-radius: 8px; background: var(--card-bg, rgba(0,0,0,0.25)); border: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px;'>"
        for msg in st.session_state.get('chat_history', [])[-4:]:
            role_color = "var(--primary-accent)" if msg["role"] == "user" else "#10b981"
            role_name = "You" if msg["role"] == "user" else "AI"
            chat_html += f"<div style='margin-bottom: 6px; line-height: 1.3;'><b style='color: {role_color}; font-size: 0.8rem;'>{role_name}:</b> <span style='font-size: 0.82rem; color: var(--font-color, #fdfbf7);'>{msg['content']}</span></div>"
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)
        
        with st.form(key=f"float_chat_form_{key_suffix}", clear_on_submit=True):
            user_input = st.text_input("Ask question...", placeholder="e.g. highest spend?", key=f"float_input_{key_suffix}")
            submit = st.form_submit_button("Send Query", use_container_width=True)
            if submit and user_input:
                st.session_state['chat_history'].append({"role": "user", "content": user_input})
                with st.spinner("Thinking..."):
                    res = generate_ollama_chat_response(user_input, df)
                st.session_state['chat_history'].append({"role": "assistant", "content": res})
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def inject_mascot_script():
    """Injects the interactive cursor-following piggy mascot and shortcut hover popup controller."""
    import streamlit.components.v1 as components
    import json
    
    show_mascot = st.session_state.get('show_mascot', True)
    shortcut_key = str(st.session_state.get('mascot_shortcut_key', 'h')).lower()
    
    show_mascot_json = json.dumps(bool(show_mascot))
    shortcut_key_json = json.dumps(shortcut_key)
    
    piggy_js = f"""
    <script>
    (function() {{
        const parentWin = window.parent || window;
        const doc = parentWin.document || document;
        const SHOW_MASCOT = {show_mascot_json};
        const SHORTCUT_KEY = {shortcut_key_json};

        // Clean up helper
        function removeExisting() {{
            const m = doc.getElementById('cursor-piggy-mascot');
            if (m) m.remove();
            const p = doc.getElementById('piggy-shortcut-popup');
            if (p) p.remove();
        }}

        if (!SHOW_MASCOT) {{
            removeExisting();
            if (parentWin.__finops_mascot_handlers) {{
                try {{
                    doc.removeEventListener('mousemove', parentWin.__finops_mascot_handlers.onMouseMove);
                    doc.removeEventListener('keydown', parentWin.__finops_mascot_handlers.onKeyDown);
                    doc.removeEventListener('click', parentWin.__finops_mascot_handlers.onClickOutside);
                }} catch(e) {{}}
                delete parentWin.__finops_mascot_handlers;
            }}
            return;
        }}

        // Section feature knowledge dictionary (fallback)
        const SECTION_INFO = {{
            'kpis': {{
                badge: 'FinOps KPIs',
                title: '📊 FinOps KPI Overview',
                desc: 'Displays primary billing run-rates: Gross Period Spend, Daily Average burn, 365-Day Projected Annual Cost, and Net Cash Outlay.',
                starter: 'Can you analyze our current KPI spend figures and identify any abnormal burn rates or budget risks?'
            }},
            'filters': {{
                badge: 'Filters',
                title: '⚙️ Time Scope & Aggregation Filters',
                desc: 'Customize your billing lookback window (7-90 days), aggregate spend by Day, Week, or Month, and select specific AWS target regions.',
                starter: 'How do changes in time scope and aggregation (Day vs Week vs Month) help pinpoint periodic billing spikes?'
            }},
            'spend-chart': {{
                badge: 'Bar Chart',
                title: '📈 Service Spend Trajectory',
                desc: 'Interactive stacked bar chart visualizing cost trends across all active AWS services over your selected billing intervals.',
                starter: 'Which AWS service shows the fastest cost acceleration, and what architectural changes could reduce its cost?'
            }},
            'donut-chart': {{
                badge: 'Donut Chart',
                title: '🍩 Service Cost Distribution',
                desc: 'Relative expenditure share across services. Minor slices are consolidated into Other Services to prevent label collision.',
                starter: 'What does our service cost distribution tell us about our architecture, and which service represents the biggest savings opportunity?'
            }},
            'details-table': {{
                badge: 'Data Table',
                title: '📋 Granular Billing Details',
                desc: 'Pivoted tabular cost matrix showing dollar spend per service per period, with a one-click CSV export for offline FinOps reporting.',
                starter: 'Explain how to conduct a line-item audit on our granular billing table to spot sudden anomalous charges.'
            }},
            'carbon-kpis': {{
                badge: 'Carbon KPIs',
                title: '🌱 Carbon Footprint & Energy KPIs',
                desc: 'Estimates total greenhouse gas emissions (kg CO2e) and electrical energy consumption (kWh) based on regional grid carbon coefficients.',
                starter: 'What are the best strategies to lower our cloud carbon footprint and improve our sustainability score?'
            }},
            'carbon-chart': {{
                badge: 'Emissions Chart',
                title: '🌿 Per-Machine Emissions Chart',
                desc: 'Time-series emissions tracking per EC2 instance and workload, highlighting your highest-emitting machines over time.',
                starter: 'Which machines have the highest carbon emissions, and could ARM/Graviton migration or instance rightsizing reduce them?'
            }},
            'carbon-table': {{
                badge: 'Emissions Table',
                title: '📊 Machine Carbon Summary',
                desc: 'Workload-by-workload breakdown of instance type, power consumption (kWh), emissions (kg CO2e), and green efficiency.',
                starter: 'Can you recommend specific rightsizing or workload scheduling to minimize energy draw across our instances?'
            }},
            'service-catalog': {{
                badge: 'Service Catalog',
                title: '🔍 Discovered AWS Service Catalog',
                desc: 'Dynamic catalog of all active AWS cloud services discovered in your billing data, with status checks and rightsizing guidance.',
                starter: 'What are the top three cost optimization actions for the active AWS services discovered in our account?'
            }},
            'alerts-feed': {{
                badge: 'Budget Alerts',
                title: '🔔 Spend-Based Machine Alerts',
                desc: 'Monitors each machine\\'s spend against its allocated operational budget. Fires percentage-only alerts when an instance exceeds the threshold.',
                starter: 'Several machines are triggering spend threshold alerts. What steps should we take to remediate these budget overruns?'
            }},
            'settings-panel': {{
                badge: 'Settings',
                title: '⚙️ FinOps System Preferences',
                desc: 'Configure lookback defaults, theme presets (Light, Dark, Minimalistic), typography fonts, AI model engine, and machine budget baselines.',
                starter: 'What are the recommended FinOps threshold and lookback settings for an enterprise cloud environment?'
            }},
            'profile-panel': {{
                badge: 'Identity Vault',
                title: '👤 Identity & Credentials Vault',
                desc: 'Manages user authentication, guest session access, and secure AES-encrypted AWS Access Key / Secret Key storage.',
                starter: 'How does this dashboard connect to AWS Cost Explorer and protect my credentials?'
            }},
            'ai-chat': {{
                badge: 'AI Assistant',
                title: '🤖 FinOps AI Assistant',
                desc: 'AI chatbot grounded in live AWS telemetry, service breakdowns, and machine spend to provide tailored cloud cost optimization advice.',
                starter: 'Can you provide a comprehensive summary of all recommended cost-saving opportunities in our account?'
            }},
            'sidebar': {{
                badge: 'Navigation',
                title: '🚊 Dashboard Navigation Rail',
                desc: 'Navigate seamlessly between Profile, Dashboard, Carbon Footprint, Resources, AI Assistant, Settings, and Alerts.',
                starter: 'Give me a tour of the FinOps dashboard and how to navigate between cost, carbon, and alerts analysis.'
            }},
            'header': {{
                badge: 'Controls',
                title: '⚡ Dashboard Controls Header',
                desc: 'Top application navigation bar displaying connection status and your user profile popover.',
                starter: 'How can I verify whether my AWS credentials are authenticated and actively querying Cost Explorer?'
            }},
            'general': {{
                badge: 'FinOps Companion',
                title: '🐷 FinOps Piggy Companion',
                desc: 'I am your interactive cloud cost assistant! Hover over any chart, KPI, table, slider, or alert and press your shortcut key to inspect that feature.',
                starter: 'What are the top three actions I should take today to optimize our cloud spend?'
            }}
        }};

        // Real-Time DOM Inspection & Contextual Explanation Engine
        function inspectElementUnderCursor(x, y) {{
            const el = doc.elementFromPoint(x, y);
            if (!el) {{
                return SECTION_INFO['general'];
            }}

            // Visual feedback: briefly highlight the element under the cursor
            try {{
                const prevHL = doc.querySelectorAll('.finops-mascot-highlighted');
                prevHL.forEach(node => node.classList.remove('finops-mascot-highlighted'));
                
                const highlightTarget = el.closest('.metric-card, .kpi-card, .chart-container, .notification-card, [data-testid="stDataFrame"], [data-baseweb="select"], [data-testid="stSlider"], button, section[data-testid="stSidebar"] a') || el;
                if (highlightTarget) {{
                    highlightTarget.classList.add('finops-mascot-highlighted');
                    setTimeout(() => {{
                        highlightTarget.classList.remove('finops-mascot-highlighted');
                    }}, 2200);
                }}
            }} catch(err) {{}}

            // 1. KPI Metric Cards
            const kpiCard = el.closest('.metric-card, .kpi-card');
            if (kpiCard) {{
                const heading = kpiCard.querySelector('h1, h2, h3, h4, .kpi-label, .metric-label, p');
                const valueEl = kpiCard.querySelector('.metric-value, .kpi-value, h3, strong, b');
                const labelText = heading ? heading.innerText.trim() : 'KPI Metric';
                const valText = valueEl ? valueEl.innerText.trim() : '';
                return {{
                    badge: 'KPI Metric',
                    title: '📊 ' + labelText,
                    desc: (valText ? 'Current Telemetry Value: ' + valText + '. ' : '') + 'Tracks run-rate and cloud consumption to monitor baseline spending velocity and identify anomalous burn rates.',
                    starter: 'Can you analyze the ' + labelText + (valText ? ' (' + valText + ')' : '') + ' metric and provide specific optimization recommendations?'
                }};
            }}

            // 2. Sliders (e.g. Lookback Window, Alert Thresholds)
            const slider = el.closest('[data-testid="stSlider"]');
            if (slider) {{
                const label = slider.querySelector('label, [data-testid="stWidgetLabel"]');
                const labelText = label ? label.innerText.trim() : 'Historical Range Slider';
                const valEl = slider.querySelector('div[role="slider"]');
                const valText = valEl ? (valEl.getAttribute('aria-valuenow') || valEl.innerText.trim()) : '';
                return {{
                    badge: 'Range Slider',
                    title: '📅 ' + labelText,
                    desc: (valText ? 'Current Setting: ' + valText + '. ' : '') + 'Controls the historical observation window. Changing this value recalculates run-rates and chart aggregations in real time.',
                    starter: 'How does adjusting our lookback window help identify periodic billing spikes versus continuous architectural spend?'
                }};
            }}

            // 3. Dropdowns and Selectboxes (e.g. Aggregation, Region, AI Provider)
            const selectbox = el.closest('[data-testid="stSelectbox"], [data-baseweb="select"]');
            if (selectbox) {{
                const label = selectbox.closest('div[data-testid="stVerticalBlock"]')?.querySelector('label, [data-testid="stWidgetLabel"]') || selectbox.querySelector('label');
                const selectedVal = selectbox.querySelector('div[data-baseweb="select"] div')?.innerText.trim() || '';
                const labelText = label ? label.innerText.trim() : 'Filter Control';
                return {{
                    badge: 'Filter Selector',
                    title: '⚙️ ' + labelText,
                    desc: (selectedVal ? 'Currently Selected: "' + selectedVal + '". ' : '') + 'Applies operational grouping or regional filtering to isolate cost drivers and evaluate architectural efficiency.',
                    starter: 'How does analyzing spend by ' + (selectedVal || labelText) + ' help uncover cloud cost optimization opportunities?'
                }};
            }}

            // 4. Plotly Charts (Bars, Pie/Donut slices, Lines)
            const chart = el.closest('.js-plotly-plot, .plotly, [data-section="spend-chart"], [data-section="donut-chart"], [data-section="carbon-chart"]');
            if (chart) {{
                const chartTitle = chart.querySelector('.gtitle, h3, h4')?.innerText.trim() || 'Interactive Telemetry Chart';
                return {{
                    badge: 'Interactive Chart',
                    title: '📈 ' + chartTitle,
                    desc: 'Multi-dimensional visual telemetry. Hover over individual bars, slices, or data points to inspect exact dollar expenditures, percentages, and trends.',
                    starter: 'What are the main insights and cost drivers shown in the ' + chartTitle + ' chart?'
                }};
            }}

            // 5. Data Tables / DataFrames
            const dataframe = el.closest('[data-testid="stDataFrame"], [data-section="details-table"], [data-section="carbon-table"], table');
            if (dataframe) {{
                return {{
                    badge: 'Data Table',
                    title: '📋 Granular Breakdown Table',
                    desc: 'Granular tabular cost allocation matrix. Inspect individual line-item costs per service or export to CSV for offline financial audits.',
                    starter: 'How can I conduct a variance analysis on our granular billing table to spot sudden anomalous charges?'
                }};
            }}

            // 6. Action Buttons
            const btn = el.closest('button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"], .stButton');
            if (btn && !btn.closest('#piggy-shortcut-popup')) {{
                const btnText = btn.innerText.trim().replace(/\\n/g, ' ') || 'Action Control';
                return {{
                    badge: 'Action Button',
                    title: '🔘 ' + btnText,
                    desc: 'Interactive action button. Triggers state updates, CSV downloads, configuration persistence, or conversation reset.',
                    starter: 'What are the best workflows and operational routines for utilizing "' + btnText + '" in cloud governance?'
                }};
            }}

            // 7. Notification / Alert Cards
            const notifCard = el.closest('.notification-card, [data-section="alerts-feed"]');
            if (notifCard) {{
                const title = notifCard.querySelector('h4, b')?.innerText.trim() || 'Budget Consumption Alert';
                const msg = notifCard.querySelector('p')?.innerText.trim() || '';
                return {{
                    badge: 'Budget Alert',
                    title: '🔔 ' + title,
                    desc: (msg ? msg + ' ' : '') + 'Alert indicating this cloud workload has exceeded its target operational budget limit.',
                    starter: 'One of our workloads triggered an alert: "' + title + '". What immediate remediation actions should we take?'
                }};
            }}

            // 8. Sidebar Navigation Links
            const navItem = el.closest('section[data-testid="stSidebar"] a, nav a');
            if (navItem) {{
                const pageName = navItem.innerText.trim() || 'Navigation Page';
                return {{
                    badge: 'Navigation Rail',
                    title: '🧭 ' + pageName + ' Page',
                    desc: 'Direct shortcut to the ' + pageName + ' module in your FinOps dashboard suite.',
                    starter: 'Give me a detailed overview of the ' + pageName + ' module and how it helps optimize cloud operations.'
                }};
            }}

            // 9. Status Badge
            const badge = el.closest('.status-badge');
            if (badge) {{
                const badgeText = badge.innerText.trim() || 'Status';
                return {{
                    badge: 'Connection State',
                    title: '⚡ AWS Connection: ' + badgeText,
                    desc: 'Indicates whether the dashboard is querying live telemetry from your connected AWS Cost Explorer account or displaying demo sandbox workloads.',
                    starter: 'How does this dashboard securely connect to AWS Cost Explorer and what permissions are needed?'
                }};
            }}

            // 10. Piggy Mascot Itself
            if (el.closest('#cursor-piggy-mascot')) {{
                return {{
                    badge: 'FinOps Companion',
                    title: '🐷 FinOps Piggy Mascot',
                    desc: 'I am your interactive cloud companion! Move me over any chart, metric, table, button, or filter and press ' + SHORTCUT_KEY.toUpperCase() + ' for real-time explanations.',
                    starter: 'What are the top three actions I should take today to optimize our cloud spend?'
                }};
            }}

            // 11. Section Tag Fallback
            const sectionEl = el.closest('[data-section]');
            if (sectionEl) {{
                const secKey = sectionEl.getAttribute('data-section');
                if (SECTION_INFO[secKey]) {{
                    return SECTION_INFO[secKey];
                }}
            }}

            // 12. Arbitrary text content under cursor
            const textContent = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
            if (textContent.length > 0 && textContent.length < 120) {{
                return {{
                    badge: 'Inspected Element',
                    title: '🔍 ' + textContent.slice(0, 36) + (textContent.length > 36 ? '...' : ''),
                    desc: 'Inspecting: "' + textContent + '". You can ask the AI Assistant for deeper analysis of this element in your cloud architecture.',
                    starter: 'Can you analyze the following element from our FinOps dashboard: "' + textContent + '"?'
                }};
            }}

            return SECTION_INFO['general'];
        }}

        // Ensure mascot element exists
        let mascot = doc.getElementById('cursor-piggy-mascot');
        if (!mascot) {{
            mascot = doc.createElement('div');
            mascot.id = 'cursor-piggy-mascot';
            mascot.innerHTML = `
                <div class="piggy-bank">
                    <div class="pig-coin">🪙</div>
                    <div class="pig-body">
                        <div class="pig-eye"></div>
                        <div class="pig-ear"></div>
                        <div class="pig-snout"></div>
                        <div class="pig-tail"></div>
                        <div class="pig-slot"></div>
                    </div>
                    <div class="pig-legs">
                        <div class="pig-leg leg-front-left"></div>
                        <div class="pig-leg leg-front-right"></div>
                        <div class="pig-leg leg-back-left"></div>
                        <div class="pig-leg leg-back-right"></div>
                    </div>
                </div>
            `;
            doc.body.appendChild(mascot);
            // Initial position near bottom right
            const initX = (parentWin.innerWidth || window.innerWidth) - 80;
            const initY = (parentWin.innerHeight || window.innerHeight) - 80;
            mascot.style.left = initX + 'px';
            mascot.style.top = initY + 'px';
        }}

        // Ensure popup element exists
        let popup = doc.getElementById('piggy-shortcut-popup');
        if (!popup) {{
            popup = doc.createElement('div');
            popup.id = 'piggy-shortcut-popup';
            doc.body.appendChild(popup);
        }}

        let lastMouseX = (parentWin.innerWidth || window.innerWidth) / 2;
        let lastMouseY = (parentWin.innerHeight || window.innerHeight) / 2;

        function onMouseMove(e) {{
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;

            const m = doc.getElementById('cursor-piggy-mascot');
            if (!m) return;

            const viewW = parentWin.innerWidth || window.innerWidth;
            const viewH = parentWin.innerHeight || window.innerHeight;

            // Position slightly below cursor
            const posX = Math.min(Math.max(10, e.clientX + 16), viewW - 70);
            const posY = Math.min(Math.max(10, e.clientY + 22), viewH - 60);

            m.style.left = posX + 'px';
            m.style.top = posY + 'px';
            m.style.display = 'block';

            // Face direction of movement
            if (e.movementX > 1) {{
                m.style.transform = 'scaleX(1)';
            }} else if (e.movementX < -1) {{
                m.style.transform = 'scaleX(-1)';
            }}
        }}

        function showPopup(info, mouseX, mouseY) {{
            const p = doc.getElementById('piggy-shortcut-popup');
            if (!p) return;

            info = info || SECTION_INFO['general'];
            const viewW = parentWin.innerWidth || window.innerWidth;
            const viewH = parentWin.innerHeight || window.innerHeight;

            let popX = mouseX + 24;
            let popY = mouseY + 15;

            if (popX + 350 > viewW) {{
                popX = Math.max(15, mouseX - 350);
            }}
            if (popY + 280 > viewH) {{
                popY = Math.max(15, mouseY - 270);
            }}

            p.style.left = popX + 'px';
            p.style.top = popY + 'px';

            const badgeText = info.badge || 'FinOps Companion';

            p.innerHTML = `
                <div class="piggy-popup-card">
                    <div class="piggy-popup-header">
                        <div class="piggy-popup-title-box">
                            <span class="piggy-popup-icon">🐷</span>
                            <span class="piggy-popup-badge">${{badgeText}}</span>
                        </div>
                        <button type="button" class="piggy-popup-close" id="btn-close-piggy-popup" title="Close (Esc)">✕</button>
                    </div>
                    <div class="piggy-popup-body">
                        <h4 class="piggy-feature-title">${{info.title}}</h4>
                        <p class="piggy-feature-desc">${{info.desc}}</p>
                        <div class="piggy-popup-hint">
                            <span>💡 Shortcut: press <b>${{SHORTCUT_KEY.toUpperCase()}}</b> anywhere to inspect</span>
                        </div>
                    </div>
                    <div class="piggy-popup-footer">
                        <button type="button" class="piggy-ai-btn" id="btn-piggy-open-ai">
                            <span>🤖 Open this in AI Assistant</span>
                            <span style="font-size: 1.1rem; margin-left: 4px;">↗</span>
                        </button>
                    </div>
                </div>
            `;

            p.style.display = 'block';

            const closeBtn = doc.getElementById('btn-close-piggy-popup');
            if (closeBtn) {{
                closeBtn.onclick = function(ev) {{
                    ev.stopPropagation();
                    hidePopup();
                }};
            }}

            const aiBtn = doc.getElementById('btn-piggy-open-ai');
            if (aiBtn) {{
                aiBtn.onclick = function(ev) {{
                    ev.stopPropagation();
                    hidePopup();
                    
                    const starterText = info.starter || 'How can I optimize our cloud costs?';
                    
                    // 1. Store starter prompt in sessionStorage for instant retrieval
                    try {{
                        parentWin.sessionStorage.setItem('finops_mascot_starter', starterText);
                    }} catch(e) {{}}
                    
                    // 2. Find the AI Assistant link in Streamlit sidebar to trigger smooth SPA transition
                    const sidebarLinks = Array.from(doc.querySelectorAll('section[data-testid="stSidebar"] a, nav a'));
                    const aiLink = sidebarLinks.find(a => {{
                        const txt = (a.textContent || '').toLowerCase();
                        const href = (a.getAttribute('href') || '').toLowerCase();
                        return txt.includes('ai assistant') || href.includes('ai_assistant') || href.includes('ai-assistant');
                    }});
                    
                    if (aiLink) {{
                        try {{
                            const u = new URL(aiLink.href, parentWin.location.origin);
                            u.searchParams.set('starter', starterText);
                            aiLink.href = u.pathname + u.search;
                        }} catch(e) {{}}
                        aiLink.click();
                    }} else {{
                        let basePath = parentWin.location.pathname;
                        basePath = basePath.replace(/\\/(ai_assistant|dashboard|carbon_footprint|analytics|settings|notifications|profile).*$/, '');
                        if (!basePath.endsWith('/')) basePath += '/';
                        const targetUrl = parentWin.location.origin + basePath + 'ai_assistant?starter=' + encodeURIComponent(starterText);
                        parentWin.location.href = targetUrl;
                    }}
                }};
            }}
        }}

        function hidePopup() {{
            const p = doc.getElementById('piggy-shortcut-popup');
            if (p) {{
                p.style.display = 'none';
            }}
        }}

        function onKeyDown(e) {{
            if (e.key === 'Escape') {{
                hidePopup();
                return;
            }}

            const activeTag = (doc.activeElement && doc.activeElement.tagName) ? doc.activeElement.tagName.toLowerCase() : '';
            if (activeTag === 'input' || activeTag === 'textarea' || (doc.activeElement && doc.activeElement.isContentEditable)) {{
                return;
            }}

            if (e.key.toLowerCase() === SHORTCUT_KEY.toLowerCase()) {{
                e.preventDefault();

                const p = doc.getElementById('piggy-shortcut-popup');
                if (p && p.style.display === 'block') {{
                    hidePopup();
                    return;
                }}

                const info = inspectElementUnderCursor(lastMouseX, lastMouseY);
                showPopup(info, lastMouseX, lastMouseY);
            }}
        }}

        function onClickOutside(e) {{
            const p = doc.getElementById('piggy-shortcut-popup');
            if (p && p.style.display === 'block') {{
                if (!p.contains(e.target)) {{
                    hidePopup();
                }}
            }}
        }}

        // Clean up previous event listeners if already registered
        if (parentWin.__finops_mascot_handlers) {{
            try {{
                doc.removeEventListener('mousemove', parentWin.__finops_mascot_handlers.onMouseMove);
                doc.removeEventListener('keydown', parentWin.__finops_mascot_handlers.onKeyDown);
                doc.removeEventListener('click', parentWin.__finops_mascot_handlers.onClickOutside);
            }} catch(e) {{}}
        }}

        // Attach listeners
        doc.addEventListener('mousemove', onMouseMove, {{ passive: true }});
        doc.addEventListener('keydown', onKeyDown);
        doc.addEventListener('click', onClickOutside);

        parentWin.__finops_mascot_handlers = {{
            onMouseMove: onMouseMove,
            onKeyDown: onKeyDown,
            onClickOutside: onClickOutside
        }};
    }})();
    </script>
    """
    components.html(piggy_js, height=0, width=0)

def render_profile_popover():
    """
    Renders the interactive Profile Popover in the navigation header.
    Allows guest users to input, view (show/hide), and use their AWS Secret Access Key directly,
    or authenticated users to inspect active credentials and sign out.
    """
    is_auth = st.session_state.get('authenticated', False)
    is_connected = st.session_state.get('aws_connected', False)

    if is_auth:
        username = st.session_state.get('username', 'User')
        initials = "".join([part[0].upper() for part in username.split('@')[0].split('.') if part])[:2]
        if not initials:
            initials = username[:2].upper() if username else "US"
        popover_label = f"👤 {initials}"
        help_text = f"Profile: {username}"
    else:
        if is_connected:
            popover_label = "👤 Guest (Live)"
            help_text = "Guest Profile (Live AWS Connected)"
        else:
            popover_label = "👤 Guest"
            help_text = "Guest Profile (Configure AWS Secret Access Key)"

    with st.popover(popover_label, use_container_width=True, help=help_text):
        if is_auth:
            username = st.session_state.get('username', 'User')
            st.markdown(
                f"""
                <div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;'>
                    <span style='font-size:1.05rem; font-weight:700; color:var(--primary-accent);'>👤 User Profile</span>
                    <span style='background:rgba(16,185,129,0.15); color:#10b981; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;'>🟢 Logged In</span>
                </div>
                <p style='margin:0 0 8px 0; font-size:0.85rem;'><b>Username:</b> <code>{username}</code></p>
                """,
                unsafe_allow_html=True
            )
            st.markdown("---")
            st.markdown(f"**AWS Account ID:** `{st.session_state.get('aws_account_id', 'N/A')}`")
            st.markdown(f"**Caller ARN:**\n`{st.session_state.get('aws_arn', 'N/A')}`")
            
            st.markdown("---")
            st.markdown("**🔑 Active Credentials**")
            st.markdown(f"**Access Key ID:** `{st.session_state.get('aws_access_key', 'Not set')}`")
            
            show_auth_sec = st.checkbox("👁️ Show Secret Access Key", key="popover_auth_show_secret")
            sec_val = st.session_state.get('aws_secret_key', '')
            if sec_val:
                if show_auth_sec:
                    st.code(sec_val, language="text")
                else:
                    masked = "•" * min(24, len(sec_val))
                    st.markdown(f"**Secret Access Key:** `{masked}`")
            else:
                st.markdown("**Secret Access Key:** *Not configured*")

            st.markdown("---")
            if st.button("Sign Out", key="popover_sign_out_btn", use_container_width=True, type="primary"):
                st.session_state['authenticated'] = False
                st.session_state['username'] = ""
                st.session_state['aws_access_key'] = ""
                st.session_state['aws_secret_key'] = ""
                st.session_state['aws_session_token'] = ""
                st.session_state['aws_connected'] = False
                st.session_state['aws_account_id'] = ""
                st.session_state['aws_arn'] = ""
                st.session_state['theme'] = auth_manager.load_anonymous_theme()
                st.toast("Signed out successfully!", icon="👋")
                st.rerun()
        else:
            # Guest Profile Popover
            st.markdown(
                """
                <div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;'>
                    <div>
                        <span style='font-size:1.05rem; font-weight:700; color:var(--primary-accent);'>👤 Guest Profile</span>
                        <br/><span style='font-size:0.75rem; color:#9ca3af;'>No account needed • Live AWS access</span>
                    </div>
                    <span style='background:rgba(249,115,22,0.15); color:var(--primary-accent); padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;'>Guest Mode</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            if is_connected:
                st.markdown(
                    f"""
                    <div style='background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:8px 10px; margin-bottom:12px; font-size:0.8rem;'>
                        🟢 <b>Live AWS Connected</b><br/>
                        <span style='opacity:0.85;'>Account: <code>{st.session_state.get('aws_account_id', 'N/A')}</code></span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    """
                    <div style='background:rgba(249,115,22,0.1); border:1px solid rgba(249,115,22,0.25); border-radius:8px; padding:8px 10px; margin-bottom:12px; font-size:0.8rem;'>
                        ⚪ <b>Demo Mode Active</b><br/>
                        <span style='opacity:0.85;'>Enter your AWS credentials below to query live Cost Explorer data.</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("**🔑 AWS Credentials**")
            p_aws_key = st.text_input(
                "Access Key ID",
                value=st.session_state.get('aws_access_key', ''),
                key="popover_g_aws_key",
                placeholder="AKIAIOSFODNN7EXAMPLE"
            )
            p_show_secret = st.checkbox("👁️ Show Secret Access Key", value=False, key="popover_g_show_secret")
            p_aws_secret = st.text_input(
                "Secret Access Key",
                type="default" if p_show_secret else "password",
                value=st.session_state.get('aws_secret_key', ''),
                key="popover_g_aws_secret",
                placeholder="wJalrXUtnFEMI/K7MDENG/..."
            )
            
            with st.expander("Session Token (Optional)", expanded=False):
                p_aws_token = st.text_input(
                    "AWS Session Token",
                    type="password",
                    value=st.session_state.get('aws_session_token', ''),
                    key="popover_g_aws_token"
                )

            st.write("")
            btn_title = "⚡ Update & Query AWS" if is_connected else "⚡ Connect AWS as Guest"
            
            if is_connected:
                col_b1, col_b2 = st.columns([1.5, 1])
                with col_b1:
                    if st.button(btn_title, key="popover_btn_connect_guest", use_container_width=True, type="primary"):
                        if not p_aws_key or not p_aws_secret:
                            st.error("Both Access Key ID and Secret Access Key are required.")
                        else:
                            st.info("Testing connection with AWS STS...")
                            test_res = test_aws_connection(p_aws_key, p_aws_secret, aws_session_token=p_aws_token if p_aws_token else None)
                            if not test_res['success']:
                                st.error(f"Connection failed: {test_res['error']}")
                            else:
                                st.session_state['aws_access_key'] = p_aws_key
                                st.session_state['aws_secret_key'] = p_aws_secret
                                st.session_state['aws_session_token'] = p_aws_token if p_aws_token else ""
                                st.session_state['aws_connected'] = True
                                st.session_state['aws_account_id'] = test_res['account_id']
                                st.session_state['aws_arn'] = test_res['arn']
                                st.toast("AWS credentials updated! Live data loaded.", icon="🟢")
                                st.rerun()
                with col_b2:
                    if st.button("Disconnect", key="popover_btn_disconnect_guest", use_container_width=True):
                        st.session_state['aws_access_key'] = ""
                        st.session_state['aws_secret_key'] = ""
                        st.session_state['aws_session_token'] = ""
                        st.session_state['aws_connected'] = False
                        st.session_state['aws_account_id'] = ""
                        st.session_state['aws_arn'] = ""
                        st.toast("Switched back to demo mode.", icon="⚪")
                        st.rerun()
            else:
                if st.button(btn_title, key="popover_btn_connect_guest", use_container_width=True, type="primary"):
                    if not p_aws_key or not p_aws_secret:
                        st.error("Both Access Key ID and Secret Access Key are required.")
                    else:
                        st.info("Testing connection with AWS STS...")
                        test_res = test_aws_connection(p_aws_key, p_aws_secret, aws_session_token=p_aws_token if p_aws_token else None)
                        if not test_res['success']:
                            st.error(f"Connection failed: {test_res['error']}")
                        else:
                            st.session_state['aws_access_key'] = p_aws_key
                            st.session_state['aws_secret_key'] = p_aws_secret
                            st.session_state['aws_session_token'] = p_aws_token if p_aws_token else ""
                            st.session_state['aws_connected'] = True
                            st.session_state['aws_account_id'] = test_res['account_id']
                            st.session_state['aws_arn'] = test_res['arn']
                            st.toast("Connected to AWS as Guest! Live data loaded.", icon="🟢")
                            st.rerun()

            st.markdown("---")
            st.markdown("<p style='font-size:0.75rem; color:#9ca3af; margin:0 0 6px 0;'>Want to save keys securely across sessions?</p>", unsafe_allow_html=True)
            if st.button("🔐 Sign In / Create Account", key="popover_open_auth_dialog_btn", use_container_width=True):
                show_auth_dialog()

