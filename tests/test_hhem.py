"""Tests for HHEM hallucination scoring."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

# Force CPU mode
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from rce_mcp.hhem import score_hallucination, is_hhem_available, hhem_status


@pytest.mark.asyncio
@pytest.mark.skipif(not is_hhem_available(), reason="HHEM not available")
async def test_consistent_claim():
    result = await score_hallucination(
        "The Eiffel Tower is in Paris, France.",
        "The Eiffel Tower is located in Paris, France.",
    )
    assert result["available"] is True
    assert result["score"] > 0.5
    assert result["label"] == "consistent"
    assert result["error"] is None


@pytest.mark.asyncio
@pytest.mark.skipif(not is_hhem_available(), reason="HHEM not available")
async def test_hallucinated_claim():
    result = await score_hallucination(
        "The Eiffel Tower is in London, England.",
        "The Eiffel Tower is located in Paris, France.",
    )
    assert result["available"] is True
    assert result["score"] < 0.2
    assert result["label"] == "hallucinated"


@pytest.mark.asyncio
@pytest.mark.skipif(not is_hhem_available(), reason="HHEM not available")
async def test_factual_but_hallucinated():
    """Test the 'factual but hallucinated' case — true in world knowledge but contradicts source."""
    result = await score_hallucination(
        "The capital of France is Paris.",
        "The capital of France is Berlin.",
    )
    assert result["available"] is True
    # Even though Paris IS the capital, HHEM should flag this as hallucinated
    # because the premise says Berlin
    assert result["score"] < 0.3
    assert result["label"] == "hallucinated"


def test_hhem_status():
    status = hhem_status()
    assert "available" in status
    assert "loaded" in status
    assert "model" in status
