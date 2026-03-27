class AutoValidatorError(Exception):
    """Base exception for all Auto-Validator errors."""


class ValidationLoopError(AutoValidatorError):
    """Raised when the pain-score refinement loop exceeds max retries."""


class LLMParseError(AutoValidatorError):
    """Raised when an LLM response cannot be parsed into the expected model."""


class IntegrationError(AutoValidatorError):
    """Raised when an external API call fails."""


class ProjectNotFoundError(AutoValidatorError):
    """Raised when a project_id does not match any stored project."""
