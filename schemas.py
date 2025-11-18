"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Task management schemas

class Task(BaseModel):
    """
    Tasks collection schema
    Collection name: "task"
    """
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Details about the task")
    priority: int = Field(3, ge=1, le=5, description="Priority from 1 (lowest) to 5 (highest)")
    estimated_duration_minutes: int = Field(30, ge=5, le=8*60, description="Estimated time needed in minutes")
    due_at: Optional[datetime] = Field(None, description="Due date/time (ISO8601)")
    status: Literal["todo", "in_progress", "done"] = Field("todo")
    tags: List[str] = Field(default_factory=list)

class ScheduleBlock(BaseModel):
    title: str
    task_id: Optional[str] = None
    start: datetime
    end: datetime
    description: Optional[str] = None

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
