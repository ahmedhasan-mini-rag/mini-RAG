import yaml
import logging
from pathlib import Path
from dataclasses import dataclass

_TEMPLATES_DIR = Path(__file__).parent
logger = logging.getLogger(__name__)

# The default language instruction when the caller doesn't specify one.
_AUTO_LANGUAGE = "the same language the user used in their query"

@dataclass(frozen=True)
class RAGTemplate:
    system_prompt: str
    document_prompt: str
    footer_prompt: str

    def format_system_prompt(self, response_language: str) -> str:
        """Render the system prompt with an explicit response language.

        Args:
            response_language: A language name (e.g. ``"Arabic"``, ``"English"``),
                or ``"auto"`` to let the model match the user's query language.
        """
        language = (
            _AUTO_LANGUAGE
            if response_language.lower() == "auto"
            else response_language
        )
        return self.system_prompt.format(response_language=language)

    def format_document(self, doc_num: int, chunk_text: str) -> str:
        """Render a single retrieved document block."""
        return self.document_prompt.format(doc_num=doc_num, chunk_text=chunk_text)

    def format_footer(self, user_query: str) -> str:
        """Render the closing footer that contains the user's question."""
        return self.footer_prompt.format(user_query=user_query)


def load_template(template_name: str) -> RAGTemplate:
    """
    Load a YAML prompt template.

    Args:
        template_name: Name of the template file without extension (e.g. ``"rag"``).

    Returns:
        A :class:`RAGTemplate` instance with the loaded prompt strings.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    template_path = _TEMPLATES_DIR / f"{template_name}.yml"
    if not template_path.is_file():
        raise FileNotFoundError(
            f"Template '{template_name}' not found. "
            f"Expected file: {template_path}"
        )

    with open(template_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return RAGTemplate(
        system_prompt=data["system_prompt"].strip(),
        document_prompt=data["document_prompt"].strip(),
        footer_prompt=data["footer_prompt"].strip(),
    )
