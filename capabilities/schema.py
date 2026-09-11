from typing import List, Optional
from pydantic import BaseModel


class LocatorStrategy(BaseModel):
    type: str
    role: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None


class Target(BaseModel):
    strategies: List[LocatorStrategy]


class Step(BaseModel):
    action: str
    target: Target
    value: Optional[str] = None
    output: Optional[str] = None


class Checkpoint(BaseModel):
    type: str
    value: str


class Capability(BaseModel):
    name: str
    version: str
    input: dict
    steps: List[Step]
    output: dict
    checkpoint: Checkpoint