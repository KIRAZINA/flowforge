import pytest

from apps.sandbox.exceptions import SandboxValidationError
from apps.sandbox.executor import execute_user_code, run_transform
from apps.sandbox.validator import validate_code


def test_valid_simple_transformation():
    code = "result = 2 + 3"
    assert execute_user_code(code)["result"] == 5


def test_transform_input_data():
    code = "result = data['value'] * 2"
    out = execute_user_code(code, input_data={"value": 21})
    assert out["success"] is True
    assert out["result"] == 42


def test_print_capture():
    code = "print('hello')\nresult = 7"
    out = execute_user_code(code)
    assert out["success"] is True
    assert out["result"] == 7
    assert "hello" in out["stdout"]


def test_import_os_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("import os")


def test_open_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("open('/etc/passwd')")


def test_eval_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("eval('1+1')")


def test_import_builtin_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("__import__('os')")


def test_dunder_attribute_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("x = ().__class__")


def test_forbidden_module_name_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("os.system('ls')")


def test_infinite_loop_times_out():
    out = execute_user_code("while True:\n    pass", timeout=0.5)
    assert out["success"] is False
    assert "timed out" in (out["error"] or "").lower()


def test_normal_exception_returned():
    out = execute_user_code("result = 1 / 0")
    assert out["success"] is False
    assert "ZeroDivisionError" in (out["error"] or "")


def test_function_definition_allowed():
    code = "def double(x):\n    return x * 2\nresult = double(6)"
    out = execute_user_code(code)
    assert out["success"] is True
    assert out["result"] == 12


def test_single_expression_supported():
    out = run_transform("data['x'] + data['y']", {"x": 2, "y": 3})
    assert out["success"] is True
    assert out["result"] == 5


def test_getattr_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("getattr({}, 'get')")


def test_setattr_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("setattr({}, 'x', 1)")


def test_hasattr_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("hasattr({}, 'x')")


def test_exit_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("exit()")


def test_help_rejected():
    with pytest.raises(SandboxValidationError):
        validate_code("help()")


def test_large_result_rejected():
    out = run_transform("result = 'a' * 1000", {}, max_result_size=10)
    assert out["success"] is False
    assert out["error_type"] == "result_too_large"
