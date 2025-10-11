"""
Amazon Q (QConnect) Integration Module

Provides Amazon Q integration for Amazon Connect with knowledge base support.
"""

from .integration import create_qconnect_integration, create_qconnect_knowledge_bucket

__all__ = [
    'create_qconnect_integration',
    'create_qconnect_knowledge_bucket',
]
