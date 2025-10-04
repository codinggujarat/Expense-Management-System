from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

class UserRole(Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"

class ExpenseStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class Company:
    id: int
    name: str
    default_currency: str
    created_at: datetime

@dataclass
class User:
    id: int
    name: str
    email: str
    role: UserRole
    company_id: int
    manager_id: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class Expense:
    id: int
    employee_id: int
    company_id: int
    amount: float
    currency: str
    converted_amount: Optional[float]
    category: str
    description: str
    expense_date: datetime
    receipt_path: Optional[str]
    status: ExpenseStatus
    created_at: datetime

@dataclass
class ApprovalWorkflow:
    id: int
    company_id: int
    name: str
    sequence_order: int
    approver_id: int
    is_manager_approver: bool
    percentage_rule: Optional[int]
    specific_approver_rule: bool
    created_at: datetime

@dataclass
class ExpenseApproval:
    id: int
    expense_id: int
    approver_id: int
    sequence_order: int
    status: ApprovalStatus
    comments: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime

# Expense categories
EXPENSE_CATEGORIES = [
    "Travel",
    "Meals & Entertainment",
    "Office Supplies",
    "Transportation",
    "Accommodation",
    "Communication",
    "Training & Education",
    "Software & Subscriptions",
    "Medical",
    "Miscellaneous"
]

# Common currencies
COMMON_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SEK", "NZD",
    "MXN", "SGD", "HKD", "NOK", "INR", "KRW", "TRY", "RUB", "BRL", "ZAR"
]
