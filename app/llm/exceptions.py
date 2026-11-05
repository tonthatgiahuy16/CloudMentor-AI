class LLMProviderError(RuntimeError):
    """A controlled failure from the external LLM provider."""


class LLMProviderUnavailableError(LLMProviderError):
    """A retryable provider failure exhausted its retry budget."""
