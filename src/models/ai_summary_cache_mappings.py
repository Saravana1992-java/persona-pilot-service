ai_summary_cache_mappings = {
    "properties": {
        "key": {
            "type": "long"
        },
        "topic": {
            "type": "text",
            "index": True
        },
        "user_query": {
            "type": "text",
            "index": True
        },
        "ai_summary_cache": {
            "type": "text",
            "index": True
        },
        "regions": {
            "type": "keyword",
            "normalizer": "case_insensitive_analyzer",
            "index": True
        },
        "total_likes": {
            "type": "long",
            "index": True
        },
        "total_dislikes": {
            "type": "long",
            "index": True
        },
        "liked_by_cdsids": {
            "type": "keyword",
            "normalizer": "case_insensitive_analyzer",
            "index": True
        },
        "disliked_by_cdsids": {
            "type": "keyword",
            "normalizer": "case_insensitive_analyzer",
            "index": True
        },
        "last_liked_by": {
            "type": "keyword",
            "normalizer": "case_insensitive_analyzer",
            "index": True
        },
        "last_disliked_by": {
            "type": "keyword",
            "normalizer": "case_insensitive_analyzer",
            "index": True
        },
        "updated_by_cdsid": {
            "type": "keyword",
            "normalizer": "case_insensitive_analyzer"
        },
        "updated_datetime_utc": {
            "type": "text"
        },
        "topic_vector": {
            "type": "dense_vector",
            "dims": 256,
            "index": True
        }
    }
}
