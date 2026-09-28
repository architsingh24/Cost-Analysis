import streamlit as st
import pandas as pd
import subprocess
import requests
import time
import os

def ensure_ollama_running(timeout_seconds: float = 10.0):
    """
    Checks if Ollama server is running locally on port 11434.
    If not, programmatically launches the server in the background and waits until it is ready.
    Returns (is_ready: bool, status_message: str).
    """
    import shutil
    
    # 1. Quick check if already responding
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=0.8)
        if res.status_code == 200:
            models = [m.get('name', '') for m in res.json().get('models', [])]
            return True, f"Ollama is active ({', '.join(models) if models else 'ready'})"
    except Exception:
        pass

    # 2. Locate Ollama executable
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        for candidate in ["/opt/homebrew/bin/ollama", "/usr/local/bin/ollama", "/usr/bin/ollama", os.path.expanduser("~/.ollama/bin/ollama")]:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                ollama_bin = candidate
                break

    if not ollama_bin:
        return False, "Ollama executable not found. Please install Ollama from https://ollama.com"

    # 3. Start 'ollama serve' in background as detached process
    try:
        subprocess.Popen(
            [ollama_bin, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        return False, f"Failed to launch Ollama background process: {str(e)}"

    # 4. Actively poll until port 11434 is accepting requests
    t_start = time.time()
    while time.time() - t_start < timeout_seconds:
        try:
            res = requests.get("http://localhost:11434/api/tags", timeout=0.8)
            if res.status_code == 200:
                models = [m.get('name', '') for m in res.json().get('models', [])]
                return True, f"Ollama auto-started in background ({', '.join(models) if models else 'ready'})"
        except Exception:
            pass
        time.sleep(0.5)

    return False, f"Ollama process was launched via {ollama_bin} serve, but port 11434 did not respond within {timeout_seconds}s."

def build_finops_system_context(df: pd.DataFrame) -> str:
    """
    Builds the standardized FinOps grounding prompt containing live AWS telemetry,
    service breakdown, and machine-level spend.
    """
    total_spend = float(df['Cost'].sum()) if not df.empty and 'Cost' in df.columns else 0.0
    active_services = df['Service'].nunique() if not df.empty and 'Service' in df.columns else 0
    num_days = df['Date'].nunique() if not df.empty and 'Date' in df.columns else 1
    daily_avg = total_spend / num_days if num_days > 0 else 0.0
    annual_projection = daily_avg * 365.25

    if not df.empty and 'Service' in df.columns:
        df_service = df.groupby('Service')['Cost'].sum().sort_values(ascending=False)
        breakdown_str = "\n".join([f"- {svc}: ${cost:,.2f}" for svc, cost in df_service.items()])
        highest_service = df_service.idxmax()
        highest_cost = df_service.max()
    else:
        breakdown_str = "No active billing services in this period."
        highest_service = "None"
        highest_cost = 0.0

    is_connected = st.session_state.get('aws_connected', False)
    if is_connected:
        if not df.empty and 'Service' in df.columns:
            active_items = [f"- {svc}: active AWS resource with ${cost:,.2f} spend" for svc, cost in df_service.items() if cost > 0]
            machine_context = "\n".join(active_items) if active_items else "No active AWS workloads with recorded spend."
        else:
            machine_context = "No active AWS workloads with recorded spend."
    else:
        machine_context = (
            "- [Demo] prod-db-primary (r6i.4xlarge): high steady database load\n"
            "- [Demo] prod-api-cluster-01 (c6i.2xlarge): auto-scaling API cluster\n"
            "- [Demo] analytics-spark-master (m6i.4xlarge): batch analytics jobs\n"
            "- [Demo] worker-queue-node (c6g.xlarge): queue worker\n"
            "- [Demo] staging-k8s-ingress (t4g.xlarge): staging cluster node"
        )

    system_prompt = (
        "You are an AI FinOps assistant embedded inside a cloud cost analysis dashboard. "
        "You have access to the user's live AWS cost data, service breakdowns, and machine-level spend. "
        "Your job is to answer questions about their cloud spending and suggest concrete cost-optimization actions "
        "(e.g., Savings Plans, Spot Instances, rightsizing, storage tier changes) based on the real data provided to you.\n\n"
        "Here is the active cloud environment summary:\n"
        f"- Observation Window: {num_days} days\n"
        f"- Total Observed Spend: ${total_spend:,.2f}\n"
        f"- Historical Daily Average: ${daily_avg:,.2f}\n"
        f"- Annual Projected Run-Rate: ${annual_projection:,.2f}\n"
        f"- Active AWS Services Count: {active_services}\n"
        f"- Primary Cost Driver: {highest_service} (${highest_cost:,.2f})\n"
        f"- Service Cost Breakdown:\n{breakdown_str}\n\n"
        f"- Monitored Workloads & Instances:\n{machine_context}\n\n"
        "Guidelines:\n"
        "1. Give concise, actionable, and financially sound cloud optimization recommendations.\n"
        "2. Ground your answers strictly in the figures above. Do not invent non-existent AWS resources.\n"
        "3. Highlight high-impact optimizations like AWS Graviton migrations, S3 lifecycle transitions, and rightsizing idle nodes."
    )
    return system_prompt

def generate_ai_chat_response(
    prompt: str, 
    df: pd.DataFrame, 
    chat_history: list = None,
    provider: str = None,
    api_key: str = None,
    model_name: str = None,
    custom_endpoint: str = None
) -> str:
    """
    Sends the user's question to the configured AI provider (OpenAI, Google Gemini, Anthropic, Ollama, or Custom),
    injecting live FinOps cost context into the system prompt.
    """
    provider = provider or st.session_state.get('ai_provider', 'Local Ollama')
    api_key = api_key or st.session_state.get('ai_api_key', '') or st.session_state.get('ai_provider_keys', {}).get(provider, '')
    model_name = model_name or st.session_state.get('ai_model_name', '') or st.session_state.get('ai_provider_models', {}).get(provider, '')
    custom_endpoint = custom_endpoint or st.session_state.get('ai_custom_endpoint', '')
    
    system_prompt = build_finops_system_context(df)
    
    if chat_history is None:
        chat_history = st.session_state.get('chat_history', [])

    # 1. Google Gemini Provider
    if provider == "Google Gemini":
        key = (api_key or os.environ.get('GEMINI_API_KEY', '')).strip()
        if not key:
            return "⚠️ Please configure your Google Gemini API Key in Settings or in the AI Assistant configuration panel."
        
        # Build prompt with system context + conversation history
        conv_text = f"System Instructions:\n{system_prompt}\n\nConversation History:\n"
        for msg in chat_history[-6:]:
            conv_text += f"{msg['role'].capitalize()}: {msg['content']}\n"
        conv_text += f"\nUser: {prompt}\nAssistant:"

        payload = {"contents": [{"parts": [{"text": conv_text}]}]}
        headers = {"Content-Type": "application/json"}

        # Auto-upgrade deprecated/sunset models (e.g. gemini-1.5-flash, gemini-2.5-flash) to current gemini-3.6-flash
        primary_model = (model_name or "gemini-3.6-flash").strip()
        if primary_model in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-pro"]:
            primary_model = "gemini-3.6-flash"

        # Prioritized resilience pool to handle server overload ("model is being used too much")
        # Flash-Lite models have dedicated, separate capacity and respond in ~1.1s
        models_to_try = [primary_model]
        for fallback_m in [
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-3.6-flash"
        ]:
            if fallback_m not in models_to_try:
                models_to_try.append(fallback_m)

        last_error = ""
        for i, m in enumerate(models_to_try):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=16.0)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get('candidates', [{}])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [{}])
                        if parts and 'text' in parts[0]:
                            ans_text = parts[0]['text']
                            # If we had to failover from an overloaded primary model, add a subtle informative note
                            if i > 0:
                                return f"*(Note: Primary model was busy/overloaded; answered via high-speed {m})*\n\n" + ans_text
                            return ans_text
                    return 'No response received from Gemini.'
                elif res.status_code in [503, 429]:
                    # 503 = "The model is overloaded. Please try again later." / "model is being used too much"
                    # 429 = "Resource has been exhausted" / rate limit
                    last_error = f"Model '{m}' is currently busy / rate-limited ({res.status_code})."
                    time.sleep(0.5)
                    continue
                elif res.status_code == 404:
                    last_error = f"Model '{m}' was not found on Google's API (404)."
                    continue
                elif res.status_code == 400:
                    err_data = {}
                    try:
                        err_data = res.json().get('error', {})
                    except Exception:
                        pass
                    msg = err_data.get('message', res.text)
                    return f"⚠️ Gemini API Error (400 - Invalid Request): {msg}"
                else:
                    last_error = f"Gemini API Error ({res.status_code}): {res.text}"
            except Exception as e:
                last_error = f"Connection error on '{m}': {str(e)}"
                time.sleep(0.5)
                continue

        # If all Gemini models returned 503/429, try auto-fallback to Local Ollama if available
        is_ollama_ok, _ = ensure_ollama_running(timeout_seconds=3.0)
        if is_ollama_ok:
            try:
                ollama_ans = generate_ai_chat_response(
                    prompt=prompt,
                    df=df,
                    chat_history=chat_history,
                    provider="Local Ollama"
                )
                if ollama_ans and not ollama_ans.startswith("⚠️"):
                    return (
                        "💡 *Note: Google Gemini cloud servers reported high global traffic ('model is being used too much'). "
                        "Your question was automatically and seamlessly answered by Local Llama 3.1:*\n\n"
                        + ollama_ans
                    )
            except Exception:
                pass

        return (
            f"⚠️ **Google Gemini Service Notice**: {last_error}\n\n"
            "Google's free-tier servers for this model are experiencing high global traffic right now ('model is being used too much').\n"
            "**Recommended**: Switch to **Local Ollama** in the configuration panel above to run completely offline on your Mac with zero rate limits!"
        )

    # 2. OpenAI Provider
    elif provider == "OpenAI":
        key = api_key or os.environ.get('OPENAI_API_KEY', '')
        if not key:
            return "⚠️ Please configure your OpenAI API Key in Settings or in the AI Assistant configuration panel."
        model = model_name if model_name else "gpt-4o-mini"
        endpoint = custom_endpoint if custom_endpoint else "https://api.openai.com/v1/chat/completions"
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            res = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": 0.3},
                timeout=25.0
            )
            if res.status_code == 200:
                return res.json().get('choices', [{}])[0].get('message', {}).get('content', 'No content returned from OpenAI.')
            else:
                return f"OpenAI API Error ({res.status_code}): {res.text}"
        except Exception as e:
            return f"Error connecting to OpenAI API: {str(e)}"

    # 3. Anthropic Claude Provider
    elif provider == "Anthropic Claude":
        key = api_key or os.environ.get('ANTHROPIC_API_KEY', '')
        if not key:
            return "⚠️ Please configure your Anthropic API Key in Settings or in the AI Assistant configuration panel."
        model = model_name if model_name else "claude-3-5-sonnet-20241022"
        
        messages = []
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            res = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={"model": model, "max_tokens": 1024, "system": system_prompt, "messages": messages},
                timeout=25.0
            )
            if res.status_code == 200:
                return res.json().get('content', [{}])[0].get('text', 'No response from Claude.')
            else:
                return f"Anthropic API Error ({res.status_code}): {res.text}"
        except Exception as e:
            return f"Error connecting to Anthropic API: {str(e)}"

    # 4. Generic Custom OpenAI-Compatible Endpoint
    elif provider == "Custom Endpoint":
        endpoint = custom_endpoint or "http://localhost:8000/v1/chat/completions"
        model = model_name or "default"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            res = requests.post(
                endpoint,
                headers=headers,
                json={"model": model, "messages": messages},
                timeout=25.0
            )
            if res.status_code == 200:
                data = res.json()
                if 'choices' in data:
                    return data['choices'][0].get('message', {}).get('content', '')
                elif 'message' in data:
                    return data['message'].get('content', '')
                return str(data)
            else:
                return f"Custom Endpoint returned error ({res.status_code}): {res.text}"
        except Exception as e:
            return f"Error connecting to Custom Endpoint ({endpoint}): {str(e)}"

    # 5. Default: Local Ollama
    else:
        is_ready, status_msg = ensure_ollama_running(timeout_seconds=10.0)
        if not is_ready:
            return (
                f"⚠️ **Could not connect to Local Ollama**:\n{status_msg}\n\n"
                "Please verify Ollama is installed on your Mac, or switch to **Google Gemini** in the configuration panel above."
            )

        # Inspect available local models
        installed_models = []
        try:
            tags_res = requests.get("http://localhost:11434/api/tags", timeout=2.0)
            if tags_res.status_code == 200:
                installed_models = [m.get('name', '') for m in tags_res.json().get('models', [])]
        except Exception:
            pass

        model = model_name if model_name else "llama3.1:8b"
        
        # If requested model not installed, but other models exist, automatically pick the first available one!
        if installed_models and model not in installed_models:
            matched = [m for m in installed_models if model.split(':')[0] in m]
            if matched:
                model = matched[0]
            else:
                model = installed_models[0]

        endpoint = custom_endpoint if custom_endpoint else "http://localhost:11434/api/chat"
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            res = requests.post(
                endpoint,
                json={"model": model, "messages": messages, "stream": False},
                timeout=120.0  # Generous 2-minute generation timeout for local LLMs
            )
            if res.status_code == 200:
                return res.json().get('message', {}).get('content', 'Error: Empty response from Ollama.')
            elif res.status_code == 404:
                return f"⚠️ Model '{model}' not found in local Ollama. Installed models: {', '.join(installed_models) if installed_models else 'None'}. Run `ollama pull llama3.1:8b` in your terminal to download."
            else:
                return f"Ollama returned status code {res.status_code}: {res.text}"
        except Exception as e:
            return f"⚠️ Local Ollama Server Note: {str(e)}\nPlease ensure Ollama has sufficient RAM to run '{model}'."

