ALIASES = {
    "respiratory infection": "Respiratory infection",
    "acute respiratory infection": "Respiratory infection",
    "ili": "Influenza-like illness",
    "influenza-like illness": "Influenza-like illness",
    "diabetes": "Diabetes mellitus",
    "gastrointestinal infection": "Gastrointestinal infection",
}


def normalize_disease_name(value: str) -> dict[str, str]:
    """Return a curated deterministic fallback; no WHO prevalence is inferred."""
    normalized = " ".join(value.lower().split())
    return {
        "input": value,
        "normalized": ALIASES.get(normalized, value.strip()),
        "method": "CURATED_FALLBACK",
        "source_status": "UNAVAILABLE",
        "note": "WHO ICD credentials or a cached lookup are required for external terminology resolution.",
    }