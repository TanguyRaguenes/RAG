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
    normalized_issuer = _clean_identifier(issuer)
    normalized_subject = _clean_identifier(subject)

    return _hash_identifier(f"{normalized_issuer}|{normalized_subject}", secret)


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

    return _hash_identifier(normalized_identifier, secret)


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


def _clean_identifier(identifier: str) -> str:
    """Retire les espaces sans altérer la casse significative d'un claim OIDC.

    Args:
        identifier: Claim `iss` ou `sub` validé par le client OIDC.

    Returns:
        Identifiant nettoyé en conservant exactement sa casse.

    Raises:
        ValueError: Si le claim est vide après nettoyage.
    """
    cleaned_identifier = identifier.strip()
    if not cleaned_identifier:
        raise ValueError("Authenticated user identifier is required")
    return cleaned_identifier


def _hash_identifier(identifier: str, secret: str) -> str:
    """Hache un identifiant déjà normalisé avec le secret applicatif.

    Args:
        identifier: Identifiant nettoyé selon les règles de son type.
        secret: Secret HMAC servant à pseudonymiser l'identité.

    Returns:
        Empreinte SHA-256 stable de l'identifiant.

    Raises:
        ValueError: Si le secret applicatif est vide.
    """
    if not secret.strip():
        raise ValueError("USER_HASH_SECRET must not be empty")
    return hmac.new(
        secret.encode("utf-8"),
        identifier.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
