from __future__ import annotations

import re
import unicodedata


class HotelNormalizationService:
    _PUNCTUATION_RE = re.compile(r"[^\w\s]")
    _SPACE_RE = re.compile(r"\s+")

    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        if not value:
            return ""
        lowered = value.strip().lower()
        no_accents = unicodedata.normalize("NFKD", lowered).encode("ascii", errors="ignore").decode("ascii")
        no_punctuation = cls._PUNCTUATION_RE.sub(" ", no_accents)
        collapsed = cls._SPACE_RE.sub(" ", no_punctuation).strip()
        return collapsed

    @classmethod
    def normalize_city(cls, city: str | None) -> str:
        return cls.normalize_text(city)

    @staticmethod
    def normalize_country_code(country_code: str | None) -> str:
        return (country_code or "").strip().upper()

