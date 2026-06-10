import os
import bcrypt
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


def get_authenticator(config_path="secrets/auth.yaml"):
    """
    Load Streamlit Authenticator config.
    """
    # Create default config if not exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    if not os.path.exists(config_path):
        # Default user: admin / admin123
        hashed_password = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        default_config = {
            "credentials": {
                "usernames": {
                    "admin": {
                        "name": "Admin",
                        "password": hashed_password,
                        "role": "admin"
                    }
                }
            },
            "cookie": {
                "expiry_days": 1,
                "key": "georag_cookie_secret",
                "name": "georag_auth_cookie"
            },
        }
        with open(config_path, 'w') as file:
            yaml.dump(default_config, file, default_flow_style=False)

    with open(config_path) as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
    )
    return authenticator, config


def save_auth_config(config, config_path="secrets/auth.yaml"):
    with open(config_path, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)


# JWT Auth (If local FastAPI is used)
from fastapi.security import HTTPBearer
from jose import jwt

# SECRET_KEY is supposed to be in env
SECRET_KEY = os.environ.get("JWT_SECRET", "default_insecure_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480
