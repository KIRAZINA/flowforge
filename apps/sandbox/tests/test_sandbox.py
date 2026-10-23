import pytest

from apps.sandbox.executor import execute_user_code, run_transform
from apps.sandbox.exceptions import SandboxValidationError
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


def test_helper_get_nested():
    code = "result = helpers.get(data, 'user.address.city', 'unknown')"
    out = run_transform(code, {"user": {"address": {"city": "Paris"}}})
    assert out["success"] is True
    assert out["result"] == "Paris"


def test_helper_set_value_immutable():
    code = "result = helpers.set_value(data, 'user.name', 'Ada')"
    out = run_transform(code, {"user": {"name": "Grace"}})
    assert out["success"] is True
    assert out["result"]["user"]["name"] == "Ada"


def test_helper_pick_and_omit():
    code = "result = {'picked': helpers.pick(data, ['a', 'b']), 'omitted': helpers.omit(data, ['a'])}"
    out = run_transform(code, {"a": 1, "b": 2, "c": 3})
    assert out["success"] is True
    assert out["result"]["picked"] == {"a": 1, "b": 2}
    assert out["result"]["omitted"] == {"b": 2, "c": 3}


def test_helper_json_roundtrip():
    code = "result = helpers.from_json(helpers.to_json({'n': 5}))"
    out = run_transform(code, {})
    assert out["success"] is True
    assert out["result"] == {"n": 5}


def test_nested_transformation():
    code = """
items = data['items']
result = [helpers.get(item, 'price', 0) * item.get('qty', 1) for item in items]
"""
    out = run_transform(code, {"items": [{"price": 3, "qty": 2}, {"price": 5}]})
    assert out["success"] is True
    assert out["result"] == [6, 5]


def test_no_result_error():
    out = run_transform("x = 5", {})
    assert out["success"] is False
    assert out["error_type"] == "runtime"
    assert "No result produced" in (out["error"] or "")


def test_validation_error_type():
    out = run_transform("import os", {})
    assert out["success"] is False
    assert out["error_type"] == "validation"


def test_timeout_error_type():
    out = run_transform("while True:\n    pass", {}, timeout=0.5)
    assert out["success"] is False
    assert out["error_type"] == "timeout"


def test_print_captured_run_transform():
    out = run_transform("print('hi')\nresult = 1", {})
    assert out["success"] is True
    assert out["stdout"] == "hi\n"


def test_clean_runtime_error():
    out = run_transform("result = 1 / 0", {})
    assert out["success"] is False
    assert out["error_type"] == "runtime"
    assert "ZeroDivisionError" in (out["error"] or "")
