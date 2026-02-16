"""
Progress Tracking Service
Centralized progress tracking for recommendation generation pipeline.

Manages real-time progress updates for background jobs, providing
thread-safe storage and retrieval of generation status.

Author: Chad + Claude
Date: February 2026
"""

import threading
from datetime import datetime
from typing import Dict, Any, Optional, List


class ProgressTracker:
    """
    Thread-safe progress tracker for recommendation generation.

    Stores progress state for each user, including current stage,
    interests discovered, retailers searched, and completion status.

    Usage:
        tracker = ProgressTracker(storage_dict)
        tracker.set_progress('user_123', stage='searching', stage_label='Searching stores...')
        progress = tracker.get_progress('user_123')
        tracker.mark_complete('user_123', success=True, recommendations=[...])
    """

    def __init__(self, storage: Optional[Dict] = None):
        """
        Initialize progress tracker.

        Args:
            storage: Optional dict-like storage (e.g., in-memory dict or shelve).
                    If None, creates new in-memory storage.
        """
        self.storage = storage if storage is not None else {}
        self.lock = threading.Lock()

    def set_progress(self, user_id: str, stage: Optional[str] = None,
                    stage_label: Optional[str] = None, **kwargs) -> None:
        """
        Update progress for a user.

        Args:
            user_id: Unique user identifier
            stage: Pipeline stage (e.g., 'profile_analysis', 'searching_retailers', 'curating')
            stage_label: Human-readable stage description
            **kwargs: Additional progress data (interests, retailers, product_count, etc.)
        """
        with self.lock:
            if user_id not in self.storage:
                self.storage[user_id] = {
                    'stage': 'starting',
                    'stage_label': 'Getting started...',
                    'interests': [],
                    'retailers': {},
                    'product_count': 0,
                    'complete': False,
                    'success': False,
                    'error': None,
                    'started_at': datetime.now().isoformat(),
                }

            # Update with provided kwargs
            update_data = {}
            if stage is not None:
                update_data['stage'] = stage
            if stage_label is not None:
                update_data['stage_label'] = stage_label
            update_data.update(kwargs)

            self.storage[user_id].update(update_data)

    def get_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Get current progress for a user.

        Args:
            user_id: Unique user identifier

        Returns:
            Dict containing progress state. Returns default state if user not found.
        """
        with self.lock:
            return dict(self.storage.get(user_id, {
                'stage': 'unknown',
                'stage_label': 'Preparing...',
                'interests': [],
                'retailers': {},
                'product_count': 0,
                'complete': False,
                'success': False,
                'error': None,
            }))

    def mark_complete(self, user_id: str, success: bool,
                     error: Optional[str] = None, **data) -> None:
        """
        Mark generation job as complete.

        Args:
            user_id: Unique user identifier
            success: Whether generation succeeded
            error: Optional error message if failed
            **data: Additional completion data (recommendations, etc.)
        """
        with self.lock:
            if user_id not in self.storage:
                self.storage[user_id] = {}

            self.storage[user_id].update({
                'complete': True,
                'success': success,
                'error': error,
                **data
            })

    def clear_progress(self, user_id: str) -> None:
        """
        Remove progress tracking for a user.

        Args:
            user_id: Unique user identifier
        """
        with self.lock:
            self.storage.pop(user_id, None)

    def update_retailer_progress(self, user_id: str, retailer: str,
                                 status: str, count: int = 0) -> None:
        """
        Update progress for a specific retailer search.

        Args:
            user_id: Unique user identifier
            retailer: Retailer name (e.g., 'Amazon', 'Etsy', 'eBay')
            status: Status ('searching', 'done', 'skipped')
            count: Number of products found
        """
        progress = self.get_progress(user_id)
        retailers = dict(progress.get('retailers', {}))
        retailers[retailer] = {'status': status, 'count': count}

        # Calculate total products
        total_products = sum(
            r.get('count', 0)
            for r in retailers.values()
            if r.get('status') == 'done'
        )

        self.set_progress(user_id, retailers=retailers, product_count=total_products)
