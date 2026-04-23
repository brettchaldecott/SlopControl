"""Tests for LLM provider registry."""

import pytest


class TestProviderRegistry:
    """Test suite for LLM provider functionality."""

    def test_parse_model_string(self):
        """Test model string parsing."""
        from planforge.providers.registry import parse_model_string

        provider, model = parse_model_string("openai:gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_parse_model_string_no_provider(self):
        """Test parsing model string without provider."""
        from planforge.providers.registry import parse_model_string

        provider, model = parse_model_string("gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_list_available_models(self):
        """Test listing available models."""
        from planforge.providers.registry import list_available_models

        models = list_available_models()
        assert "openai" in models
        assert "anthropic" in models
        assert "ollama" in models

    def test_list_models_for_provider(self):
        """Test listing models for specific provider."""
        from planforge.providers.registry import list_available_models

        openai_models = list_available_models("openai")
        assert "openai" in openai_models
        assert len(openai_models["openai"]) > 0
