from typing import Annotated
from pydantic import BaseModel, Field


class TalkInsightsRequest(BaseModel):
    gcs_path: Annotated[str, Field(
        title="GCS Path",
        description="Path to the GCS file. Example: gs://bkt-aim-files-dev/1800000111/Learning KO rep for control with AE.pdf",
        min_length=3,
        max_length=10000,
        pattern=r"^gs://[\S ]+/[0-9]{8,11}/[\S ]+\.[\S ]+$",
        json_schema_extra={"x-42c-sample": "gs://bkt-aim-files-dev/1800000111/Learning KO rep for control with AE.pdf"}
    )]
    user_question: Annotated[str, Field(
        title="User Question",
        description="User's question about the document. Example: What could be the title for this document",
        min_length=3,
        max_length=10000,
        pattern=".*",
        json_schema_extra={"x-42c-sample": "What could be the title for this document"}
    )]

    class Config:
        extra = 'forbid'
        json_schema_extra = {
            "additionalProperties": False
        }
