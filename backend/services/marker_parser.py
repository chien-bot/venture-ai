"""
services/marker_parser.py
─────────────────────────────────────────────────────────────
Robust parser for LLM HTML-comment markers: <!--SCORES:-->, <!--RUBRIC:-->, <!--RUBRIC_FULL:-->.

LLMs frequently deviate from the expected format:
  - Missing closing -->
  - Extra whitespace / newlines inside the marker
  - Bare JSON blocks (no comment wrapper)
  - JSON in code fences (```json ... ```)
  - Malformed closing like }> or } -->
  - Mixed-case tag names

This module provides a single extraction function per marker type,
each trying multiple regex patterns in priority order.
"""

import re
import json
import logging

logger = logging.getLogger(__name__)


# ── Internal helpers ───────────────────────────────────────────

def _try_parse_json(raw: str) -> dict | None:
    """Attempt to parse JSON, tolerating common LLM quirks."""
    raw = raw.strip()
    if not raw:
        return None
    # Strip trailing commas before } or ]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _extract_first_json_object(text: str) -> dict | None:
    """Find the first balanced { ... } in text and parse it."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return _try_parse_json(text[start : i + 1])
    # Unbalanced — try adding closing brace
    return _try_parse_json(text[start:] + "}")


# ── SCORES extraction ─────────────────────────────────────────

_SCORES_PATTERNS = [
    # 1. Standard: <!--SCORES:{...}-->
    re.compile(r"<!--\s*SCORES\s*:\s*(.*?)\s*-->", re.IGNORECASE | re.DOTALL),
    # 2. Unclosed: <!--SCORES:{...} (no -->)
    re.compile(r"<!--\s*SCORES\s*:\s*(\{[^}]*\})", re.IGNORECASE),
    # 3. Malformed close: <!--SCORES:{...}> or <!--SCORES:{...} -->
    re.compile(r"<!--\s*SCORES\s*:\s*(\{.*?\})\s*-?-?>?", re.IGNORECASE | re.DOTALL),
]


def parse_scores(text: str) -> dict | None:
    """Extract SCORES JSON from LLM output. Returns dict or None."""
    for pat in _SCORES_PATTERNS:
        m = pat.search(text)
        if m:
            result = _try_parse_json(m.group(1))
            if result:
                return result

    # Fallback: look for JSON in ```json code fence with score-like keys
    fence_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text)
    if fence_match:
        obj = _try_parse_json(fence_match.group(1))
        if obj and _looks_like_scores(obj):
            return obj

    # Last resort: bare JSON with score-like keys (business, innovation, etc.)
    bare_match = re.search(r"(\{[^}]*(?:business|innovation|feasibility|market|team)[^}]*\})", text, re.IGNORECASE)
    if bare_match:
        obj = _try_parse_json(bare_match.group(1))
        if obj and _looks_like_scores(obj):
            return obj

    return None


def _looks_like_scores(obj: dict) -> bool:
    """Check if dict looks like a dimension scores dict (string keys, numeric values)."""
    if not obj or len(obj) < 2:
        return False
    return all(isinstance(v, (int, float)) for v in obj.values())


# ── RUBRIC extraction (R1-R11 simple scores) ──────────────────

_RUBRIC_PATTERNS = [
    # 1. Standard: <!--RUBRIC:{...}-->
    re.compile(r"<!--\s*RUBRIC\s*:\s*(.*?)\s*-->", re.IGNORECASE | re.DOTALL),
    # 2. Unclosed
    re.compile(r"<!--\s*RUBRIC\s*:\s*(\{[^}]*\})", re.IGNORECASE),
    # 3. Malformed close
    re.compile(r"<!--\s*RUBRIC\s*:\s*(\{.*?\})\s*-?-?>?", re.IGNORECASE | re.DOTALL),
]


def parse_rubric(text: str) -> dict | None:
    """Extract RUBRIC JSON (R1-R11 simple scores) from LLM output."""
    for pat in _RUBRIC_PATTERNS:
        m = pat.search(text)
        if m:
            result = _try_parse_json(m.group(1))
            if result and _looks_like_rubric(result):
                return result

    # Fallback: JSON in code fence with R-keys
    fence_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text)
    if fence_match:
        obj = _try_parse_json(fence_match.group(1))
        if obj and _looks_like_rubric(obj):
            return obj

    # Last resort: bare JSON with R1-R11 keys
    bare_match = re.search(r"(\{\s*\"R[0-9]+\"\s*:[\s\S]*?\})", text)
    if bare_match:
        obj = _extract_first_json_object(bare_match.group(0))
        if obj and _looks_like_rubric(obj):
            return obj

    return None


def _looks_like_rubric(obj: dict) -> bool:
    """Check if dict has R1-R11 style keys."""
    if not obj:
        return False
    r_keys = sum(1 for k in obj if re.match(r"^R\d+$", k, re.IGNORECASE))
    return r_keys >= 3


# ── RUBRIC_FULL extraction (R1-R11 with score/evidence/suggestion) ─

_RUBRIC_FULL_PATTERNS = [
    # 1. Standard: <!--RUBRIC_FULL:{...}-->
    re.compile(r"<!--\s*RUBRIC_FULL\s*:\s*([\s\S]*?)\s*-->", re.IGNORECASE),
    # 2. Unclosed with balanced JSON extraction
    re.compile(r"<!--\s*RUBRIC_FULL\s*:\s*(\{[\s\S]*)", re.IGNORECASE),
    # 3. Malformed close variations
    re.compile(r"<!--\s*RUBRIC_FULL\s*:\s*([\s\S]*?)\s*-?-?>", re.IGNORECASE),
]


def parse_rubric_full(text: str) -> dict | None:
    """Extract RUBRIC_FULL JSON (R1-R11 with detail objects) from LLM output."""
    for pat in _RUBRIC_FULL_PATTERNS:
        m = pat.search(text)
        if m:
            raw = m.group(1)
            # For unclosed pattern, extract first balanced JSON object
            result = _extract_first_json_object(raw) if "{" in raw else _try_parse_json(raw)
            if result and _looks_like_rubric_full(result):
                return result

    # Fallback: JSON in code fence
    fence_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if fence_match:
        obj = _extract_first_json_object(fence_match.group(1))
        if obj and _looks_like_rubric_full(obj):
            return obj

    # Last resort: large bare JSON with R-keys and nested objects
    bare_match = re.search(r"(\{\s*\"R[0-9]+\"\s*:\s*\{[\s\S]*)", text)
    if bare_match:
        obj = _extract_first_json_object(bare_match.group(0))
        if obj and _looks_like_rubric_full(obj):
            return obj

    # Ultimate fallback: parse R1-R11 scores from plain-text markdown
    # Matches patterns like "R1: ... Estimated Score 预估得分: 3" or "**预估得分**: 3"
    result = _parse_rubric_from_plaintext(text)
    if result and _looks_like_rubric_full(result):
        return result

    return None


def _parse_rubric_from_plaintext(text: str) -> dict | None:
    """Parse R1-R11 rubric scores from plain-text LLM output when markers are missing."""
    result = {}
    # Split text into sections by R1-R11 headers
    # Match patterns like "R1:", "R1: 痛点定义", "### R1", "**R1**" etc.
    sections = re.split(r"(?=(?:^|\n)[\s#*]*R(\d{1,2})[\s:：*])", text)

    for i, section in enumerate(sections):
        # Find R-number at the start of each section
        r_match = re.match(r"(\d{1,2})", section.strip())
        if not r_match:
            continue
        r_num = int(r_match.group(1))
        if r_num < 1 or r_num > 11:
            continue
        r_key = f"R{r_num}"

        # Get the full section content (current + next part)
        section_text = section
        if i + 1 < len(sections):
            section_text = section + sections[i + 1]

        # Extract score: look for patterns like "预估得分: 3", "Score: 3", "得分：3"
        score_match = re.search(
            r"(?:Estimated\s*Score|预估得分|得分|Score|评分)\s*[:：]\s*(\d)",
            section_text, re.IGNORECASE
        )
        if not score_match:
            continue
        score = int(score_match.group(1))

        # Extract missing evidence
        evidence = ""
        ev_match = re.search(
            r"(?:Missing\s*Evidence|缺失证据|缺少证据)\s*[:：]\s*([\s\S]*?)(?=Minimal\s*Fix|最小修复|24h|$)",
            section_text, re.IGNORECASE
        )
        if ev_match:
            evidence = ev_match.group(1).strip()
            # Clean up markdown formatting
            evidence = re.sub(r"[\n\r]+", " ", evidence)
            evidence = re.sub(r"\s+", " ", evidence).strip()
            if len(evidence) > 200:
                evidence = evidence[:200] + "..."

        # Extract suggestion from Minimal Fix
        suggestion = ""
        fix_match = re.search(
            r"(?:Minimal\s*Fix|最小修复方案|修复方案)\s*[:：]\s*([\s\S]*?)(?=R\d{1,2}[\s:：]|$)",
            section_text, re.IGNORECASE
        )
        if fix_match:
            suggestion = fix_match.group(1).strip()
            suggestion = re.sub(r"[\n\r]+", " ", suggestion)
            suggestion = re.sub(r"\s+", " ", suggestion).strip()
            if len(suggestion) > 200:
                suggestion = suggestion[:200] + "..."

        result[r_key] = {
            "score": score,
            "evidence": evidence or f"详见{r_key}评估内容",
            "suggestion": suggestion or f"请参考{r_key}的修复建议",
        }

    return result if len(result) >= 3 else None


def _looks_like_rubric_full(obj: dict) -> bool:
    """Check if dict has R-keys with nested detail dicts."""
    if not obj:
        return False
    r_keys = [k for k in obj if re.match(r"^R\d+$", k, re.IGNORECASE)]
    if len(r_keys) < 3:
        return False
    # At least some values should be dicts (with score/evidence)
    nested = sum(1 for k in r_keys if isinstance(obj[k], dict))
    return nested >= 2


# ── CAPABILITY_PROFILE extraction ──────────────────────────────

_CAP_PROFILE_PATTERNS = [
    # 1. Standard: <!--CAPABILITY_PROFILE:{...}-->
    re.compile(r"<!--\s*CAPABILITY_PROFILE\s*:\s*([\s\S]*?)\s*-->", re.IGNORECASE),
    # 2. Unclosed
    re.compile(r"<!--\s*CAPABILITY_PROFILE\s*:\s*(\{[\s\S]*)", re.IGNORECASE),
    # 3. Malformed close
    re.compile(r"<!--\s*CAPABILITY_PROFILE\s*:\s*([\s\S]*?)\s*-?-?>", re.IGNORECASE),
]

_CAP_DIMS = {"empathy", "ideation", "business", "execution", "logic", "pitching", "expression"}


def parse_capability_profile(text: str) -> dict | None:
    """Extract CAPABILITY_PROFILE JSON from LLM output."""
    for pat in _CAP_PROFILE_PATTERNS:
        m = pat.search(text)
        if m:
            raw = m.group(1)
            result = _extract_first_json_object(raw) if "{" in raw else _try_parse_json(raw)
            if result and _looks_like_capability_profile(result):
                return result

    # Fallback: JSON in code fence
    fence_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if fence_match:
        obj = _extract_first_json_object(fence_match.group(1))
        if obj and _looks_like_capability_profile(obj):
            return obj

    # Last resort: bare JSON with capability dimension keys
    bare_match = re.search(r"(\{\s*\"(?:empathy|ideation|business|execution|logic)\"\s*:\s*\{[\s\S]*)", text, re.IGNORECASE)
    if bare_match:
        obj = _extract_first_json_object(bare_match.group(0))
        if obj and _looks_like_capability_profile(obj):
            return obj

    return None


def _looks_like_capability_profile(obj: dict) -> bool:
    """Check if dict has capability dimension keys with nested detail dicts."""
    if not obj:
        return False
    dim_keys = sum(1 for k in obj if k.lower() in _CAP_DIMS or k == "overall_comment")
    if dim_keys < 3:
        return False
    nested = sum(1 for k in obj if isinstance(obj[k], dict))
    return nested >= 2


# ── Clean text (remove all markers + leaked JSON) ─────────────

def clean_reply(text: str) -> str:
    """Remove all marker comments and leaked JSON from LLM reply text."""
    # 1. Standard closed markers
    text = re.sub(r"<!--\s*(?:SCORES|RUBRIC_FULL|RUBRIC|CAPABILITY_PROFILE)\s*:[\s\S]*?-->", "", text, flags=re.IGNORECASE)
    # 2. Unclosed markers (take everything after the tag)
    text = re.sub(r"<!--\s*(?:SCORES|RUBRIC_FULL|RUBRIC|CAPABILITY_PROFILE)\s*:[\s\S]*", "", text, flags=re.IGNORECASE)
    # 3. JSON code fences
    text = re.sub(r"```json[\s\S]*?```", "", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 4. Bare JSON with R-keys
    text = re.sub(r"\{\s*[\"']?R[0-9]+[\"']?\s*:[\s\S]*?\}", "", text)
    # 5. Lines with JSON field names
    text = re.sub(r"^\s*[\"']?(?:R[0-9]+|score|evidence|suggestion)[\"']?\s*:\s*.*$", "", text, flags=re.MULTILINE)
    # 6. "详细评分" sections
    text = re.sub(r"(?:详细评分|详细打分|评分详情)[^\n]*[\s\S]*", "", text)
    # 7. Clean up excessive blank lines
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()
