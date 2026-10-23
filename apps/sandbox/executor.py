import io
import multiprocessing
import sys
from contextlib import redirect_stdout

from .allowed_builtins import ALLOWED_BUILTIN_NAMES
from .exceptions import (
    SandboxExecutionError,
    SandboxTimeoutError,
    SandboxValidationError,
)
from .validator import validate_code


def _make_builtins(stdout_buffer):
    import builtins as _builtins

    result = {}
    for name in ALLOWED_BUILTIN_NAMES:
        if hasattr(_builtins, name):
            result[name] = getattr(_builtins, name)

    def _print(*args, **kwargs):
        kwargs["file"] = stdout_buffer
        _builtins.print(*args, **kwargs)

    result["print"] = _print
    result["__builtins__"] = {}
    return result


def _worker(code, input_data, queue):
    stdout_buffer = io.StringIO()
    try:
        validate_code(code)
        builtins = _make_builtins(stdout_buffer)
        globals_dict = {"__builtins__": builtins, "data": input_data, "input": input_data}
        locals_dict = {}
        with redirect_stdout(stdout_buffer):
            exec(compile(code, "<sandbox>", "exec"), globals_dict, locals_dict)
        result = locals_dict.get("result", globals_dict.get("result"))
        queue.put(
            {
                "success": True,
                "result": result,
                "error": None,
                "stdout": stdout_buffer.getvalue(),
            }
        )
    except Exception as exc:  # pragma: no cover - exercised via tests
        queue.put(
            {
                "success": False,
                "result": None,
                "error": f"{type(exc).__name__}: {exc}",
                "stdout": stdout_buffer.getvalue(),
            }
        )


def execute_user_code(code, input_data=None, timeout=2.0, max_memory_mb=64):
    validate_code(code)

    if input_data is None:
        input_data = {}

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_worker, args=(code, input_data, queue), daemon=True
    )
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "success": False,
            "result": None,
            "error": f"Execution timed out after {timeout} seconds",
            "stdout": "",
        }

    try:
        payload = queue.get(timeout=1)
    except Exception:
        payload = {
            "success": False,
            "result": None,
            "error": "SandboxExecutionError: no result returned from worker",
            "stdout": "",
        }

    if not payload.get("success", False):
        return {
            "success": False,
            "result": None,
            "error": payload.get("error", "SandboxExecutionError: execution failed"),
            "stdout": payload.get("stdout", ""),
        }

    return {
        "success": True,
        "result": payload.get("result"),
        "error": None,
        "stdout": payload.get("stdout", ""),
    }
