# ⚡ AWS FinOps Cost Analyzer & AI Copilot

An enterprise-grade, interactive Cloud FinOps dashboard built with Streamlit, Plotly, boto3, and Python. It delivers real-time AWS cost analytics, multi-dimensional spend attribution, sustainability and carbon footprint modeling, autonomous multi-provider LLM cost optimization recommendations, machine-level workload budget tracking, and an interactive keyboard-driven feature companion.

---

## 🌟 Key Highlights & Features

- **📊 Multi-Dimensional Spend Intelligence**:
  - Interactive spend timelines by Day, Week, or Month with instant aggregation.
  - Service cost attribution with dynamic low-spend threshold slice-folding to eliminate chart clutter.
  - Net out-of-pocket cash outlay vs. gross unblended spend tracking.
  - Daily run-rate analysis, annualized burn projections, and raw exportable CSV records.
- **🤖 Autonomous FinOps AI Copilot**:
  - Multi-provider LLM support: **Local Ollama**, **Google Gemini**, **OpenAI**, **Anthropic Claude**, and **Custom OpenAI-compatible endpoints** (vLLM, LM Studio, Groq, OpenRouter).
  - Grounded system prompt automatically injected with live AWS spend totals, primary cost drivers, service breakdowns, and workload instances.
  - High-resilience Gemini pool: automatically fails over across high-speed Flash models (`gemini-3.6-flash`, `gemini-3.5-flash-lite`, etc.) and falls back to Local Ollama if cloud APIs experience 503/429 overload.
  - Ollama auto-recovery: automatically detects and spawns local `ollama serve` in the background if not already running.
- **🐷 Interactive Piggy Mascot & Cursor Companion**:
  - Floating cursor-following assistant that smoothly accompanies your navigation.
  - Contextual keyboard shortcut (default <kbd>H</kbd>, customizable to <kbd>E</kbd>, <kbd>M</kbd>, <kbd>P</kbd>, or <kbd>?</kbd>) to inspect instant feature explanations on any hovered chart or metric.
  - One-click **"Open in AI Assistant"** button that pre-populates the AI prompt with the exact hovered metric context.
- **🌱 Sustainability & Carbon Footprint Modeling**:
  - Estimated cloud energy consumption (kWh) and Scope 2 CO₂e greenhouse gas emissions.
  - Regional electrical grid carbon intensity factors (e.g., `us-east-1`: 0.37 kg/kWh, `us-west-2`: 0.08 kg/kWh, `eu-west-1`: 0.25 kg/kWh, `ap-southeast-1`: 0.41 kg/kWh).
  - Tree-year carbon offset equivalencies and service-by-service energy attribution.
- **🔔 Machine Spend Alerts & Cloud Workload Budgets**:
  - Dynamic budget tracking for core cloud workloads (EC2, RDS, S3, DynamoDB, Lambda, NAT Gateway, CloudFront).
  - Configurable budget consumption threshold slider (50% – 100%).
  - In Live AWS mode, alerts evaluate actual AWS billing records in real time; in Demo mode, evaluates deterministic workload simulations.
  - Percentage-of-budget consumption indicators with zero raw dollar figure leakage for operational privacy.
- **🎨 Modern Design System & Dual Aesthetics**:
  - **Dark Glassmorphic Themes**: Sleek frosted glass cards, fluid micro-transitions, customizable color pickers for accent, sidebar, and canvas gradients.
  - **Minimalist Paper Preset**: Handmade tactile washi paper aesthetic with terracotta cinnabar accents and sumi charcoal typography.
  - Global typography selector: Plus Jakarta Sans, Outfit, or JetBrains Mono via CSS `@import`.
  - Animated KPI odometer cards with smooth counting transitions.
- **🔐 Enterprise Security & Credential Vault**:
  - PBKDF2 key derivation (100,000 iterations SHA-256) for master password hashing.
  - Fernet AES-256 symmetric encryption for AWS credentials and provider API keys stored in local `.user_vault.json`.
  - Zero cloud leakage: credentials never leave your local environment.
- **🛡️ Cost-Guard Caching Architecture**:
  - Configurable TTL caching (`@st.cache_data`) for AWS Cost Explorer API requests to prevent redundant **$0.01 per query** API charges.
  - Deterministic offline mock mode for zero-cost demonstrations and testing without live AWS credentials.

---

## 🏛️ Architecture Overview

