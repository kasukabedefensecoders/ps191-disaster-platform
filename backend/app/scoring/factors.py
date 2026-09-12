from .rounding import round_half_up


def build_factor(name: str, weight_pct: int, input_value, fraction: float) -> dict:
    """One row of the factors[] shape required by docs/BACKEND-SCHEMA.md §6.1.

    weight_pct is the prototype's original 0-100 weight (e.g. 28); the
    arithmetic is done and rounded on that same 0-100 scale, matching the
    prototype's own per-factor Math.round-then-sum behaviour exactly, and
    only divided down to the schema's 0-1 range at the end — per
    docs/BUILD-PLAN.md Part 1.2 ("rescale the weights... not the score").
    """
    return {
        "name": name,
        "weight": round(weight_pct / 100, 4),
        "input_value": input_value,
        "contribution": round_half_up(weight_pct * fraction) / 100,
    }
