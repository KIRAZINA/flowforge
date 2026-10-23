class SandboxValidationError(Exception):
    """Raised when user code fails AST validation."""


class SandboxExecutionError(Exception):
    """Raised when user code fails during execution."""


class SandboxTimeoutError(SandboxExecutionError):
    """Raised when user code exceeds the allowed execution time."""


class SandboxMemoryError(SandboxExecutionError):
    """Raised when user code exceeds the allowed memory (stub)."""
