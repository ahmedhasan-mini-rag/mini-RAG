from .providers import OpenAIProvider, CohereProvider, GoogleProvider
from .llm_enums import Provider
from utils.config import Settings
from exceptions import InvalidConfigError

class LLMProviderFactory:
    def __init__(self, config: Settings):
        self.config = config
    
    def create(self, provider: str):
        match provider.lower():
            case Provider.OPENAI:
                client = OpenAIProvider(
                    api_key=self.config.OPENAI_API_KEY,
                    base_url=self.config.OPENAI_BASE_URL,
                    default_max_output_tokens=self.config.DEFAULT_MAX_OUTPUT_TOKENS,
                    default_max_input_chars=self.config.DEFAULT_MAX_INPUT_CHARS,
                    default_temperature=self.config.DEFAULT_TEMPERATURE,
                )
            
            case Provider.COHERE:
                client = CohereProvider(
                    api_key=self.config.COHERE_API_KEY,
                    default_max_output_tokens=self.config.DEFAULT_MAX_OUTPUT_TOKENS,
                    default_max_input_chars=self.config.DEFAULT_MAX_INPUT_CHARS,
                    default_temperature=self.config.DEFAULT_TEMPERATURE,
                )
            
            case Provider.GOOGLE:
                client = GoogleProvider(
                    api_key=self.config.GOOGLE_API_KEY,
                    default_max_output_tokens=self.config.DEFAULT_MAX_OUTPUT_TOKENS,
                    default_max_input_chars=self.config.DEFAULT_MAX_INPUT_CHARS,
                    default_temperature=self.config.DEFAULT_TEMPERATURE,
                )
            
            case _:
                raise InvalidConfigError(f"Unknown LLM provider: '{provider}'")
        
        return client