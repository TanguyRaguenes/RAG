import hashlib
import hmac


def build_user_id_from_email(email: str, secret: str) -> str:
    normalized_email = _normalize_identifier(email)

    return build_user_id_from_identifier(normalized_email, secret)


def build_user_id_from_identifier(identifier: str, secret: str) -> str:
    normalized_identifier = _normalize_identifier(identifier)

    if not secret.strip():
        raise ValueError("USER_HASH_SECRET must not be empty")

    return hmac.new(
        secret.encode("utf-8"),
        normalized_identifier.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _normalize_identifier(identifier: str) -> str:
    normalized_identifier = identifier.strip().lower()

    if not normalized_identifier:
        raise ValueError("Authenticated user identifier is required")

    return normalized_identifier
