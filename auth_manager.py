import json
import os
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

VAULT_FILE = ".user_vault.json"
ANONYMOUS_THEME_FILE = ".anonymous_settings.json"

DEFAULT_THEME = {
    "primary_accent": "#f97316",
    "sidebar_bg": "#0f0a07",
    "card_bg": "rgba(30, 20, 15, 0.75)",
    "font_color": "#fdfbf7",
    "main_bg_start": "#180f0a",
    "main_bg_end": "#0d0805"
}

def load_vault() -> dict:
    """Loads the user vault database from disk."""
    if not os.path.exists(VAULT_FILE):
        return {"users": {}}
    try:
        with open(VAULT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}

def save_vault(vault_data: dict):
    """Saves the user vault database to disk."""
    try:
        with open(VAULT_FILE, "w") as f:
            json.dump(vault_data, f, indent=4)
    except Exception as e:
        print(f"Failed to write to user vault: {e}")

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    """Computes a PBKDF2 hash of the master password using SHA-256."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return key.hex(), salt.hex()

def derive_encryption_key(password: str, salt_hex: str) -> bytes:
    """Derives a Fernet symmetric encryption key from the password and salt."""
    salt = bytes.fromhex(salt_hex)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    derived = kdf.derive(password.encode('utf-8'))
    return base64.urlsafe_b64encode(derived)

def encrypt_value(value: str, key: bytes) -> str:
    """Encrypts a string value using Fernet symmetric encryption."""
    if not value:
        return ""
    f = Fernet(key)
    return f.encrypt(value.encode('utf-8')).decode('utf-8')

def decrypt_value(encrypted_value: str, key: bytes) -> str:
    """Decrypts a Fernet encrypted string back to plaintext."""
    if not encrypted_value:
        return ""
    f = Fernet(key)
    return f.decrypt(encrypted_value.encode('utf-8')).decode('utf-8')

def create_user_account(username: str, password: str, aws_access_key: str, aws_secret_key: str, aws_session_token: str = None) -> dict:
    """Registers a new user, hashes password, encrypts AWS keys, and stores in the vault."""
    vault = load_vault()
    if username in vault["users"]:
        return {"success": False, "error": "Username already exists."}

    password_hash, salt_hex = hash_password(password)
    key = derive_encryption_key(password, salt_hex)

    enc_access = encrypt_value(aws_access_key, key)
    enc_secret = encrypt_value(aws_secret_key, key)
    enc_session = encrypt_value(aws_session_token if aws_session_token else "", key)

    vault["users"][username] = {
        "salt": salt_hex,
        "password_hash": password_hash,
        "encrypted_aws_access_key": enc_access,
        "encrypted_aws_secret_key": enc_secret,
        "encrypted_aws_session_token": enc_session,
        "theme": DEFAULT_THEME
    }

    save_vault(vault)
    return {"success": True}

def register_user(username: str, password: str, aws_access_key: str, aws_secret_key: str, aws_session_token: str = None) -> dict:
    """Registers a new user and returns credential payload for immediate session setup."""
    create_res = create_user_account(username, password, aws_access_key, aws_secret_key, aws_session_token)
    if not create_res["success"]:
        return create_res
    
    # Authenticate immediately to load derived key and session settings
    auth_res = authenticate_user(username, password)
    return auth_res

def authenticate_user(username: str, password: str) -> dict:
    """Validates user password and decrypts stored AWS credentials."""
    vault = load_vault()
    if username not in vault["users"]:
        return {"success": False, "error": "User not found."}

    user_record = vault["users"][username]
    salt_hex = user_record["salt"]
    stored_hash = user_record["password_hash"]

    # Re-compute hash to verify master password
    computed_hash, _ = hash_password(password, bytes.fromhex(salt_hex))
    if computed_hash != stored_hash:
        return {"success": False, "error": "Incorrect password."}

    try:
        key = derive_encryption_key(password, salt_hex)
        dec_access = decrypt_value(user_record["encrypted_aws_access_key"], key)
        dec_secret = decrypt_value(user_record["encrypted_aws_secret_key"], key)
        dec_session = decrypt_value(user_record.get("encrypted_aws_session_token", ""), key)
        
        # Load theme or use default
        theme = user_record.get("theme", DEFAULT_THEME)

        return {
            "success": True,
            "aws_access_key": dec_access,
            "aws_secret_key": dec_secret,
            "aws_session_token": dec_session,
            "aws_connected": bool(dec_access and dec_secret),
            "aws_account_id": "",
            "aws_arn": "",
            "enc_key": base64.b64encode(key).decode('utf-8'),
            "theme": theme
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to decrypt credentials: {str(e)}"}

def update_user_credentials(username: str, aws_access_key: str, aws_secret_key: str, aws_session_token: str = None, password: str = None, enc_key_b64: str = None) -> dict:
    """Updates the encrypted AWS credentials for a verified user using password or session encryption key."""
    vault = load_vault()
    if username not in vault["users"]:
        return {"success": False, "error": "User not found."}

    user_record = vault["users"][username]
    salt_hex = user_record["salt"]

    key = None
    if enc_key_b64:
        try:
            key = base64.b64decode(enc_key_b64.encode('utf-8'))
        except Exception:
            key = None

    if key is None and password:
        stored_hash = user_record["password_hash"]
        computed_hash, _ = hash_password(password, bytes.fromhex(salt_hex))
        if computed_hash != stored_hash:
            return {"success": False, "error": "Incorrect password."}
        key = derive_encryption_key(password, salt_hex)

    if key is None:
        return {"success": False, "error": "Authentication verification required to encrypt credentials."}

    try:
        enc_access = encrypt_value(aws_access_key, key)
        enc_secret = encrypt_value(aws_secret_key, key)
        enc_session = encrypt_value(aws_session_token if aws_session_token else "", key)

        user_record["encrypted_aws_access_key"] = enc_access
        user_record["encrypted_aws_secret_key"] = enc_secret
        user_record["encrypted_aws_session_token"] = enc_session
        
        vault["users"][username] = user_record
        save_vault(vault)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"Failed to update credentials: {str(e)}"}

def save_user_theme(username: str, theme_data: dict):
    """Saves the user's theme settings to the vault."""
    vault = load_vault()
    if username in vault["users"]:
        vault["users"][username]["theme"] = theme_data
        save_vault(vault)

