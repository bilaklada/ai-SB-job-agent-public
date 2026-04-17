"""
Admin Pydantic Schemas

Response models for admin/debug endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ApplicationRead(BaseModel):
    """Response model for Application."""
    id: int
    job_id: int
    account_id: Optional[int] = None
    applied_at: Optional[datetime] = None
    status: str
    submission_channel: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccountRead(BaseModel):
    """Response model for Account."""
    id: int
    portal_name: str
    domain: str
    login_email: str
    applicant_full_name: str
    account_health: str
    is_active: bool
    created_at: datetime
    verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AIArtifactRead(BaseModel):
    """Response model for AIArtifact."""
    id: int
    job_id: int
    application_id: Optional[int] = None
    artifact_type: str
    content: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# LLM Provider & Model Schemas
# ============================================================================

class LLMProviderBase(BaseModel):
    """Base schema for LLMProvider."""
    llm_provider_name: str


class LLMProviderCreate(LLMProviderBase):
    """Schema for creating a new LLM Provider."""
    pass


class LLMProviderUpdate(BaseModel):
    """Schema for updating an LLM Provider."""
    llm_provider_name: Optional[str] = None


class LLMProviderRead(LLMProviderBase):
    """Response model for LLMProvider."""
    llm_provider_id: int

    class Config:
        from_attributes = True


class LLMModelBase(BaseModel):
    """Base schema for LLMModel."""
    llm_model_name: str
    llm_provider_id: int
    llm_provider_name: str


class LLMModelCreate(BaseModel):
    """Schema for creating a new LLM Model."""
    llm_model_name: str
    llm_provider_id: int


class LLMModelUpdate(BaseModel):
    """Schema for updating an LLM Model."""
    llm_model_name: Optional[str] = None
    llm_provider_id: Optional[int] = None


class LLMModelRead(LLMModelBase):
    """Response model for LLMModel."""
    llm_model_id: int

    class Config:
        from_attributes = True


# ============================================================================
# Settings Schemas
# ============================================================================

class SettingBase(BaseModel):
    """Base schema for Setting."""
    setting_name: str
    setting_value: Dict[str, Any]


class SettingCreate(SettingBase):
    """Schema for creating a new Setting."""
    pass


class SettingUpdate(BaseModel):
    """Schema for updating a Setting."""
    setting_value: Dict[str, Any]


class SettingRead(SettingBase):
    """Response model for Setting."""
    setting_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
