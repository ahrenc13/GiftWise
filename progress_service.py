"""
Progress Tracking Service
Centralized progress tracking for recommendation generation pipeline.

Previously stored state in an in-memory dict — invisible across Gunicorn
worker processes. Now delegates all reads/writes to progress_store (SQLite,
WAL mode) so any worker can read progress written by any other worker.

Author: Chad + Claude
Date: February 2026
"""

import progress_store


class ProgressTracker:
    """
    Cross-process progress tracker for recommendation generation.

    All state is persisted via progress_store (SQLite/WAL), so reads
    from any Gunicorn worker reflect writes from any other worker.

    Usage:
        tracker = ProgressTracker()
        tracker.set_progress('user_123', stage='searching', stage_label='Searching stores...')
        progress = tracker.get_progress('user_123')
        tracker.mark_complete('user_123', success=True)
    """

    def __init__(self, storage=None):
        """
        storage param kept for backward compatibility — no longer used.
        State is stored in SQLite via progress_store, not in-memory.
        """
        pass

    def set_progress(self, user_id: str, stage: str = None,
                     stage_label: str = None, **kwargs) -> None:
        """Update progress for a user."""
        if stage is not None:
            kwargs['stage'] = stage
        if stage_label is not None:
            kwargs['stage_label'] = stage_label
        progress_store.set_progress(user_id, **kwargs)

    def get_progress(self, user_id: str) -> dict:
        """Get current progress for a user."""
        return progress_store.get_progress(user_id)

    def mark_complete(self, user_id: str, success: bool,
                      error: str = None, **data) -> None:
        """Mark generation job as complete."""
        progress_store.set_progress(
            user_id,
            complete=True,
            success=success,
            error=error,
            **data
        )

    def clear_progress(self, user_id: str) -> None:
        """Remove progress tracking for a user."""
        progress_store.clear_progress(user_id)

    def update_retailer_progress(self, user_id: str, retailer: str,
                                  status: str, count: int = 0) -> None:
        """Update progress for a specific retailer search."""
        # Write the retailer delta — progress_store merges into existing dict
        progress_store.set_progress(
            user_id,
            retailers={retailer: {'status': status, 'count': count}}
        )
        # Recalculate total product count from all completed retailers
        current = progress_store.get_progress(user_id)
        total = sum(
            r.get('count', 0)
            for r in current.get('retailers', {}).values()
            if r.get('status') == 'done'
        )
        progress_store.set_progress(user_id, product_count=total)