```
                                ┌──────────────────────────────────────────────┐
                                │          Streamlit Multipage Router          │
                                │        (app.py via st.navigation)            │
                                └──────────────┬───────────────────────────────┘
                                               │
             ┌─────────────────────────────────┼─────────────────────────────────┐
             ▼                                 ▼                                 ▼
   ┌────────────────────┐            ┌────────────────────┐            ┌────────────────────┐
   │ Presentation Views │            │  Cost Data Engine  │            │  FinOps AI Copilot │
   │ (pages/*.py)       │            │  (cost_engine.py)  │            │  (ai_helper.py)    │
   ├────────────────────┤            ├────────────────────┤            ├────────────────────┤
   │ • Dashboard        │            │ • boto3 CE Client  │            │ • Local Ollama     │
   │ • Profile          │            │ • STS Identity     │            │ • Google Gemini    │
   │ • Carbon Footprint │            │ • st.cache_data    │            │ • OpenAI / Claude  │
   │ • Resources        │            │ • Mock Data Gen    │            │ • Custom v1 API    │
   │ • AI Assistant     │            └─────────┬──────────┘            └─────────┬──────────┘
   │ • Settings         │                      │                                 │
   │ • Alerts           │                      ▼                                 ▼
   └────────────────────┘            ┌────────────────────┐            ┌────────────────────┐
             │                       │ AWS Cost Explorer  │            │ LLM Inference /    │
             ▼                       │ Cloud API ($0.01)  │            │ Local GPU Server   │
   ┌────────────────────┐            └────────────────────┘            └────────────────────┘
   │ UI & Design System │
   │ (ui_components.py  │
   │  style.css)        │
   │ • Glassmorphism    │
   │ • Mascot Script    │
   │ • Animated KPIs    │
   │ • Vault Encryption │
   └────────────────────┘
```

---

## 📁 Project Structure

```
Cost_analysis/
├── app.py                     # Main application entrypoint, global session state & st.navigation router
├── run.py                     # Cross-platform port checker (8501) & resilient process launcher
├── requirements.txt           # Project dependencies (streamlit, boto3, plotly, cryptography, etc.)
├── cost_engine.py             # AWS Cost Explorer API integration, STS verification, caching & mock data
├── page_views.py              # Visual charts, Plotly themes, analytical layouts & carbon emissions models
├── ui_components.py           # Glassmorphism cards, animated KPI odometers, CSS injector & mascot runtime
├── auth_manager.py            # Local credentials encryption (Fernet/PBKDF2), vault & settings persistence
├── ai_helper.py               # Multi-provider FinOps AI engine (Ollama auto-serve, Gemini failover pool, etc.)
├── style.css                  # Unified design system tokens, responsive glassmorphism & paper aesthetic
├── pages/                     # Streamlit multipage application views (st.Page)
│   ├── profile.py             # User authentication, STS caller identity & encrypted AWS credentials
│   ├── dashboard.py           # Core FinOps dashboard: animated KPIs, spend timelines & service distribution
│   ├── carbon_footprint.py    # Scope 2 CO₂e emissions, regional grid carbon intensity & tree offsets
│   ├── analytics.py           # AWS Cloud resources & services spend breakdown with tabular search
│   ├── ai_assistant.py        # Dedicated FinOps AI Copilot conversational workspace
│   ├── settings.py            # 5-tab control panel (Display, Themes, AI Engine, Alerts, Mascot)
│   └── notifications.py       # Active workload spend alerts & budget consumption monitoring
└── README.md                  # Comprehensive project documentation
```

---

## 📋 Prerequisites

1. **Python 3.10+** installed on your system.
2. **AWS Account & Cost Explorer**:
   - AWS Cost Explorer must be enabled in your AWS Billing Console (*Note: AWS requires up to 24 hours after initial activation to compile historical data*).
