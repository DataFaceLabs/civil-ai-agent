"""Fact-echo and post-render validation (Phase 2).

Phrase lists marked "sync with eval-harness/review_batch.py" must be kept aligned manually.
"""

from __future__ import annotations

import re

from civilai_agent.guardrails.structured import SectionDraftOutput
from civilai_agent.pipeline.specs import DraftSpec

# sync with eval-harness/review_batch.py — genuine no-zoning denials only.
NO_ZONING_PHRASES = (
    "no zoning applies",
    "no zoning regulations apply",
    "no zoning classification applies",
    "zoning does not apply",
    "not subject to zoning",
    "no municipal zoning applies",
    "counties do not have zoning",
    "non-zoning county",
    "is not zoned",
    "property is not zoned",
)

SFHA_FLOOD_ZONES = frozenset({"A", "AE", "AO", "AH", "VE"})

NOT_IN_FLOODPLAIN_PHRASES = (
    "not in the 100-year floodplain",
    "is not in the 100-year floodplain",
    "lies outside the 100-year floodplain",
    "outside the special flood hazard area",
    "not in a special flood hazard area",
    "not in the sfha",
    "outside the sfha",
)

IN_FLOODPLAIN_PHRASES = (
    "is in the 100-year floodplain",
    "lies within the 100-year floodplain",
    "within the 100-year floodplain",
    "in the special flood hazard area",
    "within the sfha",
    "in the sfha",
)

OUTSIDE_EDWARDS_PHRASES = (
    "outside the edwards aquifer",
    "outside edwards aquifer",
    "no additional permits are required for development activities related to the edwards",
    "no tceq edwards aquifer",
)

_AVAILABILITY_RE = re.compile(
    r"\b(water|wastewater)\s+(service\s+)?is\s+available\b",
    re.IGNORECASE,
)

_COVERAGE_QUALIFIERS = (
    "coverage",
    "territory",
    "service area",
    "service-area",
    "ccn",
    "boundary",
    "boundaries",
    "does not confirm",
    "do not confirm",
    "not confirmed",
    "not establish",
    "does not establish",
    "obtain",
    "verify",
    "letter",
    "pending",
    "could serve",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _draft_blob(output: SectionDraftOutput) -> str:
    return "\n".join(
        [output.suggested_language, *output.caveats, *output.verification_steps]
    ).lower()


def _slot_value(spec: DraftSpec, key: str) -> str | None:
    val = spec.slots.get(key)
    if val is None or not str(val).strip():
        return None
    text = str(val).strip()
    if text.lower() in ("null", "none"):
        return None
    return text


def _has_capacity_fact(spec: DraftSpec) -> bool:
    for source in (spec.slots, spec.facts):
        for key in ("capacity_confirmed", "utility_capacity", "confirmed_capacity"):
            val = source.get(key)
            if val is True:
                return True
            if isinstance(val, str) and val.strip().lower() in ("true", "yes", "1"):
                return True
        flags = source.get("capacity_flags")
        if isinstance(flags, dict) and any(flags.values()):
            return True
        if isinstance(flags, str) and flags.strip().lower() not in ("", "null", "none", "{}"):
            return True
    return False


def _zoning_fact_echo_warning(spec: DraftSpec, text: str) -> str | None:
    zoning_code = _slot_value(spec, "zoning_code")
    if zoning_code is None:
        return None
    if any(phrase in text for phrase in NO_ZONING_PHRASES):
        return (
            f"Draft denies zoning applicability while spec.slots['zoning_code'] is {zoning_code!r}."
        )
    return None


def _normalize_flood_zone(zone: str) -> str:
    return zone.strip().upper().split()[0]


def _flood_fact_echo_warning(spec: DraftSpec, text: str) -> str | None:
    flood_zone = _slot_value(spec, "flood_zone")
    if flood_zone is None:
        return None
    zone = _normalize_flood_zone(flood_zone)
    in_sfha = zone in SFHA_FLOOD_ZONES
    asserts_not = any(phrase in text for phrase in NOT_IN_FLOODPLAIN_PHRASES)
    asserts_in = any(phrase in text for phrase in IN_FLOODPLAIN_PHRASES)
    if in_sfha and asserts_not:
        return (
            f"Draft asserts outside the 100-year floodplain while "
            f"spec.slots['flood_zone'] is {flood_zone!r} (SFHA)."
        )
    if not in_sfha and asserts_in:
        return (
            f"Draft asserts inside the 100-year floodplain while "
            f"spec.slots['flood_zone'] is {flood_zone!r} (non-SFHA)."
        )
    return None


_OSSF_NOT_REQUIRED_PHRASES = (
    "not required to install an on-site sewage facility",
    "not required to install an ossf",
    "ossf is not required",
    "no ossf is required",
    "on-site sewage facility (ossf) are not required",
)

_AUSTIN_ENERGY_PHRASES = ("austin energy",)


def _utilities_fact_echo_warning(spec: DraftSpec, text: str) -> str | None:
    branch = spec.branch_id or ""
    if branch in ("utilities.ossf", "utilities.provider_distant") and any(
        phrase in text for phrase in _OSSF_NOT_REQUIRED_PHRASES
    ):
        return f"Draft denies OSSF requirement while dispatch branch is {branch!r}."
    for slot_key, phrases in (
        ("power_provider", _AUSTIN_ENERGY_PHRASES),
        ("water_provider", ()),
        ("wastewater_provider", ()),
    ):
        slot_val = _slot_value(spec, slot_key)
        if (
            slot_val is None
            and slot_key == "power_provider"
            and any(phrase in text for phrase in phrases)
        ):
            return (
                "Draft names Austin Energy but spec.slots['power_provider'] is unset "
                "(CCN not confirmed)."
            )
    if _has_capacity_fact(spec):
        return None
    for sentence in _SENTENCE_SPLIT.split(text):
        if not _AVAILABILITY_RE.search(sentence):
            continue
        lowered = sentence.lower()
        if any(marker in lowered for marker in _COVERAGE_QUALIFIERS):
            continue
        return (
            "Draft asserts water/wastewater availability without a coverage qualifier "
            "and spec has no confirmed capacity fact."
        )
    return None


def _environmental_fact_echo_warning(spec: DraftSpec, text: str) -> str | None:
    branch = spec.branch_id or ""
    if branch == "environmental.edwards_outside":
        return None
    if any(phrase in text for phrase in OUTSIDE_EDWARDS_PHRASES):
        return (
            "Draft asserts outside the Edwards Aquifer but dispatch branch is "
            f"{branch!r} (definitive outside requires TCEQ overlay confirmation)."
        )
    return None


def fact_echo_warnings(spec: DraftSpec, output: SectionDraftOutput) -> tuple[str, ...]:
    """Negation-safe checks that draft prose contradicts governed spec slots."""
    text = _draft_blob(output)
    warnings: list[str] = []

    checkers = {
        "zoning": _zoning_fact_echo_warning,
        "environmental": _environmental_fact_echo_warning,
        "flood": _flood_fact_echo_warning,
        "utilities": _utilities_fact_echo_warning,
    }
    checker = checkers.get(spec.section_id)
    if checker is not None:
        msg = checker(spec, text)
        if msg:
            warnings.append(msg)

    return tuple(warnings)
