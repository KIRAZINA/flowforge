import ast
import io
import json
import multiprocessing
import traceback
from contextlib import redirect_stdout

from .allowed_builtins import ALLOWED_BUILTIN_NAMES
from .exceptions import (
    SandboxValidationError,
)
from .helpers import Helpers
from .validator import validate_code

DEFAULT_TIMEOUT = 3.0
DEFAULT_MAX_MEMORY_MB = 64
DEFAULT_MAX_RESULT_SIZE = 1 * 1024 * 1024


def _apply_memory_limit(max_memory_mb):
    # Soft memory limits via resource.setrlimit proved unstable on several
    # platforms (the forked interpreter can already exceed the limit and die
    # silently). Keep this as a documented stub for now.
    return False


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


def _result_size(result):
    try:
        return len(json.dumps(result, default=str))
    except Exception:
        try:
            return len(repr(result))
        except Exception:
            return 0


def _worker(code, input_data, queue, timeout, max_memory_mb, max_result_size):
    stdout_buffer = io.StringIO()
    _apply_memory_limit(max_memory_mb)
    try:
        validate_code(code)
        tree = ast.parse(code, mode="exec")
        is_single_expression = len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr)

        builtins = _make_builtins(stdout_buffer)
        globals_dict = {
            "__builtins__": builtins,
            "data": input_data,
            "input": input_data,
            "helpers": Helpers,
        }
        locals_dict = {}

        with redirect_stdout(stdout_buffer):
            if is_single_expression:
                result = eval(  # noqa: S307
                    compile(code, "<sandbox>", "eval"), globals_dict, locals_dict
                )
            else:
                exec(compile(code, "<sandbox>", "exec"), globals_dict, locals_dict)  # noqa: S102
                if "result" in locals_dict:
                    result = locals_dict["result"]
                elif "result" in globals_dict:
                    result = globals_dict["result"]
                else:
                    raise ValueError(
                        "No result produced: assign to a variable named 'result' "
                        "or provide a single expression."
                    )

        if _result_size(result) > max_result_size:
            queue.put(
                {
                    "success": False,
                    "result": None,
                    "error": f"Result exceeds the maximum allowed size of {max_result_size} bytes.",
                    "error_type": "result_too_large",
                    "stdout": stdout_buffer.getvalue(),
                }
            )
            return

        queue.put(
            {
                "success": True,
                "result": result,
                "error": None,
                "error_type": None,
                "stdout": stdout_buffer.getvalue(),
            }
        )
    except MemoryError as exc:
        queue.put(
            {
                "success": False,
                "result": None,
                "error": f"MemoryError: {exc}",
                "error_type": "memory",
                "stdout": stdout_buffer.getvalue(),
            }
        )
    except Exception as exc:
        frames = traceback.extract_tb(exc.__traceback__)
        sandbox_frames = [frame for frame in frames if frame.filename == "<sandbox>"]
        selected = (sandbox_frames or frames)[-4:]
        tb_text = "".join(traceback.format_list(selected)).strip()
        message = f"{type(exc).__name__}: {exc}"
        if tb_text:
            message = f"{message}\n{tb_text}"
        queue.put(
            {
                "success": False,
                "result": None,
                "error": message,
                "error_type": "runtime",
                "stdout": stdout_buffer.getvalue(),
            }
        )


def _run(code, input_data, timeout, max_memory_mb, max_result_size):
    if input_data is None:
        input_data = {}

    try:
        validate_code(code)
    except SandboxValidationError as exc:
        return {
            "success": False,
            "result": None,
            "error": str(exc),
            "error_type": "validation",
            "stdout": "",
        }

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_worker,
        args=(code, input_data, queue, timeout, max_memory_mb, max_result_size),
        daemon=True,
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
            "error_type": "timeout",
            "stdout": "",
        }

    try:
        payload = queue.get(timeout=1)
    except Exception:
        return {
            "success": False,
            "result": None,
            "error": "SandboxExecutionError: no result returned from worker",
            "error_type": "runtime",
            "stdout": "",
        }

    return {
        "success": bool(payload.get("success", False)),
        "result": payload.get("result"),
        "error": payload.get("error"),
        "error_type": payload.get("error_type"),
        "stdout": payload.get("stdout", ""),
    }


def run_transform(
    code,
    data,
    timeout=DEFAULT_TIMEOUT,
    max_memory_mb=DEFAULT_MAX_MEMORY_MB,
    max_result_size=DEFAULT_MAX_RESULT_SIZE,
):
    """Main entry point for Transform nodes."""
    return _run(code, data, timeout, max_memory_mb, max_result_size)


def execute_user_code(
    code,
    input_data=None,
    timeout=DEFAULT_TIMEOUT,
    max_memory_mb=DEFAULT_MAX_MEMORY_MB,
    max_result_size=DEFAULT_MAX_RESULT_SIZE,
):
    """Backward-compatible alias."""
    return _run(code, input_data, timeout, max_memory_mb, max_result_size)
