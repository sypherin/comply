from __future__ import annotations
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
import pandas as pd

REQUIRED_HEADERS = [
    "Learner", "First Name", "Last Name", "Email Address", "Manager Email",
    "Course Title", "Completion Status", "Required Date", "Org", "BU", "Department"
]

STATUS_MAP = {
    "complete": "Completed",
    "completed": "Completed",
    "done": "Completed",
    "in progress": "In Progress",
    "not started": "Not Started",
    "incomplete": "Not Started",
}

def normalize_status_values(v: str) -> str:
    if not isinstance(v, str):
        return "Not Started"
    key = v.strip().lower()
    return STATUS_MAP.get(key, v.strip())

def validate_headers(headers: List[str]):
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

class UserPrincipal(BaseModel):
    name: str
    email: EmailStr
    oid: str

class UploadRow(BaseModel):
    Learner: str
    First_Name: str
    Last_Name: str
    Email_Address: EmailStr
    Manager_Email: Optional[EmailStr] = None
    Course_Title: str
    Completion_Status: str
    Required_Date: Optional[str] = None
    Org: str
    BU: str
    Department: str

    @field_validator("Completion_Status")
    @classmethod
    def norm_status(cls, v):
        return normalize_status_values(v)

class ReminderLog(BaseModel):
    recipient: EmailStr
    cc: Optional[list[EmailStr]] = []
    course_count: int
    status: str
    message_id: Optional[str] = None

class DatasetMeta(BaseModel):
    row_count: int
    uploaded_by: EmailStr
    uploaded_at: str
