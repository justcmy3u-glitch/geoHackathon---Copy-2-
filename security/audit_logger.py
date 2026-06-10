import structlog
import json
import psycopg2
import os
from datetime import datetime

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

audit_log = structlog.get_logger("audit")

AUDIT_EVENTS = {
    "FILE_UPLOAD":    {"level": "INFO",    "retain_days": 365},
    "FILE_DELETE":    {"level": "WARNING", "retain_days": 365},
    "QUERY_MADE":     {"level": "INFO",    "retain_days": 90},
    "AUTH_SUCCESS":   {"level": "INFO",    "retain_days": 365},
    "AUTH_FAILURE":   {"level": "WARNING", "retain_days": 365},
    "SECURITY_BLOCK": {"level": "ERROR",   "retain_days": 730},
    "COLAB_REQUEST":  {"level": "INFO",    "retain_days": 90},
    "HALLUCINATION":  {"level": "WARNING", "retain_days": 180},
}

def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            database="georag",
            user="postgres",
            password=os.environ.get("POSTGRES_PASSWORD", "password")
        )
    except Exception as e:
        audit_log.error("db_connection_failed", error=str(e))
        return None

def log_event(event_type: str, user: str, details: dict):
    if event_type not in AUDIT_EVENTS:
        audit_log.warning("unknown_event_type", type=event_type)
        level = "INFO"
    else:
        level = AUDIT_EVENTS[event_type]["level"]

    log_method = getattr(audit_log, level.lower(), audit_log.info)
    
    # Write to local JSON structured log
    log_method(
        event_type,
        user=user,
        **details
    )
    
    # Write to Postgres
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audit_log (event_type, user_id, details, created_at) VALUES (%s, %s, %s, %s)",
                    (event_type, user, json.dumps(details), datetime.utcnow())
                )
            conn.commit()
        except Exception as e:
            audit_log.error("db_insert_failed", error=str(e))
        finally:
            conn.close()