# Alias for backward compatibility
generate_ollama_chat_response = generate_ai_chat_response

# --- Persistent Chat History Management ---
CHAT_STORAGE_FILE = ".chat_history.json"

def get_default_chat_session() -> dict:
    """Returns a fresh initial chat session."""
    session_id = f"chat_{int(time.time())}"
    return {
        "id": session_id,
        "title": "FinOps Conversation 1",
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
        "messages": [
            {
                "role": "assistant",
                "content": "Hello! I am your AI FinOps Assistant. I have live access to your AWS spend and resource breakdown. How can I help you analyze costs or find optimization opportunities today?"
            }
        ]
    }

def load_all_chat_sessions() -> dict:
    """Loads past chat sessions from local file storage or returns a fresh initial session."""
    import json
    if os.path.exists(CHAT_STORAGE_FILE):
        try:
            with open(CHAT_STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass
            
    initial = get_default_chat_session()
    return {initial["id"]: initial}

def save_all_chat_sessions(sessions: dict):
    """Persists chat sessions to local file storage."""
    import json
    try:
        with open(CHAT_STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        print(f"Failed to persist chat sessions: {e}")

def create_new_chat_session(title: str = None) -> dict:
    """Creates and returns a new empty chat session."""
    session_id = f"chat_{int(time.time())}_{int(time.time() * 1000) % 1000}"
    new_sess = {
        "id": session_id,
        "title": title if title else f"Conversation {time.strftime('%b %d, %H:%M')}",
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
        "messages": [
            {
                "role": "assistant",
                "content": "Hello! I am your AI FinOps Assistant. How can I help you analyze or optimize your AWS costs today?"
            }
        ]
    }
    return new_sess