3. **AWS IAM Credentials** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optional `AWS_SESSION_TOKEN`) with the following read-only IAM permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ce:GetCostAndUsage",
           "ce:GetDimensionValues",
           "sts:GetCallerIdentity"
         ],
         "Resource": "*"
       }
     ]
   }
   ```
4. *(Optional for AI Copilot)*:
   - **Local Ollama** installed (`ollama pull llama3.1:8b`) for offline, free inference.
   - OR an API key for **Google Gemini**, **OpenAI**, or **Anthropic Claude**.
   - OR a **Custom Endpoint** URL compatible with OpenAI's v1 chat completions.

---

## 🚀 Quick Start & Installation

### 1. Clone the Repository & Navigate
```bash
git clone <your-repository-url>
cd Cost_analysis
```

### 2. Create and Activate Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt / PowerShell)
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
You can optionally set credentials via environment variables:
```bash
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-east-1"
```
*(Alternatively, you can securely input your credentials in the app via the **Profile** page, which encrypts them locally using AES-256).*

---

## 💻 How to Run

### Method 1: Resilient Cross-Platform Launcher (Recommended)
Use `run.py`, which inspects port 8501 for zombie or dangling Streamlit sessions, cleanly terminates them across macOS, Linux, or Windows, and launches the application:
```bash
python run.py
```

### Method 2: Direct Streamlit Command
```bash
streamlit run app.py
```

Open your browser and navigate to **`http://localhost:8501`**.

---

## 🧭 Application Walkthrough & Multipage Guide

The dashboard uses Streamlit's official `st.navigation` architecture with 7 distinct pages:

### 1. 📊 Dashboard (`pages/dashboard.py`)
- **KPI Metric Strip**: Real-time animated counters displaying **Gross Spend**, **Daily Average Run-Rate**, **Projected Annual Burn**, and **Net Out-of-Pocket Cash Outlay**.
- **Interactive Controls**: Timeframe lookback selector (7, 14, 30, 60, 90 days), aggregation frequency (Day, Week, Month), and AWS Region selector.
- **Spend Over Time Breakdown**: Plotly stacked bar chart showing exact spend distribution by service with outside legends and collision-free rotated date labels.
- **Service Distribution Chart**: Donut chart with dynamic low-spend slice-folding (<3% spend aggregated into "Other") to maintain visual clarity.
- **Raw Billing Data**: Full tabular view with instant CSV download capability.

### 2. 👤 Profile (`pages/profile.py`)
- **Authentication**: Switch between Guest Mode and Authenticated User accounts.
- **Encrypted Credential Storage**: Add, validate, or disconnect AWS Access Keys, Secret Keys, and Session Tokens.
- **STS Validation**: Live identity check displaying AWS Account ID and IAM Caller ARN.

### 3. 🌱 Carbon Footprint (`pages/carbon_footprint.py`)
- **Scope 2 Greenhouse Emissions**: Models cloud electricity usage (kWh) and CO₂e emissions based on AWS service spend.
- **Grid Carbon Intensity**: Incorporates regional grid factors (us-east-1, us-west-2, eu-west-1, ap-southeast-1).
- **Sustainability Metrics**: Calculates equivalent tree-years required for carbon sequestration and breaks down emissions by service.

### 4. 📦 Resources & Services (`pages/analytics.py`)
- Deep analytical breakdown of active cloud resources and services.
- Searchable and filterable tables highlighting top spending cloud components.
- Relative cost contribution metrics to guide targeted engineering optimizations.

### 5. 🤖 AI Assistant (`pages/ai_assistant.py`)
- Full-page interactive chat interface powered by your chosen LLM provider.
- Context injection: system prompt receives live data on total spend, daily burn, active services, top cost driver, and workload instances.
- Quick prompt buttons for common FinOps queries (e.g., right-sizing idle instances, Graviton migrations, S3 lifecycle policies).
- Clear conversation history button with session reset.

### 6. ⚙️ Settings (`pages/settings.py`)
Organized into 5 specialized preference tabs:
1. **General & Display**: Lookback window defaults, currency symbol prefix (`$`, `€`, `£`, `¥`, `₹`), and Cost Explorer cache TTL.
2. **Theme & Colors**: Theme preset selector (Modern Amber vs. Minimalist Paper), live color pickers for custom accents/backgrounds, and global font selector (Plus Jakarta Sans, Outfit, JetBrains Mono).
3. **AI Assistant Engine**: Provider selector (Local Ollama, Google Gemini, OpenAI, Claude, Custom Endpoint), model ID fields, and API key management.
4. **Alert Thresholds**: Spend threshold slider (50% – 100%) and configurable workload budget baselines for active AWS services or demo workloads.
5. **Mascot Preferences**: Toggle Piggy Mascot on/off and select the keyboard shortcut key (<kbd>H</kbd>, <kbd>E</kbd>, <kbd>M</kbd>, <kbd>P</kbd>, <kbd>?</kbd>).

