from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from http.cookiejar import Cookie
import logging
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HarvestedCookie:
    name: str
    value: str
    domain: str
    path: str
    secure: bool = True
    expires: int | None = None

    @classmethod
    def from_playwright_entry(cls, entry: Mapping[str, object]) -> "HarvestedCookie | None":
        name = entry.get("name")
        value = entry.get("value")
        if not (isinstance(name, str) and isinstance(value, str) and name and value):
            return None
        raw_domain = entry.get("domain")
        raw_path = entry.get("path")
        domain = raw_domain if isinstance(raw_domain, str) else ""
        path = raw_path if isinstance(raw_path, str) and raw_path else "/"
        secure = bool(entry.get("secure", True))
        raw_expires = entry.get("expires")
        expires: int | None = None
        if isinstance(raw_expires, (int, float)) and raw_expires > 0:
            expires = int(raw_expires)
        return cls(name=name, value=value, domain=domain, path=path, secure=secure, expires=expires)


def merge_cookies_into_session(session: Any, cookies: list[HarvestedCookie] | None) -> None:
    if not cookies:
        return
    jar = getattr(session, "cookies", None)
    if jar is None:
        return
    try:
        for entry in cookies:
            if hasattr(jar, "set") and callable(getattr(jar, "set", None)):
                try:
                    jar.set(entry.name, entry.value)  # type: ignore[attr-defined]
                    continue
                except TypeError:
                    pass
            cookie = Cookie(
                version=0,
                name=entry.name,
                value=entry.value,
                port=None,
                port_specified=False,
                domain=entry.domain,
                domain_specified=bool(entry.domain),
                domain_initial_dot=entry.domain.startswith("."),
                path=entry.path or "/",
                path_specified=bool(entry.path),
                secure=entry.secure,
                expires=entry.expires,
                discard=entry.expires is None,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False,
            )
            jar.set_cookie(cookie)
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.debug("merge_cookies_into_session skipped: %s", exc)


def merge_cookies_from_mapping(session: Any, cookies: Mapping[str, str] | None) -> None:
    if not cookies:
        return
    jar = getattr(session, "cookies", None)
    if jar is None:
        return
    try:
        for name, value in cookies.items():
            if hasattr(jar, "set") and callable(getattr(jar, "set", None)):
                jar.set(name, value)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.debug("merge_cookies_from_mapping skipped: %s", exc)
