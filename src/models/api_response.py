from typing import Annotated, Any, Dict

from pydantic import Field, conint, BaseModel


class ApiResponse(BaseModel):
    status_code: Annotated[conint(ge=1, le=1000), Field(title="The response status code",
                                                        description="The response status code. Example: 200",
                                                        default=...,
                                                        strict=True,
                                                        json_schema_extra={"format": "int32"})]
    message: Annotated[str, Field(title="The message",
                                  description="The message",
                                  default=...,
                                  strict=True,
                                  min_length=3,
                                  max_length=10000,
                                  pattern=r"([a-zA-Z0-9-._!\"`'#%&,:;<>=@{}~\$\(\)\*\+\/\\\?\[\]\^\|]+|[\.\^\$\*\+\?\{\}\[\]\\\|\(\)])")]

    data: Annotated[Dict[str, Any], Field(title="The response data",
                                          description="The response data",
                                          default_factory=dict,
                                          json_schema_extra={"additionalProperties": True})]

    class Config:
        extra = 'forbid'
        json_schema_extra = {
            "additionalProperties": False
        }
