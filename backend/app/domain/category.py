from __future__ import annotations

from enum import StrEnum


class BudgetBucket(StrEnum):
    NEEDS = "needs"
    WANTS = "wants"
    SAVINGS = "savings"
    DEBT = "debt"
    UNKNOWN = "unknown"


class Category(StrEnum):
    GROCERIES = "groceries"
    RESTAURANTS = "restaurants"
    TRANSPORT = "transport"
    AUTO = "auto"
    HOUSEHOLD = "household"
    HEALTH = "health"
    PERSONAL_CARE = "personal_care"
    ENTERTAINMENT = "entertainment"
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    TOOLS = "tools"
    FEES = "fees"
    TAX = "tax"
    DISCOUNT = "discount"
    OTHER = "other"
    UNKNOWN = "unknown"


DEFAULT_CATEGORY_BUCKETS: dict[Category, BudgetBucket] = {
    Category.GROCERIES: BudgetBucket.NEEDS,
    Category.RESTAURANTS: BudgetBucket.WANTS,
    Category.TRANSPORT: BudgetBucket.NEEDS,
    Category.AUTO: BudgetBucket.NEEDS,
    Category.HOUSEHOLD: BudgetBucket.NEEDS,
    Category.HEALTH: BudgetBucket.NEEDS,
    Category.PERSONAL_CARE: BudgetBucket.NEEDS,
    Category.ENTERTAINMENT: BudgetBucket.WANTS,
    Category.CLOTHING: BudgetBucket.WANTS,
    Category.ELECTRONICS: BudgetBucket.WANTS,
    Category.TOOLS: BudgetBucket.WANTS,
    Category.FEES: BudgetBucket.NEEDS,
    Category.TAX: BudgetBucket.NEEDS,
    Category.DISCOUNT: BudgetBucket.UNKNOWN,
    Category.OTHER: BudgetBucket.UNKNOWN,
    Category.UNKNOWN: BudgetBucket.UNKNOWN,
}


def default_bucket_for_category(category: Category) -> BudgetBucket:
    return DEFAULT_CATEGORY_BUCKETS.get(category, BudgetBucket.UNKNOWN)
