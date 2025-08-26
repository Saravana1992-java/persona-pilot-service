insights_mappings = {
    "properties": {
        "key": {
            "type": "long"
        },
        "name": {
            "type": "text",
            "index": True
        },
        "preferred_role": {
            "type": "text",
            "index": True
        },
        "publication_date": {
            "type": "text",
        },
        "created_by": {
            "type": "text",
            "index": True
        },
        "created_datetime": {
            "type": "date",
            "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd HH:mm:ss.SSSSSS||yyyy-MM-dd'T'HH:mm:ss.SSSSSS||epoch_millis"
        },
        "updated_by": {
            "type": "text",
            "index": True
        },
        "updated_datetime": {
            "type": "date",
            "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd HH:mm:ss.SSSSSS||yyyy-MM-dd'T'HH:mm:ss.SSSSSS||epoch_millis"
        },
        "authors": {
            "type": "text",
            "index": True
        },
        "regions": {
            "type": "keyword",
            "normalizer": "case_insensitive_analyzer",
            "index": True
        },
        "keywords": {
            "type": "keyword",
            "normalizer": "case_insensitive_analyzer"
        },
        "file_link": {
            "type": "text",
            "index": True
        },
        "description_vector": {
            "type": "dense_vector",
            "dims": 256,
            "index": True
        },
        "title_vector": {
            "type": "dense_vector",
            "dims": 256,
            "index": True
        }
    }
}
