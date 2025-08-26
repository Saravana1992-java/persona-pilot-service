import vertexai
import vertexai.preview.generative_models as generative_models
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import storage

class ChatService:
    """
    Manages the interaction with Vertex AI generative models for document processing and question answering.

    This service is responsible for initializing the Vertex AI environment, configuring the generative model, and generating responses based on provided documents and user questions. It supports operations such as processing documents from Google Cloud Storage and generating content using Vertex AI's generative models.

    Attributes:
        bean_id (str): An identifier for the instance of this class, typically used for logging or debugging purposes.

    Methods:
        process_document(gcs_path: str, user_question: str) -> dict:
            Processes a document from Google Cloud Storage and generates a response based on the user question. Returns a dictionary containing the generated responses.
        generate(TEXT: str, DOCUMENT: Part) -> list:
            Generates content using the Vertex AI generative model based on the provided text and document. Returns a list of response texts.
    """
    
    def __init__(self, bean_id, app_properties):
        self.bean_id = bean_id
        self.app_properties = app_properties
    
    
    async def process_document(self, gcs_path, user_question) -> dict:
        TEXT = f''' Understand the document completely and answer the question below
        Question -> {user_question}'''
        
        if gcs_path.endswith('.pdf'):
            DOCUMENT = Part.from_uri(
                gcs_path, mime_type="application/pdf"
            )
        elif gcs_path.endswith('.json'):
            client = storage.Client()
            bucket = client.get_bucket('bkt-aim-files-dev')
            extracted_path = "/".join(gcs_path.split("/")[3:])
            blob = bucket.blob(extracted_path)
            content = blob.download_as_text()   
            DOCUMENT = Part.from_text(content)
        else:
            return ["Invalid file type"]
        return await self.generate(TEXT, DOCUMENT)

    async def generate(self, TEXT, DOCUMENT):
        """
        Initialize Vertex AI with the specified project and location, create a
        generative model with the specified model, and generate content with the
        specified text and document.

        Args:
            TEXT: The text to be used for content generation.
            DOCUMENT: The document to be used for content generation.

        Returns:
            responses: A list of responses from the Vertex AI function for the
            generated content.
        """
        
        safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        MODEL = "gemini-1.5-pro-001"

        generation_config = {
            "max_output_tokens": 8192,
            "temperature": 1,
            "top_p": 0.95,
        }
        
        try:
            vertexai.init(project=self.app_properties.gcp_project_id, location=self.app_properties.pgsql_region)
            model = GenerativeModel(
                f"{MODEL}",
            )
            responses = model.generate_content(
                [
                    TEXT,
                    DOCUMENT
                ],
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=True,
            )

            response_texts = []
            for response in responses:
                response_texts.append(response.text)
            return response_texts
        except Exception as exception:
            return [str(exception)]