### 7. 🔔 Alerts & Machine Budgets (`pages/notifications.py`)
- Monitors active cloud workloads against configured budget baselines.
- Displays percentage-of-budget consumption alerts (e.g., `85% of Budget`) with actionable remediation tips.
- Evaluates real AWS billing records when connected to AWS, or simulated workloads in demo mode.

---

## 🐷 Interactive Piggy Mascot Feature

The dashboard includes a built-in interactive cursor companion:
- **Hover & Inspect**: Hover your mouse over any metric card, chart, or data table.
- **Keyboard Shortcut**: Press <kbd>H</kbd> (or your custom configured shortcut from Settings).
- **Instant Insights**: A glassmorphic popup explains the purpose of the metric, its financial significance, and potential FinOps implications.
- **AI Integration**: Click **"Open in AI Assistant"** inside the popup to jump directly to the AI Assistant page with contextual prompt pre-loaded!

---

## 💰 AWS Cost Explorer Pricing & Caching Strategy

> [!IMPORTANT]
> **AWS Cost Awareness**: AWS charges **$0.01 per Cost Explorer API request** (`ce:GetCostAndUsage`). Frequent page refreshes or un-cached queries can incur minor charges on your AWS bill.

### Built-in Cost Protection:
- **In-Memory Caching (`@st.cache_data`)**: All data fetches in `cost_engine.py` are cached in memory. The default TTL is **1 hour** (configurable up to 24 hours in Settings).
- **Rerun Immunity**: Navigating between pages, typing in the AI Assistant chat, or changing theme colors **does not** trigger new AWS Cost Explorer network calls.
- **Zero-Cost Demo Mode**: If no AWS credentials are configured, the app seamlessly runs on a deterministic, realistic mock dataset generator (`generate_mock_data()`) with zero network overhead and zero AWS cost.

---

## 🔒 Security & Data Privacy

- **Local Storage Only**: All user credentials, API keys, and theme settings are saved locally in the project root (`.user_vault.json`, `.ai_settings.json`, `.anonymous_settings.json`).
- **Cryptographic Encryption**:
  - Master passwords are authenticated using **PBKDF2-HMAC-SHA256** with 100,000 iterations and unique cryptographic salts.
  - AWS Access Keys, Secret Keys, Session Tokens, and LLM API keys are encrypted at rest using **Fernet (AES-128-CBC with SHA256 HMAC)** derived from the master password.
- **No Third-Party Telemetry**: Your AWS billing data is never sent to external servers other than direct calls to AWS APIs and your explicitly configured AI provider.

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|:---|:---|:---|
| **Frontend Framework** | Streamlit (>= 1.35.0) | Multipage reactive web application (`st.navigation`, `st.Page`) |
| **Data Visualizations** | Plotly (>= 5.20.0) | Interactive charts with custom themes, folding & hovertemplates |
| **Cloud Integration** | boto3 (>= 1.34.0) | AWS Cost Explorer (`ce`) & AWS STS (`sts`) client APIs |
| **Data Processing** | pandas (>= 2.0.0) | Time-series aggregation, grouping, and statistical calculations |
| **Security & Cryptography** | cryptography (>= 42.0.0) | Fernet symmetric encryption and PBKDF2 key derivation |
| **Process Management** | psutil (>= 5.9.0) | Cross-platform port detection and clean session termination |
| **AI / LLM Integration** | requests / Ollama / REST | Multi-provider AI Copilot engine with resilience fallbacks |
| **Styling & Design** | Vanilla CSS3 | Dark glassmorphism, Minimalist Paper aesthetic, Google Fonts |

---

## 🚧 Known Behaviors & Roadmap

1. **Available Credits**:
   - *Current Behavior*: AWS Cost Explorer does not expose remaining promotional credits via `ce:GetCostAndUsage`. The primary dashboard focuses on **Gross Spend**, **Daily Average**, **Projected Annual Burn**, and **Net Out-of-Pocket Outlay**. Promotional credit tracking is supported via Settings for custom balance entry.
   - *Roadmap*: Direct integration with the AWS Invoicing / AWS Budgets API for automated credit balance sync.
2. **Alert Sources**:
   - *Current Behavior*: Workload spend alerts evaluate live AWS service burn against customizable percentage thresholds.
   - *Roadmap*: Live webhook ingestion of Amazon CloudWatch billing alarms and AWS SNS anomaly notifications.
3. **Multi-Account AWS Organizations**:
   - *Roadmap*: Linked account selector and Consolidated Billing breakdown across AWS Organizations accounts.
