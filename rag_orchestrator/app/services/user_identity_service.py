import hashlib
import hmac


def build_user_id_from_email(email: str, secret: str) -> str:
    normalized_email = _normalize_email(email)

    if not secret.strip():
        raise ValueError("USER_HASH_SECRET must not be empty")

    return hmac.new(
        secret.encode("utf-8"),
        normalized_email.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _normalize_email(email: str) -> str:
    normalized_email = email.strip().lower()

    if not normalized_email:
        raise ValueError("Authenticated user email is required")

    return normalized_email
