"""Luat HNGD knowledge domain implementation."""

from __future__ import annotations

from ..base import KnowledgeDomain
from ..registry import domain

@domain("hngd")
class HNGDDomain(KnowledgeDomain):
    """HNGD domain for knowledge graph extraction.
    
    This class uses automatic root resolution and grouped API 
    inherited from KnowledgeDomain.
    """
    pass

__all__ = ["HNGDDomain"]