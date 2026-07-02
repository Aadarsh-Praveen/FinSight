"""Pydantic schemas for structured hand-offs between orchestrator sub-agents.

Each schema is one node's `output_schema`, saved to session state via `output_key`. Downstream
agents reference the prior state (e.g. `{plan}`, `{analyst_findings}`) in their instructions,
rather than parsing free-form prose from earlier turns.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    start_date: str = Field(description="YYYY-MM-DD, inclusive.")
    end_date: str = Field(description="YYYY-MM-DD, inclusive.")


class InvestigationPlan(BaseModel):
    question: str = Field(description="The original user question, verbatim.")
    current_period: DateRange
    prior_period: DateRange = Field(
        description="Same length as current_period, ending immediately before it starts."
    )
    reasoning: str = Field(description="Why these dates were chosen, grounded in dataset coverage.")


class PeriodFigures(BaseModel):
    revenue: float
    order_count: int


class AnalystFindings(BaseModel):
    current: PeriodFigures
    prior: PeriodFigures
    delta_revenue: float = Field(description="current.revenue - prior.revenue")
    delta_pct: float = Field(description="delta_revenue / prior.revenue * 100, rounded to 2 dp.")


class ForecastResult(BaseModel):
    expected_current_revenue: float = Field(
        description="Baseline projection for the current period from the trailing-average method."
    )
    actual_current_revenue: float
    surprise: float = Field(description="actual_current_revenue - expected_current_revenue")
    surprise_pct: float = Field(description="surprise / expected_current_revenue * 100.")
    method: str = Field(description="How the baseline was computed, e.g. 'trailing_average(30d)'.")


class CategoryDelta(BaseModel):
    category: str
    current_revenue: float
    prior_revenue: float
    delta_revenue: float


class DriverFinding(BaseModel):
    dimension: str = Field(description="What dimension was analyzed, e.g. 'category'.")
    top_driver: str = Field(
        description="The single category/segment contributing most to the delta."
    )
    top_driver_delta: float = Field(description="That driver's own delta_revenue.")
    share_of_total_delta_pct: float = Field(
        description="top_driver_delta / analyst_findings.delta_revenue * 100."
    )
    breakdown: list[CategoryDelta] = Field(
        description="All categories, sorted by |delta| descending."
    )


class FinOpsReport(BaseModel):
    summary: str = Field(description="1-2 sentence direct answer to the original question.")
    root_cause: str = Field(
        description="The likely driver and why, or 'insufficient evidence' if the top driver "
        "doesn't plausibly explain most of the delta."
    )
    evidence: list[str] = Field(description="Concrete cited figures pulled from prior agent state.")
    recommendation: str = Field(description="One concrete, actionable next step.")
    confidence: str = Field(description="One of: high, medium, low, insufficient evidence.")
