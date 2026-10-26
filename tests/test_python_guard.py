import pytest


@pytest.mark.parametrize("version", [(3, 8), (3, 9), (3, 10)])
def test_old_interpreter_is_refused_with_an_actionable_message(version):
    import app
    with pytest.raises(RuntimeError) as caught:
        app.check_python(version)
    assert "needs Python 3.11" in str(caught.value)
    assert "python3.11 -m venv" in str(caught.value)


@pytest.mark.parametrize("version", [(3, 14), (3, 15), (4, 0)])
def test_interpreter_without_a_pydantic_core_wheel_is_refused_before_pip_fails(version):
    import app
    with pytest.raises(RuntimeError) as caught:
        app.check_python(version)
    message = str(caught.value)
    assert "tested on Python 3.11 through 3.13" in message
    assert "pydantic-core" in message and "compile" in message


@pytest.mark.parametrize("version", [(3, 11), (3, 12), (3, 13)])
def test_supported_interpreters_pass_the_guard(version):
    import app
    assert app.check_python(version) is None
