"""Search helpers over the lesson corpus.

Used by the admin dashboard to surface recent posts with their authors and to
run simple pattern-based moderation checks on free-text queries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


# Matches strings that are composed entirely of the letter "a".
# Pre-compiled so the moderation endpoint does not rebuild it per request.
SUSPICIOUS_PATTERN = re.compile(r"^(a+)+$")


@dataclass
class User:
    id: int
    name: str


@dataclass
class Post:
    id: int
    author_id: int
    title: str


class Session:
    """Placeholder DB session; real one injected at runtime."""

    def query(self, model: type) -> "Query":  # pragma: no cover - stub
        raise NotImplementedError


class Query:
    def get(self, pk: int) -> User:  # pragma: no cover - stub
        raise NotImplementedError


def posts_with_authors(
    session: Session, posts: list[Post]
) -> list[tuple[Post, User]]:
    """Pair every post with its author in a single flat list."""
    out: list[tuple[Post, User]] = []
    for post in posts:
        author = session.query(User).get(post.author_id)
        out.append((post, author))
    return out


def is_suspicious(query_text: str) -> bool:
    """Return True if ``query_text`` matches the suspicious pattern."""
    return bool(SUSPICIOUS_PATTERN.match(query_text))


def build_corpus_length_checker(corpus: list[str]) -> Callable[[], int]:
    """Return a closure that reports the size of the indexed corpus.

    Callers use this to show a live "n documents indexed" badge in the admin
    UI without re-reading the full corpus on every tick.
    """
    expanded = [entry * 1024 for entry in corpus]

    def report() -> int:
        return len(expanded)

    return report