def load_user_theme(username: str) -> dict:
    """Loads the user's theme settings from the vault."""
    vault = load_vault()
    if username in vault["users"]:
        return vault["users"][username].get("theme", DEFAULT_THEME)
    return DEFAULT_THEME

def save_anonymous_theme(theme_data: dict):
    """Saves the unauthenticated theme settings to disk."""
    try:
        with open(ANONYMOUS_THEME_FILE, "w") as f:
            json.dump(theme_data, f, indent=4)
    except Exception as e:
        print(f"Failed to save anonymous theme: {e}")

def load_anonymous_theme() -> dict:
    """Loads the unauthenticated theme settings from disk."""
    if not os.path.exists(ANONYMOUS_THEME_FILE):
        return DEFAULT_THEME
    try:
        with open(ANONYMOUS_THEME_FILE, "r") as f:
            data = json.load(f)
            # If the file contains custom_credit_balance, extract theme or return DEFAULT_THEME
            if "primary_accent" in data:
                return data
            return DEFAULT_THEME
    except Exception:
        return DEFAULT_THEME

def save_custom_credits(amount: float):
    """Saves custom available credits to local settings file."""
    data = {}
    if os.path.exists(ANONYMOUS_THEME_FILE):
        try:
            with open(ANONYMOUS_THEME_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["custom_credit_balance"] = float(amount)
    try:
        with open(ANONYMOUS_THEME_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to save custom credit balance: {e}")

def load_custom_credits() -> float | None:
    """Loads custom available credits from local settings file."""
    if not os.path.exists(ANONYMOUS_THEME_FILE):
        return None
    try:
        with open(ANONYMOUS_THEME_FILE, "r") as f:
            data = json.load(f)
            if "custom_credit_balance" in data:
                return float(data["custom_credit_balance"])
    except Exception:
        return None
    return None

AI_SETTINGS_FILE = ".ai_settings.json"

DEFAULT_AI_SETTINGS = {
    "active_provider": "Local Ollama",
    "provider_models": {
        "Local Ollama": "llama3.1:8b",
        "Google Gemini": "gemini-3.6-flash",
        "OpenAI": "gpt-4o-mini",
        "Anthropic Claude": "claude-3-5-sonnet-20241022",
        "Custom Endpoint": "default"
    },
    "provider_keys": {
        "Local Ollama": "",
        "Google Gemini": "",
        "OpenAI": "",
        "Anthropic Claude": "",
        "Custom Endpoint": ""
    },
    "custom_endpoint": "http://localhost:8000/v1/chat/completions"
}

def load_ai_settings() -> dict:
    """Loads persistent AI model configuration and API keys from disk."""
    import copy
    settings = copy.deepcopy(DEFAULT_AI_SETTINGS)
    if not os.path.exists(AI_SETTINGS_FILE):
        return settings
    try:
        with open(AI_SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            if isinstance(saved, dict):
                if "active_provider" in saved:
                    settings["active_provider"] = saved["active_provider"]
                if "custom_endpoint" in saved:
                    settings["custom_endpoint"] = saved["custom_endpoint"]
                if "provider_models" in saved and isinstance(saved["provider_models"], dict):
                    settings["provider_models"].update(saved["provider_models"])
                if "provider_keys" in saved and isinstance(saved["provider_keys"], dict):
                    settings["provider_keys"].update(saved["provider_keys"])
    except Exception as e:
        print(f"Warning: Failed to load AI settings: {e}")
    return settings

def save_ai_settings(settings: dict):
    """Saves AI model configuration and API keys permanently to disk."""
    try:
        current = load_ai_settings()
        if "active_provider" in settings:
            current["active_provider"] = settings["active_provider"]
        if "custom_endpoint" in settings:
            current["custom_endpoint"] = settings["custom_endpoint"]
        if "provider_models" in settings and isinstance(settings["provider_models"], dict):
            current["provider_models"].update(settings["provider_models"])
        if "provider_keys" in settings and isinstance(settings["provider_keys"], dict):
            current["provider_keys"].update(settings["provider_keys"])
            
        with open(AI_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4)
        return True
    except Exception as e:
        print(f"Failed to save AI settings: {e}")
        return False

