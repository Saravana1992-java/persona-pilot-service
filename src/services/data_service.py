import re
from typing import Any

from elasticsearch import NotFoundError

from src.config import ic_logging, properties
from src.constants.es_index_prefix import EsIndexPrefix
from src.constants.job_statuses import JobStatus
from src.exceptions.AppException import AppException
from src.handlers.async_job_handler import AsyncJobHandler
from src.models.insights import Insights
from src.models.insights_search_request import InsightsSearchRequest
from src.services.ai.embedding_service import VertexTextEmbeddingService
from src.services.ai.llm_service import LLMService
from src.services.chat_service import ChatService
from src.services.elastic_service import ElasticService
from src.services.resume_service import ResumeService


class DataService:
    """
    Provides data services for managing resumes, including fetching, synchronizing, searching, and deleting
    resumes.

    This service integrates various components such as AsyncJobHandler, ResumeService, EmbeddingService,
    ElasticService, and LLMService to perform operations related to resume data.

    Attributes:
        bean_id (str): An identifier for the instance of this class, typically used for logging or debugging
        purposes.
        async_job_handler (AsyncJobHandler): Handles asynchronous job operations.
        resume_service (ResumeService): Manages operations related to resume.
        embedding_service (EmbeddingService): Provides text embedding services using SentenceTransformer
        AI.
        elastic_service (ElasticService): Manages interactions with Elasticsearch for resume data.
        llm_service (LLMService): Provides services for interacting with Large Language Model (LLM) API.

    Methods:
        fetch_resume(key: str) -> Resume:
            Fetches resume based on the provided key and model name.

        process_sync(job_id: int, key: str, index: str, sync_option: str) -> None:
            Processes synchronization of resume data based on the provided parameters.

        sync_resume(key: str, index_name: str, sync_option: str) -> dict:
            Synchronizes resume data with an external system or database.

        search_resume(_request: ResumeRequest) -> dict:
            Searches for resume based on a provided query and summarizes the results.

        delete_resume(index_name: str, key: str) -> dict:
            Deletes an resume based on the provided index name and key.

        get_embeddings(sentence: str, task_type: str) -> dict:
            Retrieves the embeddings for the provided sentence using the specified model.
    """

    def __init__(self,
                 bean_id,
                 async_job_handler: AsyncJobHandler,
                 resume_service: ResumeService,
                 embedding_service: EmbeddingService,
                 elastic_service: ElasticService,
                 llm_service: LLMService,
                 chat_service: ChatService):
        self.bean_id = bean_id
        self.async_job_handler = async_job_handler
        self.resume_service = resume_service
        self.vertex_text_embedding_service = embedding_service
        self.elastic_service = elastic_service
        self.llm_service = llm_service
        self.chat_service = chat_service

    async def fetch_insights(self, key):
        """
        Fetches insights based on the provided key (optional) and model name.

        This function retrieves insights from the InsightsService, removes 'title_vector' and 'description_vector'
        from the columns, and then converts the DataFrame to a dictionary.

        Parameters:
        key (str): (optional) The key used to fetch insights.
        model_name (str): (required) The name of the model used to fetch insights.

        Returns:
        Insights: An instance of the Insights class, containing the fetched insight records and their count.
        """
        insights_df = await self.insight_service.get_insights(key)
        insights_df = await InsightsService.pre_process_date_data(insights_df)
        insights_df = await InsightsService.pre_process_audit_date_data(insights_df)
        # Convert the DataFrame to a dictionary
        insight_records = insights_df.to_dict('records')
        insights = Insights(insight_records, len(insight_records))
        return insights

    async def process_sync(self, job_id, key, index, sync_option):
        try:
            response = await self.sync_insights(key, index, sync_option)
            await self.async_job_handler.update(job_id=job_id, status=JobStatus.COMPLETED.name, data=response)
        except Exception as e:
            error = {"error": str(e)}
            ic_logging.get_logger(__name__).exception(e)
            await self.async_job_handler.update(job_id=job_id, status=JobStatus.FAILED.name, data=error)

    async def update_user_reaction(self, key, index: str, user_reaction: str, cdsid: str, logged_in_user_name: str):
        if index.strip().startswith(EsIndexPrefix.ai_summary_cache.name):
            result = await self.elastic_service.get_document_by_id(index_name=index, document_id=key)
            document = result["_source"]
            response = await self.elastic_service.update_summary_cache(key=key, index=index, document=document,
                                                                       user_reaction=user_reaction, cdsid=cdsid,
                                                                       logged_in_user_name=logged_in_user_name)
            ai_summary_cache = {
                "summary": response
            }
            return ai_summary_cache
        else:
            raise AppException(404, "Invalid index name")

    async def sync_insights(self, key, index_name, sync_option):
        insights = await self.insight_service.get_insights(key)
        insight_docs = await InsightsService.preprocess_data(insights)

        insight_embeddings = await self.vertex_text_embedding_service.vectorize_data(insight_docs)
        insight_records = insight_embeddings.to_dict('records')

        es_records_count = await self.elastic_service.sync_insights(key, insight_records, index_name, sync_option)

        res = {"index": index_name, "model": self.vertex_text_embedding_service.name,
               "total_records": es_records_count}
        ic_logging.get_logger(__name__).info(f"Sync Response: {res}")
        return res

    async def search_insights_v2(self, _request: InsightsSearchRequest):
        """
        Search and Summarize for insights based on the provided query.

        This function retrieves insights from the ElasticService using the provided request,
        which should contain the model name, query and other search parameters. It then converts the
        retrieved insights into an instance of the Insights class.

        Parameters:
        _request (InsightsRequest): The request object containing search parameters.

        Returns:
        response: A summary about search results & instance of the Insights class, containing the fetched insight
        records and their count.
        """
        ic_logging.get_logger(__name__).info(f"Extracting keywords in Query ...")
        original_query = _request.query
        keywords_query = await self.llm_service.extract_keywords(original_query)
        if keywords_query:
            _request.query = keywords_query
        ic_logging.get_logger(__name__).info(
            f"Extracting keywords in Query completed... _request.query = {_request.query}")
        # Retrieve search results asynchronously
        response = await self.elastic_service.get_documents_from_search_insights(_request)
        # Re Rank results based on the score
        search_results = [result for result in response['results'] if result['_score'] >= 14]
        total_search_count = response['total_search_count']
        size_of_cur_page_results = len(search_results)
        ic_logging.get_logger(__name__).info(
            f"size_of_cur_page_results after re ranking and cut off: {size_of_cur_page_results}")
        ic_logging.get_logger(__name__).info(f"total_search_count: {total_search_count}")

        page_no = _request.page_no
        ai_summary_cache = {}
        if total_search_count > 0:
            # Summarize search results only for the first page
            if page_no == 1:
                index_name = EsIndexPrefix.ai_summary_cache.name + "_" + properties.env.strip().lower()
                _request.index = index_name
                if _request.ai_summary_cache_id:
                    ai_summary_cache = await self.summarize_and_cache(original_query=original_query,
                                                                      search_results=search_results,
                                                                      _request=_request)
                else:
                    ai_summary_cache = await self.get_ai_summary_from_cache(original_query, _request,
                                                                            search_results)
        else:
            summary = ("I'm sorry, but there are no search results for your query. If you have any other queries or "
                       "need assistance with different information, feel free to ask.")
            ai_summary_cache = await self.elastic_service.cache_ai_summaries(
                key=_request.ai_summary_cache_id,
                topic=_request.query,
                user_query=original_query,
                ai_summary=summary,
                index_name=_request.index,
                cdsid=_request.cdsid,
                logged_in_user_name=_request.logged_in_user_name,
                regions=_request.regions
            )

        # Construct response
        if page_no == 1:
            response = {
                "summary": ai_summary_cache['summary'],
                "search_results": Insights(search_results, total_search_count).to_dict()
            }
        else:
            response = {
                "summary": {},
                "search_results": Insights(search_results, total_search_count).to_dict()
            }

        return response

    async def get_ai_summary_from_cache(self, original_query: str, _request: InsightsSearchRequest,
                                        search_results: list):
        """
        Fetches AI summaries from the cache.

        This function retrieves AI summaries from the cache using the InsightsService.

        Returns:
        dict: A dictionary containing the AI summaries fetched from the cache.
        """

        is_ai_summary_cache_index_exists = await self.elastic_service.check_index_exists(_request.index)
        ic_logging.get_logger(__name__).info(
            f"Finding Summary from cache in index {_request.index}... exists? {is_ai_summary_cache_index_exists}")
        if not is_ai_summary_cache_index_exists:
            ai_summary_cache = await self.summarize_and_cache(original_query, search_results, _request)
        else:
            try:
                response = await self.elastic_service.get_documents_from_search_insights(_request)
                if not response:
                    ai_summary_cache = await self.summarize_and_cache(original_query, search_results, _request)
                else:
                    if response['total_search_count'] > 0:
                        if _request.regions is None or _request.regions == []:
                            response['results'] = [result for result in response['results'] if
                                                   result['_source'].get('regions') == []]
                        result = response['results'][0]
                        doc = result['_source']
                        query_cache = doc['user_query']
                        llm_response = await self.llm_service.analyse_user_queries(original_query, query_cache)
                        if llm_response and bool(re.search(r'\byes\b', str(llm_response).strip(), re.IGNORECASE)):
                            ai_summary_cache = {
                                "summary": doc
                            }
                        else:
                            ai_summary_cache = await self.summarize_and_cache(original_query, search_results, _request)
                    else:
                        ai_summary_cache = await self.summarize_and_cache(original_query, search_results, _request)
            except NotFoundError as nfe:
                ic_logging.get_logger(__name__).exception(nfe)
                ai_summary_cache = await self.summarize_and_cache(original_query, search_results, _request)
            except Exception as e:
                raise AppException(500, str(e))
        return ai_summary_cache

    async def summarize_and_cache(self, original_query: str, search_results: list[dict],
                                  _request: InsightsSearchRequest) -> dict[str, str | None | Any] | dict[str, Any]:
        ai_summary = await self.get_insights_summary(original_query, search_results)
        ai_summary_cache = await self.elastic_service.cache_ai_summaries(
            key=_request.ai_summary_cache_id,
            topic=_request.query,
            user_query=original_query,
            ai_summary=ai_summary,
            index_name=_request.index,
            cdsid=_request.cdsid,
            logged_in_user_name=_request.logged_in_user_name,
            regions=_request.regions
        )
        return ai_summary_cache

    async def get_insights_summary(self, query, search_results):
        summary = ""
        insight_documents = [search_result['_source'] for search_result in search_results]

        ic_logging.get_logger(__name__).info(f"Summarizing search results...")
        # Create a new list to hold the documents with only the specified fields
        documents_to_summarize = []

        # Define the fields to be copied
        fields_to_summarize = ['title', 'description', 'authors', 'regions']
        summarizing_length = 10
        for doc in insight_documents:
            if summarizing_length == 0:
                break
            else:
                filtered_doc = {field: doc[field] for field in fields_to_summarize if field in doc}
                documents_to_summarize.append(filtered_doc)
            summarizing_length -= 1

        try:
            # Generate summary
            summary = await self.llm_service.summarize(query, documents_to_summarize)
            ic_logging.get_logger(__name__).info(f"Summarizing completed successfully...")
        except Exception as e:
            ic_logging.get_logger(__name__).exception(e)
        return summary

    async def delete_insight(self, index_name, key):
        """
            Deletes an insight based on the provided index name and key (optional).

            This function uses the ElasticService to delete an insight from the specified index.
            If the key is provided, it deletes the specific insight associated with that key.
            If the key is not provided, it deletes all insights in the specified index including the index itself.

            Parameters:
            index_name (str): (required) The name of the index from which the insight is to be deleted.
            key (str): (optional) The key of the specific insight to be deleted.

            Returns:
            dict: A dictionary containing the response from the Elasticsearch delete operation.
            """
        await self.elastic_service.delete_insights(index_name, key)

    async def get_embeddings(self, sentence, task_type):
        """
            Retrieves the embeddings for the provided sentence using the specified model.

            This function uses the `embeddings` module to fetch the embeddings for the given sentence using
            provided model.

            Parameters:
            model (str): The name of the model to be used for generating embeddings.
            sentence (str): The sentence for which embeddings are to be generated.

            Returns:
            dict: A dictionary containing the embeddings for the provided sentence.
            """

        # Step 1: create embeddings
        for _task_type in EmbeddingsTaskType:
            if _task_type.name == task_type:
                embedding = await self.vertex_text_embedding_service.to_embeddings(sentence, _task_type)
                # Step 2: Convert embeddings to list if not already
                embedding_list = embedding.tolist() if not isinstance(embedding, list) else embedding
                return {"embedding": embedding_list}

        raise AppException(404, "Invalid task type")

    async def chat_process(self, gcs_path, user_question):
        """
            Processes a document from Google Cloud Storage and generates a response based on the user question.

            This function uses the ChatService to process the document and generate a response.

            Parameters:
            gcs_path (str): The Google Cloud Storage path to the document.
            user_question (str): The question asked by the user.

            Returns:
            dict: A dictionary containing the generated responses.
            """
        return await self.chat_service.process_document(gcs_path, user_question)
