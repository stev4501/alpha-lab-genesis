"""Passive SPY baseline with an explicit warm-up contract."""

STRATEGY_ID = "S-0002"
WARMUP_SESSIONS = 1


def target_weights(history, as_of):
    if not history:
        return {}
    return {"SPY": 1.0}
