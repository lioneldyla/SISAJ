"""Shared constraints for manual entry and imported case headers."""
from datetime import date
from pydantic import BaseModel, ConfigDict, Field


class CaseIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    rp_number: str = Field(min_length=1, max_length=100)
    rp_year: int = Field(ge=1900, le=2200)
    date_rp: date
    provenance: str = Field(min_length=1, max_length=250)
    transnational: bool | None
    category: str = Field(min_length=1, max_length=250)
    ri_number: str | None = None
    person_physical_count: int | None = Field(default=None, ge=0, le=2147483647)
    person_legal_count: int | None = Field(default=None, ge=0, le=2147483647)
