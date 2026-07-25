import hashlib
import hmac


def build_user_id_from_email(email: str, secret: str) -> str:
    """Construit un identifiant utilisateur stable à partir d'une adresse e-mail.

    Args:
        email: Adresse e-mail utilisée pour identifier l'utilisateur sans l'exposer inutilement.
        secret: Secret applicatif utilisé pour hacher un identifiant utilisateur.

    Returns:
        Identifiant utilisateur pseudonymisé dérivé de l'e-mail.
    """
    normalized_email = _normalize_identifier(email)

    return build_user_id_from_identifier(normalized_email, secret)


def build_user_id_from_oidc_subject(issuer: str, subject: str, secret: str) -> str:
    """Construit l'identifiant interne stable d'un utilisateur OIDC.

    Args:
        issuer: Émetteur OIDC qui a produit le token utilisateur.
        subject: Claim `sub` stable de l'utilisateur chez cet émetteur.
        secret: Secret applicatif utilisé pour pseudonymiser l'identité OIDC.

    Returns:
        Identifiant utilisateur pseudonymisé dérivé du couple `issuer + sub`.
    """
    normalized_issuer = _normalize_identifier(issuer)
    normalized_subject = _normalize_identifier(subject)

    return build_user_id_from_identifier(
        f"{normalized_issuer}|{normalized_subject}", secret
    )


def build_user_id_from_identifier(identifier: str, secret: str) -> str:
    """Construit un identifiant utilisateur pseudonymisé à partir d'un identifiant OIDC.

    Args:
        identifier: Identifiant source à normaliser ou pseudonymiser.
        secret: Secret applicatif utilisé pour hacher un identifiant utilisateur.

    Returns:
        Identifiant utilisateur pseudonymisé dérivé de l'identifiant source.

    Raises:
        ValueError: Si une valeur obligatoire est absente ou invalide.
    """
    normalized_identifier = _normalize_identifier(identifier)

    if not secret.strip():
        raise ValueError("USER_HASH_SECRET must not be empty")

    return hmac.new(
        secret.encode("utf-8"),
        normalized_identifier.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _normalize_identifier(identifier: str) -> str:
    """Normalise un identifiant avant de le hacher ou de le comparer.

    Args:
        identifier: Identifiant source à normaliser ou pseudonymiser.

    Returns:
        Valeur normalisée prête à être comparée, stockée ou affichée.

    Raises:
        ValueError: Si une valeur obligatoire est absente ou invalide.
    """
    normalized_identifier = identifier.strip().lower()

    if not normalized_identifier:
        raise ValueError("Authenticated user identifier is required")

    return normalized_identifier
