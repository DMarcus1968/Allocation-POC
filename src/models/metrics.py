"""Normalized metrics schema for allocation comparison."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetricsSummary:
    accounts_fulfilled_pct: float
    tickets_fulfilled: int
    avg_tickets_per_fulfilled_account: float
    singles_stranded_count: int
    inventory_sold_pct: float
    unsold_inventory_count: int
    gross_revenue_fixed_pricebook: float

    def to_dict(self) -> dict:
        return {
            "accounts_fulfilled_pct": self.accounts_fulfilled_pct,
            "tickets_fulfilled": self.tickets_fulfilled,
            "avg_tickets_per_fulfilled_account": self.avg_tickets_per_fulfilled_account,
            "singles_stranded_count": self.singles_stranded_count,
            "inventory_sold_pct": self.inventory_sold_pct,
            "unsold_inventory_count": self.unsold_inventory_count,
            "gross_revenue_fixed_pricebook": self.gross_revenue_fixed_pricebook,
        }
