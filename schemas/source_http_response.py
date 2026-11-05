from typing import Optional

from pydantic import BaseModel, ConfigDict


class SourceHttpResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int
    requested_url: str
    final_url: str
    content_type: Optional[str]
    body: bytes
