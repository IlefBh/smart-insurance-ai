"""
LLM Explanation Layer
Generates human-readable explanations for insurance offers.
"""

from .explainer import OfferExplainer, ExplanationOutput

__all__ = ['OfferExplainer', 'ExplanationOutput']