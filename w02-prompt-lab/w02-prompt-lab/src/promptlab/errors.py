"""Errors used by the Week 2 local model lab."""


class TransientProviderError(Exception):
    """Raised on timeout, connection failure, or a temporary Ollama/server failure."""


class PermanentProviderError(Exception):
    """Raised on a malformed request, unavailable model, unsupported parameter, or other non-retryable request failure."""


class TruncatedResponseError(Exception):
    """Raised when Ollama reports that the output token ceiling was reached."""


class UnknownModelError(ValueError):
    """Raised when a model identifier is not present in the configured model table."""
