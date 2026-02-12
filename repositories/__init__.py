"""
Repository pattern implementations for data access
Decouples business logic from storage implementation
"""

from .user_repository import UserRepository, ShelveUserRepository, get_user_repository

__all__ = ['UserRepository', 'ShelveUserRepository', 'get_user_repository']
