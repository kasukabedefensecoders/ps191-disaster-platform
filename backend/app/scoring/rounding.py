import math


def round_half_up(x: float) -> int:
    """Match JavaScript's Math.round, which always rounds .5 up.

    Python's builtin round() uses banker's rounding (ties to even), which
    silently disagrees with the prototype on several of its own seeded
    households — e.g. HH-107's "Children under 12" factor is exactly
    18 * 0.25 = 4.5, which Math.round takes to 5 but Python's round() takes
    to 4. Every prototype-ported score uses this instead of round() so the
    port reproduces the prototype's own numbers exactly, not approximately.
    Only ever called with non-negative x here, so floor(x + 0.5) is enough
    (it would diverge from Math.round's away-from-zero behaviour for
    negative inputs, but no factor weight or normalized value is negative).
    """
    return math.floor(x + 0.5)
