from typing import Annotated, List

from pydantic import BaseModel, Field, conint, constr


class VectorSearchRequest(BaseModel):
    cdsid: Annotated[str, Field(title="The requester's CDSID",
                                description="The requester's CDSID. Example: THAWLEY2",
                                default=...,
                                strict=True,
                                min_length=3,
                                max_length=10000,
                                pattern=r"^[a-zA-Z0-9_-]+$",
                                json_schema_extra={"x-42c-sample": "JHERALD2"})]

    ai_summary_cache_id: Annotated[str, Field(title="AI Summary cache id",
                                              description="AI Summary cache id. Example: 1800000112",
                                              default=None,
                                              pattern=r"^\d{0,20}$",
                                              json_schema_extra={"x-42c-sample": "1800000112"})]

    query: Annotated[str, Field(
        title="User's Query for semantic search",
        description="User's Query for semantic search. Example: Blue cruise",
        default=...,
        strict=True,
        min_length=3,
        max_length=10000,
        pattern=r"([a-zA-Z0-9-._!\"`'#%&,:;<>=@{}~\$\(\)\*\+\/\\\?\[\]\^\|]+|[\.\^\$\*\+\?\{\}\[\]\\\|\(\)])",
        json_schema_extra={"x-42c-sample": "Blue Cruise"})]

    regions: Annotated[List[constr(strip_whitespace=True,
                                   max_length=30000,
                                   pattern=r"^[a-zA-Z0-9_-]+$")], Field(
        title="List of regions",
        description="A list of regions. Example: ['NA', 'EU', 'IMG']",
        default=[],
        max_length=1000,
        json_schema_extra={"x-42c-sample": ["NA", "EU", "IMG"]}
    )]

    categories: Annotated[List[constr(strip_whitespace=True,
                                      max_length=30000,
                                      pattern=r"^[a-zA-Z0-9_-]+$")], Field(
        title="List of categories",
        description="A list of categories. Example: ['Performance', 'Engagement']",
        default=[],
        max_length=1000,
        json_schema_extra={"x-42c-sample": ["Performance", "Engagement"]}
    )]

    authors: Annotated[
        List[
            constr(
                strip_whitespace=True,
                max_length=30000,
                pattern=r"([a-zA-Z0-9-._!\"`'#%&,:;<>=@{}~\$\(\)\*\+\/\\\?\[\]\^\|]+|[\.\^\$\*\+\?\{\}\[\]\\\|\(\)])")],
        Field(title="List of authors",
              description="A list of authors. Example: ['SSUBR104', 'THAWLEY2']",
              default=[],
              max_length=1000,
              json_schema_extra={"x-42c-sample": ["SSUBR104", "THAWLEY2"]}
              )]

    sorted_by: Annotated[str, Field(
        title="Sorted by",
        description="Sorted by. Example: lastUpdatedAsc, lastUpdatedDesc, relevance, mostAccessed",
        default=...,
        strict=True,
        min_length=3,
        max_length=50,
        pattern=r"([a-zA-Z0-9-._!\"`'#%&,:;<>=@{}~\$\(\)\*\+\/\\\?\[\]\^\|]+|[\.\^\$\*\+\?\{\}\[\]\\\|\(\)])",
        json_schema_extra={"x-42c-sample": "relevance"})]

    page_no: Annotated[conint(ge=1, le=10000), Field(title="The page no to be fetched",
                                                     description="The page no to be fetched. Example: 1",
                                                     default=...,
                                                     strict=True,
                                                     json_schema_extra={"x-42c-sample": 1, "minimum": 1,
                                                                        "maximum": 10000,
                                                                        "format": "int32"})]

    page_size: Annotated[conint(ge=24, le=30), Field(title="The page size to be fetched",
                                                     description="The page size to be fetched. Example: 24",
                                                     default=...,
                                                     strict=True,
                                                     json_schema_extra={"x-42c-sample": 24, "minimum": 24,
                                                                        "maximum": 30,
                                                                        "format": "int32"})]

    class Config:
        extra = 'forbid'
        json_schema_extra = {
            "additionalProperties": True
        }
