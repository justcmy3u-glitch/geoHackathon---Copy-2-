import os
import hmac

class TunnelAuth:
    """
    Verifies that requests to/from Colab contain the correct HMAC key.
    This logic is mostly used by the Colab server itself, but defined here for consistency.
    """
    @staticmethod
    def verify_api_key(received_key: str, expected_key: str) -> bool:
        if not received_key or not expected_key:
            return False
        return hmac.compare_digest(received_key.encode('utf-8'), expected_key.encode('utf-8'))
