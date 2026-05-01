"""Token budget tracker. Halts the autopilot when monthly budget is exhausted."""

from __future__ import annotations

from dataclasses import dataclass

from etzchaim.autopilot.config import AutopilotConfig
from etzchaim.autopilot.state import AutopilotState


@dataclass
class BudgetCheck:
    allowed: bool
    consumed: int
    limit: int
    remaining: int


class TokenBudget:
    """Reads/writes monthly token consumption from the autopilot state."""

    def __init__(self, config: AutopilotConfig, state: AutopilotState) -> None:
        self.config = config
        self.state = state
        self.state.reset_monthly_budget_if_needed()

    def consume(self, tokens: int) -> BudgetCheck:
        """Record `tokens` consumption and return a fresh allowance check."""
        if tokens > 0:
            self.state.autopilot_tokens_consumed_month += tokens
            self.state.save()
        return self.check()

    def check(self) -> BudgetCheck:
        consumed = self.state.autopilot_tokens_consumed_month
        limit = self.config.budget_tokens_monthly
        remaining = max(limit - consumed, 0)
        return BudgetCheck(
            allowed=consumed < limit,
            consumed=consumed,
            limit=limit,
            remaining=remaining,
        )
