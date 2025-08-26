import asyncio
import json
import re
import time
from datetime import datetime, timezone

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk, async_scan

from src.config import ic_logging
from src.constants.es_index_prefix import EsIndexPrefix
from src.constants.sorted_by import SortedBy
from src.constants.summary_reactions import SummaryReactions
from src.constants.sync_options import SyncOptions
from src.exceptions.AppException import InsightException
from src.models.ai_summary_cache_index import ai_summary_cache_index
from src.models.insights_index import insights_index
from src.models.insights_search_request import InsightsSearchRequest
from src.services.ai.embedding_service import VertexTextEmbeddingService


class ElasticService:
    """
    Provides Elasticsearch services for managing and querying insights data.

    This service offers asynchronous methods to interact with Elasticsearch, including checking for index existence,
    searching for insights, indexing documents, and deleting insights or indices. It leverages
    the VertexTextEmbeddingService for generating query vectors for semantic search capabilities.

    Attributes:
        bean_id (str): An identifier for the instance of this class, typically used for logging or debugging purposes.
        async_es (AsyncElasticsearch): An instance of AsyncElasticsearch client for asynchronous operations.
        vertex_text_embedding_service (VertexTextEmbeddingService): A service for generating embeddings used in
        semantic search queries.

    Methods:
        check_index_exists(index_name: str) -> bool:
            Checks asynchronously if a given index exists in Elasticsearch.

        ids_from_search_insights(_request: InsightsSearchRequest) -> dict:
            Retrieves insights based on a search request and returns their IDs and total search count.

        search_insights(_request: InsightsSearchRequest) -> dict:
            Performs a search query in Elasticsearch based on the provided request parameters.

        documents_from_search_insights(_request: InsightsSearchRequest) -> dict:
            Retrieves documents based on a search request, including highlights and total search count.

        find_deleted_insights(insight_records: list, index_name: str) -> set:
            Identifies insights that are present in an index but not in the provided records.

        sync_insights(key: str, insight_records: list, index_name: str, sync_option: str) -> str:
            Synchronizes insights data with Elasticsearch, supporting bulk insert and upsert operations.

        get_total_count(index_name: str) -> int:
            Returns the total count of documents in a given index.

        bulk_index(index_name: str, insight_records: list):
            Performs a bulk indexing operation for the provided records in the specified index.

        delete_insight_by_keys(keys_not_in_source: set, index_name: str):
            Deletes insights by their keys from a specified index.

        delete_insight_by_key(_index_name: str, key: str):
            Deletes a single insight by its key from a specified index.

        get_all_keys(index_name: str) -> list:
            Retrieves all document IDs (keys) from a specified index.

        create_index_if_not_exists(index_name: str):
            Creates an index if it does not already exist, with predefined mappings.

        raise_error_if_index_not_exists(index_name: str):
            Raises an error if a specified index does not exist.

        delete_insights(index_name: str, key: str):
            Deletes insights from a specified index. If a key is provided, deletes the specific insight; otherwise,
            deletes the entire index.

        insert_or_upsert(index_name: str, insight_records: list, sync_option: str):
            Inserts or upserts insights into a specified index based on the sync option.

        get_es_query(_request: InsightsSearchRequest, total_docs: int) -> dict:
            Constructs an Elasticsearch query based on the request parameters and total document count.

    Raises:
        InsightException: If any operation with Elasticsearch fails or returns an error.
    """

    def __init__(self, bean_id, async_es: AsyncElasticsearch,
                 vertex_text_embedding_service: VertexTextEmbeddingService):
        self.bean_id = bean_id
        self.async_es = async_es
        self.vertex_text_embedding_service = vertex_text_embedding_service
        self.search_fields = ["title", "description", "finding", "created_by", "authors", "draft_viewers", "file_path",
                              "file_link", "data_source"]
        self.hash_tag_fields = ["created_by_cdsid", "authors_cdsid", "draft_viewers_cdsid", "platform", "regions",
                                "classifications", "confidentiality"]

    async def check_index_exists(self, index_name):
        """Check if the given index exists in Elasticsearch asynchronously."""
        indices = self.async_es.indices
        exists = await indices.exists(index=index_name)
        return exists

    async def elastic_search(self, _request: InsightsSearchRequest):
        await self.raise_error_if_index_not_exists(_request.index)
        total_docs = await self.get_total_count(_request.index)
        if total_docs > 0:
            if _request.index.startswith(EsIndexPrefix.ai_summary_cache.name):
                es_query = await self.get_ai_summary_cache_query(_request)
            else:
                es_query = await self.get_es_query(_request, total_docs)
            ic_logging.get_logger(__name__).info("es_query: " + json.dumps(es_query, indent=2))
            res = await self.async_es.search(index=_request.index, body=es_query)
            hits = res['hits']['hits']
            total_hits = res['hits']['total']['value']
            result = {
                "hits": hits,
                "total_hits": total_hits
            }
        else:
            result = {}
        return result

    async def get_documents_from_search_insights(self, _request: InsightsSearchRequest):
        result = await self.elastic_search(_request)
        if not result:
            return {}
        hits = result['hits']
        total_search_count = result['total_hits']
        results = []
        for hit in hits:
            result = {"_id": hit['_id'], "_score": hit['_score'], "_source": hit['_source']}
            if 'highlight' in hit:
                result['highlight'] = hit['highlight']
            results.append(result)
        response = {
            "results": results,
            "total_search_count": total_search_count
        }
        return response

    async def find_deleted_insights(self, insight_records, index_name):
        indexed_keys = set(await self.get_all_keys(index_name))
        ic_logging.get_logger(__name__).debug("Total indexed_keys " + str(indexed_keys))
        source_keys = set([record['key'] for record in insight_records])
        ic_logging.get_logger(__name__).debug("Total source_keys " + str(source_keys))
        keys_not_in_source = indexed_keys.difference(source_keys)
        ic_logging.get_logger(__name__).debug("Total keys_not_in_source " + str(keys_not_in_source))
        return keys_not_in_source

    async def sync_insights(self, key, insight_records, index_name, sync_option):
        await self.create_index_if_not_exists(insights_index, index_name)

        if key is None:
            keys_not_in_source = await self.find_deleted_insights(insight_records, index_name)
            if keys_not_in_source:
                await self.delete_insight_by_keys(keys_not_in_source, index_name)

        if sync_option == SyncOptions.bulk_insert.name:
            await self.bulk_index(index_name, insight_records)
        else:
            await self.insert_or_upsert(index_name, insight_records, sync_option)

        return str(await self.get_total_count(index_name))

    async def cache_ai_summaries(self, key, topic: str, user_query: str, ai_summary: str, index_name: str,
                                 cdsid: str, logged_in_user_name: str, regions):
        await self.create_index_if_not_exists(ai_summary_cache_index, index_name)
        if not key:
            key = int(time.time() * 1000)
            ai_summary_cache_document = await self.new_ai_summary_cache_document(key=key, topic=topic,
                                                                                 user_query=user_query,
                                                                                 ai_summary=ai_summary, cdsid=cdsid,
                                                                                 regions=regions)
            ic_logging.get_logger(__name__).info(f"Caching topic ::{ai_summary_cache_document['topic']}")
            es_response = await self.async_es.index(index=index_name, document=ai_summary_cache_document,
                                                    id=str(key))
        else:
            result = await self.get_document_by_id(index_name=index_name, document_id=str(key))
            ai_summary_cache_document = result['_source']
            ic_logging.get_logger(__name__).info(f"Update cached topic ::{ai_summary_cache_document['topic']}")
            ai_summary_cache_document['ai_summary_cache'] = ai_summary
            es_response = await self.update_summary_cache(key=key, index=index_name,
                                                          document=ai_summary_cache_document,
                                                          user_reaction=SummaryReactions.reload.name,
                                                          cdsid=cdsid, logged_in_user_name=logged_in_user_name)

        ic_logging.get_logger(__name__).info("Record cached successfully::" + str(es_response))
        response = await self.get_document_by_id(index_name=index_name, document_id=str(key))
        ai_summary_cache = {
            "summary": response['_source']
        }
        return ai_summary_cache

    async def get_document_by_id(self, index_name: str, document_id: str):
        await self.raise_error_if_index_not_exists(index_name)
        res = await self.async_es.get(index=index_name, id=document_id, source_excludes=["topic_vector"])
        ic_logging.get_logger(__name__).info("Record found successfully::" + str(res))
        return res

    async def update_summary_cache(self, key, index: str, document, user_reaction: str, cdsid: str,
                                   logged_in_user_name: str):
        if user_reaction == SummaryReactions.like.name:
            if cdsid is not None and cdsid not in document["liked_by_cdsids"]:
                document["total_likes"] += 1
                document["liked_by_cdsids"].append(cdsid)
            if cdsid is not None and cdsid in document["disliked_by_cdsids"]:
                document["total_dislikes"] -= 1
                document["disliked_by_cdsids"].remove(cdsid)
            if logged_in_user_name.strip().lower() == document["last_disliked_by"].strip().lower():
                document["last_disliked_by"] = document["disliked_by_cdsids"][-1] if document[
                    "disliked_by_cdsids"] else ""
            document["last_liked_by"] = logged_in_user_name
        elif user_reaction == SummaryReactions.dislike.name:
            if cdsid is not None and cdsid not in document["disliked_by_cdsids"]:
                document["total_dislikes"] += 1
                document["disliked_by_cdsids"].append(cdsid)
            if cdsid is not None and cdsid in document["liked_by_cdsids"]:
                document["total_likes"] -= 1
                document["liked_by_cdsids"].remove(cdsid)
            if logged_in_user_name.strip().lower() == document["last_liked_by"].strip().lower():
                document["last_liked_by"] = document["liked_by_cdsids"][-1] if document["liked_by_cdsids"] else ""
            document["last_disliked_by"] = logged_in_user_name
        elif user_reaction == SummaryReactions.reload.name:
            document["total_likes"] = 0
            document["total_dislikes"] = 0
            document["liked_by_cdsids"] = []
            document["disliked_by_cdsids"] = []
            document["last_liked_by"] = ""
            document["last_disliked_by"] = ""
        else:
            raise InsightException(400, f"Invalid user reaction {user_reaction}.")
        document["updated_by_cdsid"] = cdsid
        document["updated_datetime_utc"] = datetime.now(timezone.utc).isoformat()
        es_response = await self.async_es.update(index=index, id=key, body={"doc": document, "doc_as_upsert": True})
        ic_logging.get_logger(__name__).info("Record updated successfully::" + str(es_response))
        res = await self.get_document_by_id(index_name=index, document_id=str(key))
        return res['_source']

    async def get_total_count(self, index_name):
        es_response = await self.async_es.count(index=index_name)
        es_count = es_response['count']
        ic_logging.get_logger(__name__).debug(f"Total records in index {index_name} are {es_count}.")
        return es_count

    async def bulk_index(self, index_name, insight_records):

        # Prepare bulk update actions
        response = None

        documents = await get_documents(insight_records, index_name)
        # Perform bulk index
        try:
            response = await async_bulk(client=self.async_es, actions=documents, timeout="5m")
        except Exception as e:
            ic_logging.get_logger(__name__).error(f"Error updating index {index_name}. Caused by: {e}.")
            # Print any errors that occurred during indexing
            for item in response[1]:
                if item['update']['status'] != 200:
                    ic_logging.get_logger(__name__).error(item)
            raise InsightException(500, f"Error updating index {index_name}. Caused by: {e}.")

    async def delete_insight_by_keys(self, keys_not_in_source, index_name):
        delete_tasks = [self.delete_insight_by_key(index_name, key) for key in keys_not_in_source]
        await asyncio.gather(*delete_tasks)

    async def delete_insight_by_key(self, _index_name, key):
        await self.async_es.delete(index=_index_name, id=key)
        ic_logging.get_logger(__name__).info(
            f"Record deleted successfully::_index_name={_index_name} :: key {key}")

    async def get_all_keys(self, index_name):
        results = async_scan(self.async_es, index=index_name, query={"query": {"match_all": {}}})
        ids = [result['_id'] async for result in results]
        return list(map(int, ids))

    async def create_index_if_not_exists(self, index, index_name):
        indices = self.async_es.indices
        if not await self.check_index_exists(index_name):
            await indices.create(index=index_name, body=index)
            ic_logging.get_logger(__name__).info(f"Index {index_name} created.")
        else:
            ic_logging.get_logger(__name__).info(f"Index {index_name} already exists.")

    async def raise_error_if_index_not_exists(self, index_name):
        if not await self.check_index_exists(index_name=index_name):
            ic_logging.get_logger(__name__).error(f"Index {index_name} does not exist.")
            raise InsightException(404, f"Index {index_name} does not exist.")
        else:
            ic_logging.get_logger(__name__).info(f"Index {index_name} already exists.")

    async def delete_insights(self, index_name, key):
        await self.raise_error_if_index_not_exists(index_name)
        await self.delete_insight(index_name, key)

    async def delete_insight(self, _index_name, key):
        if key:
            await self.delete_insight_by_key(_index_name, key)
            ic_logging.get_logger(__name__).info("Record deleted successfully::index_name=" + _index_name +
                                                 " ::key=" + str(key))
        else:
            indices = self.async_es.indices
            await indices.delete(index=_index_name)
            ic_logging.get_logger(__name__).info(
                "Index with::index_name=" + _index_name + " deleted successfully.")

    async def insert_or_upsert(self, index_name, insight_records, sync_option):
        for insight_record in insight_records:
            if insight_record is not None:
                if sync_option == SyncOptions.insert.name:
                    ic_logging.get_logger(__name__).info(f"inserting::{insight_record['key']}")
                    es_response = await self.async_es.index(index=index_name, document=insight_record,
                                                            id=insight_record['key'])
                elif sync_option == SyncOptions.upsert.name:
                    ic_logging.get_logger(__name__).info(f"upserting::{insight_record['key']}")
                    es_response = await self.async_es.update(index=index_name, id=insight_record['key'],
                                                             body={"doc": insight_record, "doc_as_upsert": True})
                else:
                    raise InsightException(404, f"Invalid sync option {sync_option}.")
                ic_logging.get_logger(__name__).info("Record inserted successfully::" + str(es_response))
            else:
                ic_logging.get_logger(__name__).error(f"Insight record is None for id: {insight_record}")

    async def get_query_vector(self, query: str):
        ic_logging.get_logger(__name__).info("Before remove special characters in query:: " + query)
        query = re.sub(r'[^a-zA-Z0-9_ ]', '', query)
        ic_logging.get_logger(__name__).info("After remove special characters in query:: " + query)
        query_vector = await self.vertex_text_embedding_service.to_embeddings([query],
                                                                              EmbeddingsTaskType.SEMANTIC_SIMILARITY)
        return query, query_vector

    async def get_es_query(self, _request: InsightsSearchRequest, total_docs: int):
        cdsid = _request.cdsid
        query = _request.query
        hash_tags = await ElasticService.extract_hashtags(query)
        search_fields = self.search_fields
        hash_tag_fields = self.hash_tag_fields
        page_number = _request.page_no
        page_size = _request.page_size
        query, query_vector = await self.get_query_vector(query)

        max_result_window = 10000  # Assuming default Elasticsearch limit
        from_param = (page_number - 1) * page_size

        if from_param + page_size > max_result_window:
            raise InsightException(400, "Requested range exceeds the maximum allowed. "
                                        "Please adjust the page size.")

        if from_param >= total_docs:
            raise InsightException(404, "No more documents to fetch")
        else:
            es_knn_query = await ElasticService.es_knn_query(search_fields=search_fields,
                                                             query=query,
                                                             query_vector=query_vector,
                                                             hash_tags=hash_tags,
                                                             hash_tag_fields=hash_tag_fields,
                                                             _request=_request)
            es_filter_by_user_permission_query = await ElasticService.es_filter_query(cdsid=cdsid)
            filter_by_score_query = await ElasticService.filter_by_score_query()
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            es_knn_query["query"],
                            es_filter_by_user_permission_query["query"]
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "title": {},
                        "description": {}
                    }
                },
                "size": min(page_size, total_docs - from_param),
                "from": from_param,
                "_source": {
                    "excludes": ["title_vector", "description_vector"]
                }
            }
            sorted_by = await ElasticService.sorted_by(_request=_request)
            es_query["sort"] = sorted_by

        return es_query

    async def get_ai_summary_cache_query(self, _request: InsightsSearchRequest):
        query, query_vector = await self.get_query_vector(_request.query)
        return await self.es_search_query(query=query, query_vector=query_vector, num_candidates=5,
                                          regions=_request.regions)

    @staticmethod
    async def extract_hashtags(query):
        words = query.split()
        hashtags = [word[1:] for word in words if word.startswith('#')]
        ic_logging.get_logger(__name__).info("Before remove # Hashtags:: " + str(hashtags))
        hashtags = [re.sub(r'[^a-zA-Z0-9_]', '', hashtag) for hashtag in hashtags]
        ic_logging.get_logger(__name__).info("After special char other than a-zA-Z0-9_ :: " + str(hashtags))
        return hashtags

    @staticmethod
    async def es_search_query(query: str,
                              query_vector: list[float],
                              num_candidates: int,
                              regions):
        es_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match_phrase_prefix": {
                                "topic": {
                                    "query": query
                                }
                            }
                        },
                        {
                            "knn": {
                                "field": "topic_vector",
                                "query_vector": query_vector,
                                "num_candidates": num_candidates,
                                "boost": 1
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "_source": {
                "excludes": ["topic_vector"]
            }
        }
        must_clauses = []
        if regions:
            must_clauses.append({
                "terms": {
                    "regions": regions
                }
            })
            es_query["query"]["bool"]["must"] = must_clauses
        return es_query

    @staticmethod
    async def es_hash_tags_query(hash_tags, hash_tag_fields: list[str]):
        """
            Constructs an Elasticsearch query for searching multiple hashtags.

            Parameters:
            hashtags (list): A list of hashtags to search for.
            fields (list): A list of fields to search the hashtags in.

            Returns:
            dict: An Elasticsearch query.
            """
        should_clauses = await ElasticService.get_queries_for_hash_tags_search(hash_tags=hash_tags,
                                                                               hash_tag_fields=hash_tag_fields)

        es_query = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1
                }
            }
        }

        return es_query

    @staticmethod
    async def get_queries_for_hash_tags_search(hash_tags: list[str], hash_tag_fields: list[str]):
        should_clauses = []
        for hash_tag in hash_tags:
            should_clauses.append({
                "multi_match": {
                    "query": hash_tag,
                    "fields": hash_tag_fields,
                    "type": "phrase",
                    "boost": 15
                }
            })
        return should_clauses

    @staticmethod
    async def sorted_by(_request: InsightsSearchRequest):
        sorted_by = [{"_score": {"order": "desc"}}]
        if _request.sorted_by == SortedBy.lastUpdatedAsc.name:
            sorted_by.append({"updated_datetime": {"order": "asc"}})
        if _request.sorted_by == SortedBy.lastUpdatedDesc.name:
            sorted_by.append({"updated_datetime": {"order": "desc"}})
        ic_logging.get_logger(__name__).info("sorted_by::" + str(sorted_by))
        return sorted_by

    @staticmethod
    async def filter_by_score_query():
        filter_by_score_query = {
            "range": {
                "_score": {
                    "gte": 14
                }
            }
        }
        ic_logging.get_logger(__name__).info("sorted_by::" + str(filter_by_score_query))
        return filter_by_score_query

    @staticmethod
    async def es_cosine_filters_query(_request: InsightsSearchRequest):
        must_clauses = []
        if _request.regions:
            must_clauses.append({
                "terms": {
                    "regions": _request.regions
                }
            })
        if _request.categories:
            must_clauses.append({
                "terms": {
                    "classifications": _request.categories
                }
            })
        if _request.authors:
            must_clauses.append({
                "terms": {
                    "authors_cdsid": _request.authors
                }
            })
        ic_logging.get_logger(__name__).info("must_clauses::" + str(must_clauses))
        return must_clauses

    @staticmethod
    async def es_knn_query(search_fields: list[str],
                           query: str,
                           query_vector: list[float],
                           hash_tags: list[str],
                           hash_tag_fields: list[str],
                           _request: InsightsSearchRequest):
        es_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": search_fields,
                                "type": "best_fields",
                                "boost": 10
                            }
                        },
                        {
                            "knn": {
                                "field": "title_vector",
                                "query_vector": query_vector,
                                "num_candidates": 5
                            }
                        },
                        {
                            "knn": {
                                "field": "description_vector",
                                "query_vector": query_vector,
                                "num_candidates": 5
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        if _request.regions or _request.categories or _request.authors:
            must_clauses = await ElasticService.es_cosine_filters_query(_request=_request)
            es_query["query"]["bool"]["must"] = must_clauses
        if hash_tags:
            es_hash_tags_query = await ElasticService.es_hash_tags_query(hash_tags=hash_tags,
                                                                         hash_tag_fields=hash_tag_fields)
            es_query["query"]["bool"]["should"].append(es_hash_tags_query["query"])
        return es_query

    @staticmethod
    async def es_cosine_query_deprecated(search_fields: list[str],
                                         query: str,
                                         query_vector: list[float],
                                         hash_tags: list[str],
                                         hash_tag_fields: list[str],
                                         _request: InsightsSearchRequest):
        es_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": """
                                            double titleScore = cosineSimilarity(params.query_vector, 'title_vector') 
                                            + 1.0;
                                            double descriptionScore = cosineSimilarity(params.query_vector, 
                                            'description_vector') + 1.0;
                                            return titleScore + descriptionScore;
                                            """,
                                    "params": {
                                        "query_vector": query_vector
                                    }
                                }
                            }
                        },
                        {
                            "multi_match": {
                                "query": query,
                                "fields": search_fields,
                                "type": "best_fields",
                                "boost": 10
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        if _request.regions or _request.categories or _request.authors:
            must_clauses = await ElasticService.es_cosine_filters_query(_request=_request)
            es_query["query"]["bool"]["must"].extend(must_clauses)
        if hash_tags:
            es_hash_tags_query = await ElasticService.es_hash_tags_query(hash_tags=hash_tags,
                                                                         hash_tag_fields=hash_tag_fields)
            es_query["query"]["bool"]["should"].append(es_hash_tags_query["query"])
        return es_query

    async def new_ai_summary_cache_document(self, key: int, topic: str, user_query: str, ai_summary: str, cdsid: str,
                                            regions):
        """
        Creates a document for the AI summary cache.

        This function creates a document for the AI summary cache using the provided parameters.

        Parameters:
        topic (str): The topic of the AI summary.
        user_query (str): The user query for which the AI summary was generated.
        ai_summary (str): The AI summary generated for the user query.
        cdsid (str): The CDSID of the user who generated the AI summary.
        user_name (str): The name of the user who generated the AI summary.

        Returns:
        dict: A dictionary containing the AI summary cache document.
        """
        topic, topic_vector = await self.get_query_vector(topic)
        return {
            "key": key,
            "topic": topic,
            "user_query": user_query,
            "ai_summary_cache": ai_summary,
            "regions": regions,
            "total_likes": 0,
            "total_dislikes": 0,
            "liked_by_cdsids": [],
            "disliked_by_cdsids": [],
            "last_liked_by": "",
            "last_disliked_by": "",
            "updated_by_cdsid": cdsid,
            "updated_datetime_utc": datetime.now(timezone.utc).isoformat(),
            "topic_vector": topic_vector
        }

    @staticmethod
    async def es_filter_query(cdsid: str):
        es_filter_by_user_permission_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "term": {
                                "is_draft": {
                                    "value": False
                                }
                            }
                        },
                        {
                            "bool": {
                                "must": [
                                    {
                                        "term": {
                                            "is_draft": {
                                                "value": True
                                            }
                                        }
                                    },
                                    {
                                        "bool": {
                                            "should": [
                                                {
                                                    "term": {
                                                        "authors_cdsid": cdsid
                                                    }
                                                },
                                                {
                                                    "term": {
                                                        "draft_viewers_cdsid": cdsid
                                                    }
                                                },
                                                {
                                                    "term": {
                                                        "created_by_cdsid": cdsid
                                                    }
                                                }
                                            ],
                                            "minimum_should_match": 1
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        return es_filter_by_user_permission_query


async def get_documents(insight_records, index_name):
    documents = []
    for insight_record in insight_records:
        if insight_record is not None and insight_record["key"] is not None:
            document = {
                "_op_type": "index",  # Specify the operation type for bulk API
                "_index": index_name,  # Specify the index name
                "_id": insight_record["key"],  # Use the record's key as the document ID
                "_source": insight_record  # The actual data to be indexed
            }
            documents.append(document)
    return documents
