import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import get_logger

logger = get_logger(__name__)


class FileHandler:
    """Handles file operations for saving summaries and managing output directories."""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize the file handler.

        Args:
            output_dir: Base directory for output files
        """
        self.output_dir = Path(output_dir)
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Ensure the output directory exists."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory ensured: {self.output_dir}")
        except PermissionError as e:
            logger.error(f"Permission denied when creating output directory: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create output directory: {str(e)}")
            raise

    def _validate_path(self, path: Path) -> None:
        """
        Validate a file path.

        Args:
            path: Path to validate

        Raises:
            ValueError: If path is invalid
            PermissionError: If path is not writable
        """
        try:
            if not path.parent.exists():
                raise ValueError(f"Parent directory does not exist: {path.parent}")

            if path.exists() and not os.access(path, os.W_OK):
                raise PermissionError(f"File exists and is not writable: {path}")
        except PermissionError as e:
            logger.error(f"Permission error when validating path: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error validating path: {str(e)}")
            raise

    def save_summary(
        self,
        video_id: str,
        transcript_language: str,
        summary_language: str,
        summary: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Save a summary to a file in Markdown format.

        Args:
            video_id: YouTube video ID
            transcript_language: Transcript language used for the video
            summary_language: Language requested for the summary output
            summary: The summary text
            metadata: Optional metadata to save with the summary

        Returns:
            Path to the saved file

        Raises:
            ValueError: If path is invalid
            PermissionError: If file is not writable
            IOError: If file operation fails
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = (
                f"summary_{video_id}_{transcript_language}_"
                f"{summary_language}_{timestamp}.md"
            )
            file_path = self.output_dir / filename

            # Validate path
            self._validate_path(file_path)

            summary_metadata = dict(metadata or {})
            summary_metadata["transcript_language"] = transcript_language
            summary_metadata["summary_language"] = summary_language

            # Prepare markdown content
            markdown_content = f"""## Summary
{summary}

## Metadata
"""
            for key, value in summary_metadata.items():
                markdown_content += f"- **{key}**: {value}\n"

            markdown_content += f"\nGenerated on: {timestamp}"

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            logger.info(f"Summary saved to: {file_path}")
            return file_path

        except (ValueError, PermissionError) as e:
            logger.error(f"Failed to save summary: {str(e)}")
            raise
        except IOError as e:
            logger.error(f"IO error when saving summary: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error when saving summary: {str(e)}")
            raise

    def get_summary_path(
        self,
        video_id: str,
        transcript_language: str,
        summary_language: str,
    ) -> Optional[Path]:
        """
        Get the path to the most recent summary for a video.

        Args:
            video_id: YouTube video ID
            transcript_language: Transcript language used for the video
            summary_language: Requested summary language

        Returns:
            Path to the summary file if found, None otherwise
        """
        try:
            patterns = [
                f"summary_{video_id}_{transcript_language}_{summary_language}_*.md"
            ]
            if transcript_language == summary_language:
                patterns.append(f"summary_{video_id}_{transcript_language}_*.md")

            files = []
            for pattern in patterns:
                files = list(self.output_dir.glob(pattern))
                if files:
                    break
            if not files:
                return None

            # Get the most recent file
            latest_file = max(files, key=lambda x: x.stat().st_mtime)
            return latest_file

        except Exception as e:
            logger.error(f"Failed to get summary path: {str(e)}")
            return None

    def cleanup_old_summaries(self, max_age_days: int = 30) -> None:
        """
        Remove summary files older than specified days.

        Args:
            max_age_days: Maximum age of files to keep in days

        Raises:
            PermissionError: If unable to delete files
            IOError: If file operations fail
        """
        try:
            current_time = datetime.now()
            for pattern in ("summary_*.md", "summary_*.txt"):
                for file_path in self.output_dir.glob(pattern):
                    try:
                        file_age = current_time - datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        )
                        if file_age.days > max_age_days:
                            file_path.unlink()
                            logger.info(f"Removed old summary file: {file_path}")
                    except PermissionError as e:
                        logger.error(
                            f"Permission denied when removing file {file_path}: {str(e)}"
                        )
                        raise
                    except Exception as e:
                        logger.error(f"Error removing file {file_path}: {str(e)}")
                        continue

        except Exception as e:
            logger.error(f"Failed to cleanup old summaries: {str(e)}")
            raise
