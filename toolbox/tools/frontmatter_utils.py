"""
Front matter utilities for QiOS notes.
Ensures all notes have proper YAML front matter per MTA.001.
"""
import datetime
from typing import List, Optional
from textwrap import dedent


def ensure_frontmatter(
    content_md: str,
    *,
    title: str,
    slug: str,
    realm: str,
    tags: Optional[List[str]] = None,
    sensitivity: str = "internal",
    qid: Optional[str] = None,
    node: str = "kb",
    doc_type: str = "note",
    created: Optional[str] = None,
    updated: Optional[str] = None,
) -> str:
    """
    Ensure content_md has YAML front matter.
    If it already starts with ---, leave it alone.
    Otherwise, prepend front matter.
    """
    # If content already starts with front matter, leave it alone
    stripped = content_md.lstrip()
    if stripped.startswith("---"):
        return content_md

    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    created = created or now
    updated = updated or now

    tags_yaml = ""
    if tags:
        tags_yaml = "tags:\n" + "\n".join(f"  - {t}" for t in tags)
    else:
        tags_yaml = "tags: []"

    qid_line = f"qid: {qid}" if qid else "qid: ''"

    fm = f"""---
title: {title}
slug: {slug}
realm: {realm}
type: {doc_type}
node: {node}
created: {created}
updated: {updated}
{qid_line}
sensitivity: {sensitivity}
{tags_yaml}
---

"""

    return fm + content_md.lstrip()

