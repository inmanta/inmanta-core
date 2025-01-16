import json
from datetime import timedelta
from typing import Any, Iterable

from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey, EllipticCurvePublicKey
from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey, Ed448PublicKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

AllowedPublicKeys = RSAPublicKey | EllipticCurvePublicKey | Ed25519PublicKey | Ed448PublicKey
AllowedPrivateKeys = RSAPrivateKey | EllipticCurvePrivateKey | Ed25519PrivateKey | Ed448PrivateKey

def decode(
    jwt: str | bytes,
    key: AllowedPublicKeys | str | bytes = "",
    algorithms: list[str] | None = None,
    options: dict[str, Any] | None = None,
    # deprecated arg, remove in pyjwt3
    verify: bool | None = None,
    # could be used as passthrough to api_jws, consider removal in pyjwt3
    detached_payload: bytes | None = None,
    # passthrough arguments to _validate_claims
    # consider putting in options
    audience: str | Iterable[str] | None = None,
    issuer: str | None = None,
    leeway: float | timedelta = 0,
    # kwargs
    **kwargs: object,
) -> dict[str, object]: ...

def encode(
    payload: dict[str, Any],
    key: AllowedPrivateKeys | str | bytes,
    algorithm: str | None = "HS256",
    headers: dict[str, Any] | None = None,
    json_encoder: type[json.JSONEncoder] | None = None,
    sort_headers: bool = True,
) -> str: ...


def get_unverified_header(jwt: str | bytes) -> dict[str, object]: ...