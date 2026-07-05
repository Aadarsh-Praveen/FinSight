"""Custom Python function-tools (math, formatting) not covered by MCP Toolbox."""

from __future__ import annotations

import datetime
import logging

from finsight.guardrails.injection_guard import scan_for_injection
from finsight.guardrails.pii_redaction import EMAIL_PATTERN

logger = logging.getLogger("finsight.tools.finops_tools")


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


def compute_timesfm_forecast(daily_series: list[dict], projection_days: int) -> dict:
    """Projects expected total revenue using BigQuery's AI.FORECAST function (the built-in,
    pre-trained TimesFM model), with an automatic fallback to the deterministic trailing-average
    baseline (compute_baseline_forecast) if AI.FORECAST errors, times out, or the series is
    unusable -- the agent always gets a usable forecast back, never a failed tool call.

    Verified live before this was built (see PROGRESS.md): a ~30-point daily series returns a
    sane, non-degenerate forecast whose 90% interval actually contained the real subsequent
    outcome in testing -- and the interval width reflects genuine data volatility this dataset
    has, not a model artifact. The interval surfaces uncertainty the deterministic baseline
    hides entirely.

    Security note: `horizon` is a validated, clamped int, never raw agent-supplied text --
    AI.FORECAST's own named arguments (horizon, confidence_level) must be SQL literals, not bound
    query parameters (a real restriction of the function itself, confirmed by testing). The
    actual time-series data (dates, revenues) -- the part that matters for injection safety --
    is fully parameterized via bigquery.ArrayQueryParameter, never string-interpolated.

    Args:
        daily_series: Historical daily revenue with dates, e.g. from get_daily_sales -- list of
            {"date": "YYYY-MM-DD", "revenue": float} (also accepts the raw MCP Toolbox key name
            "order_date" in place of "date").
        projection_days: Number of days to project forward.

    Returns:
        A dict with expected_total (float), avg_daily (float), and method (str) -- identical
        shape to compute_baseline_forecast's return, so the calling agent's downstream handling
        doesn't need to know which path was taken.
    """
    revenues = [float(d["revenue"]) for d in daily_series]
    horizon = max(1, min(int(projection_days), 90))

    try:
        dates = [
            datetime.date.fromisoformat(str(d.get("date") or d["order_date"]))
            for d in daily_series
        ]
        from google.cloud import bigquery

        from finsight.config import settings

        client = bigquery.Client(project=settings.bigquery_project)
        query = f"""
        SELECT * FROM AI.FORECAST(
          (
            SELECT day, revenue
            FROM UNNEST(@dates) AS day WITH OFFSET pos
            JOIN UNNEST(@revenues) AS revenue WITH OFFSET pos
            USING(pos)
          ),
          data_col => 'revenue',
          timestamp_col => 'day',
          horizon => {horizon},
          confidence_level => 0.9
        )
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("dates", "DATE", dates),
                bigquery.ArrayQueryParameter("revenues", "FLOAT64", revenues),
            ]
        )
        rows = list(client.query(query, job_config=job_config).result(timeout=30))
        if not rows:
            raise RuntimeError("AI.FORECAST returned no rows")

        expected_total = sum(r["forecast_value"] for r in rows)
        lower_total = sum(r["prediction_interval_lower_bound"] for r in rows)
        upper_total = sum(r["prediction_interval_upper_bound"] for r in rows)
        return {
            "expected_total": round(expected_total, 2),
            "avg_daily": round(expected_total / len(rows), 2),
            "method": (
                f"AI.FORECAST (TimesFM), 90% CI [{round(lower_total, 2)}, "
                f"{round(upper_total, 2)}]"
            ),
        }
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never fail the investigation
        logger.warning("AI.FORECAST unavailable, falling back to baseline: %s", exc)
        fallback = compute_baseline_forecast(revenues, projection_days)
        fallback["method"] = f"{fallback['method']} [AI.FORECAST fallback: {type(exc).__name__}]"
        return fallback


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


def check_text_for_policy_violations(text: str) -> dict:
    """Deterministically scans text for PII leakage and prompt-injection patterns.

    Used by the verifier agent as a policy check on the draft report, rather than relying on
    LLM judgment alone -- reuses the same regexes as the pii_redaction and injection_guard
    guardrail callbacks (finsight/guardrails/), so the standard is identical.

    Args:
        text: The text to scan, e.g. the report's summary + root_cause + recommendation.

    Returns:
        A dict with pii_found (bool) and injection_found (bool).
    """
    return {
        "pii_found": bool(EMAIL_PATTERN.search(text)),
        "injection_found": scan_for_injection(text) is not None,
    }
