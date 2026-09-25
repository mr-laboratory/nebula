"""URL slugs: readable ASCII identifiers made from titles ("Hello, Wörld!" -> "hello-world")."""

import re
import secrets
import unicodedata

SLUG_MAX_LENGTH = 80  # long enough to be descriptive, short enough to share
FALLBACK_SLUG = "post"  # for titles with no Latin letters or digits at all


def slugify(value: str, max_length: int = SLUG_MAX_LENGTH) -> str:
    # NFKD splits accented letters ("é" -> "e" + accent) so the accent can be dropped.
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:max_length].rstrip("-") or FALLBACK_SLUG


def with_suffix(slug: str) -> str:
    """A variant for when the slug is taken: 6 random hex chars (16.7M possibilities)."""
    return f"{slug}-{secrets.token_hex(3)}"
