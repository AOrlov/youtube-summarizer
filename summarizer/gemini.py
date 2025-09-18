from typing import List, Optional

from google import genai
from google.genai import types

from .utils import get_logger

logger = get_logger(__name__)


class GeminiSummarizer:
    """Class for generating summaries using the Gemini API."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash-latest"):
        """
        Initialize the Gemini summarizer.

        Args:
            api_key: The Gemini API key
            model_name: The name of the Gemini model to use (default: "gemini-1.5-flash-latest")
        """
        self.api_key = api_key
        self.model_name = (
            model_name
            if model_name.startswith("models/")
            else f"models/{model_name}"
        )
        self.client = self._configure_api()

        logger.info(f"Initialized GeminiSummarizer with model: {model_name}")

    def _configure_api(self) -> genai.Client:
        """Configure the Gemini API with the provided key."""
        try:
            client = genai.Client(api_key=self.api_key)
            logger.info("Gemini API configured successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {str(e)}")
            raise

    def _create_prompt(self, transcript: str, language: str) -> str:
        """
        Create a prompt for the Gemini API.

        Args:
            transcript: The transcript text to summarize

        Returns:
            The formatted prompt
        """
        return f"""Please provide a comprehensive summary of the given text. The summary should cover all the key points and main ideas presented in the original text, while also condensing the information into a concise and easy-to-understand format. Please ensure that the summary includes relevant details and examples that support the main ideas, while avoiding any unnecessary information or repetition. The length of the summary should be appropriate for the length and complexity of the original text, providing a clear and accurate overview without omitting any important information.
If you notice from the context any links to books or authors, add concise descriptions of the ideas and concepts they represent to the summary.
Output in {language} language:

{transcript}

Summary:"""

    def summarize(
        self, transcript: str, language: str, max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a summary of the transcript using the Gemini API.

        Args:
            transcript: The transcript text to summarize
            max_tokens: Optional maximum number of tokens for the summary

        Returns:
            The generated summary

        Raises:
            Exception: If there's an error during summarization
        """
        try:
            prompt = self._create_prompt(transcript, language)
            # Configure generation parameters
            generation_config = types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.8,
                top_k=40,
                max_output_tokens=max_tokens,
                http_options=types.HttpOptions(timeout=60000),
            )

            # Generate the summary
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=generation_config,
            )

            logger.info("Summary generated successfully")
            if not getattr(response, "text", ""):
                error_message = "Gemini API returned an empty response"
                logger.error(error_message)
                raise ValueError(error_message)

            return response.text

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise

    def get_available_models(self) -> List[str]:
        """
        Get list of available Gemini models.

        Returns:
            List of available model names
        """
        try:
            models = self.client.models.list()
            return [model.name for model in models]
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            raise
