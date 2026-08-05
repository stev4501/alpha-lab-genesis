"""Passive SPY baseline for the sealed daily-bar evaluator."""


def target_weights(history, as_of):
    if "SPY" not in history or not history["SPY"]:
        return {}
    return {"SPY": 1.0}
