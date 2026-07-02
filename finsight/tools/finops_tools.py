"""Custom Python function-tools (math, formatting) not covered by MCP Toolbox."""

from __future__ import annotations


def compute_baseline_forecast(daily_revenues: list[float], projection_days: int) -> dict:
    """Projects expected total revenue for a period using a trailing-average baseline.

    This is a deliberately simple period-over-period baseline (not BigQuery AI.FORECAST /
    TimesFM): average the given historical daily revenues, then multiply by the number of days
    being projected. Use it as the "expected" value to compare against an actual period total.

    Args:
        daily_revenues: Historical daily revenue figures (e.g. from get_daily_sales), any order.
        projection_days: Number of days to project forward -- typically the length of the period
            being evaluated against this baseline.

    Returns:
        A dict with expected_total (float), avg_daily (float), and method (str).
    """
    if not daily_revenues:
        return {"expected_total": 0.0, "avg_daily": 0.0, "method": "trailing_average (no history)"}
    avg_daily = sum(daily_revenues) / len(daily_revenues)
    return {
        "expected_total": round(avg_daily * projection_days, 2),
        "avg_daily": round(avg_daily, 2),
        "method": f"trailing_average({len(daily_revenues)}d)",
    }


def propose_recommendation(recommendation: str, confidence: str) -> dict:
    """Finalizes a FinOps action recommendation for the report.

    This tool is wrapped with require_confirmation=True (see finsight/agents/reporter.py), so it
    never runs silently: the first call always comes back pending human approval, and the report
    must reflect that status rather than presenting the recommendation as already approved.

    Args:
        recommendation: The concrete recommended action.
        confidence: The confidence level backing this recommendation (high/medium/low/
            insufficient evidence).

    Returns:
        A dict confirming the recommendation was approved and logged.
    """
    return {"status": "approved", "recommendation": recommendation, "confidence": confidence}
