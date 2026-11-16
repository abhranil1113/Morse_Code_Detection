import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class CalibrationSave(BaseModel):
    model_config = {"protected_namespaces": ()}
    device_key: str = Field(..., min_length=1, max_length=128)
    calibration_data: Dict[str, Any]
    model_version: Optional[str] = "1.0.0"


class CalibrationResponse(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}
    id: str
    user_id: str
    device_key: str
    calibration_data: Dict[str, Any]
    model_version: Optional[str]
    calibrated_at: datetime

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        return str(v) if v is not None else ""
