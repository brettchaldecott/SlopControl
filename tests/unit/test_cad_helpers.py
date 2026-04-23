"""Tests for CAD helpers utilities."""

import pytest


class TestCadHelpers:
    """Test suite for CAD helper functions."""

    def test_serialize_body(self):
        """Test body serialization."""
        from planforge.utils.cad_helpers import serialize_body

        result = serialize_body({"body": "test", "name": "test_body"})
        assert "ref" in result
        assert "name" in result

    def test_deserialize_body(self):
        """Test body deserialization."""
        from planforge.utils.cad_helpers import serialize_body, deserialize_body

        original = {"body": "test_data", "name": "test"}
        serialized = serialize_body(original)
        deserialized = deserialize_body(serialized)

        assert deserialized["body"] == "test_data"
        assert deserialized["name"] == "test"

    def test_validate_dimensions_valid(self):
        """Test dimension validation with valid values."""
        from planforge.utils.cad_helpers import validate_dimensions

        valid, error = validate_dimensions(width=10, height=20)
        assert valid is True
        assert error is None

    def test_validate_dimensions_negative(self):
        """Test dimension validation with negative value."""
        from planforge.utils.cad_helpers import validate_dimensions

        valid, error = validate_dimensions(width=-5)
        assert valid is False
        assert "must be positive" in error

    def test_validate_dimensions_zero(self):
        """Test dimension validation with zero."""
        from planforge.utils.cad_helpers import validate_dimensions

        valid, error = validate_dimensions(height=0)
        assert valid is False

    def test_get_model_info(self):
        """Test model info extraction structure."""
        from planforge.utils.cad_helpers import get_model_info

        info = get_model_info(None)
        assert "type" in info
        assert "dimensions" in info
