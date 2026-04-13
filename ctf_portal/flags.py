import hmac
import hashlib


def generate_flag(slug: str, user_id: int, secret: str) -> str:
    """HMAC 기반 동적 플래그 생성. 사용자별로 고유한 플래그를 반환."""
    mac = hmac.new(
        secret.encode(), f"{slug}:{user_id}".encode(), hashlib.sha256
    ).hexdigest()[:12]
    return f"FLAG{{{slug}_{mac}}}"
