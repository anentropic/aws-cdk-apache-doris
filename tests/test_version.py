"""Basic tests for the package."""

import aws_cdk_apache_doris


def test_version():
    """Test that version is defined."""
    assert hasattr(aws_cdk_apache_doris, "__version__")
    assert isinstance(aws_cdk_apache_doris.__version__, str)
    assert aws_cdk_apache_doris.__version__ == "0.1.0"
