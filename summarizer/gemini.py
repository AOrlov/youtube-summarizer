from typing import List, Optional

import google.generativeai as genai

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
        self.model_name = model_name
        self._configure_api()

        logger.info(f"Initialized GeminiSummarizer with model: {model_name}")

    def _configure_api(self) -> None:
        """Configure the Gemini API with the provided key."""
        try:
            genai.configure(api_key=self.api_key)
            logger.info("Gemini API configured successfully")
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
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.8,
                top_k=40,
                max_output_tokens=max_tokens,
            )

            # Generate the summary
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt, generation_config=generation_config, request_options={
                    "timeout": 600},
            )

            logger.info("Summary generated successfully")
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
            models = genai.list_models()
            return [model.name for model in models]
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            raise
