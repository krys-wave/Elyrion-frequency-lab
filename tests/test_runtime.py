import pytest
from scripts.check_runtime import check_node, check_python


def test_supported_toolchain():
    check_python((3, 12, 10))
    check_python((3, 12, 14))
    check_node("v22.23.4\n")


@pytest.mark.parametrize("version", [(3, 11, 9), (3, 13, 1)])
def test_python_guard_explains_pinned_wheel_requirement(version):
    with pytest.raises(ValueError, match="Python 3.12.x"):
        check_python(version)


@pytest.mark.parametrize("version", ["v20.19.0", "v24.19.0"])
def test_node_guard_prevents_unverified_monterey_runtime(version):
    with pytest.raises(ValueError, match="Node.js 22.x"):
        check_node(version)
