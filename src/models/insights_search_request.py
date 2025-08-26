import re
from dataclasses import dataclass

from src.models.vector_search_request import VectorSearchRequest


@dataclass
class InsightsSearchRequest:
    index: str
    cdsid: str
    ai_summary_cache_id: str
    regions: list
    categories: list
    authors: list
    sorted_by: str
    logged_in_user_name: str
    query: str
    page_no: int
    page_size: int

    @classmethod
    def to_instance(cls, index: str, cdsid: str, logged_in_user_name: str, vector_search_request: VectorSearchRequest):
        key = vector_search_request.ai_summary_cache_id
        author_display_names = vector_search_request.authors
        author_cdsids = []
        for name in author_display_names:
            match = re.search(r'\((.*?)\)', name)
            if match:
                author_cdsids.append(match.group(1))
        return cls(index=index.strip(),
                   cdsid=cdsid.strip().upper(),
                   ai_summary_cache_id=str(key).strip() if key else None,
                   regions=vector_search_request.regions,
                   categories=vector_search_request.categories,
                   authors=author_cdsids,
                   sorted_by=vector_search_request.sorted_by,
                   logged_in_user_name=logged_in_user_name.strip().capitalize(),
                   query=vector_search_request.query.strip(),
                   page_no=int(vector_search_request.page_no),
                   page_size=int(vector_search_request.page_size))
