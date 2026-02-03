"""
UPDATE REVIEWER
Review and approve staged intelligence updates before they go live.
Provides command-line interface for reviewing, approving, or rejecting updates.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from difflib import unified_diff

class UpdateReviewer:
    """
    Review system for staged intelligence updates.
    
    Workflow:
    1. View pending updates
    2. Review changes (what's new, what changed)
    3. Approve or reject updates
    4. Approved updates become active
    5. Rejected updates are archived
    """
    
    def __init__(self, staging_path='/mnt/user-data/staged_updates'):
        """Initialize reviewer."""
        self.staging_path = staging_path
        self.pending_file = os.path.join(staging_path, 'pending_updates.json')
        self.approved_file = os.path.join(staging_path, 'approved_updates.json')
        self.rejected_file = os.path.join(staging_path, 'rejected_updates.json')
        self.history_file = os.path.join(staging_path, 'review_history.json')
        
        # Create directory if needed
        os.makedirs(staging_path, exist_ok=True)
        
        # Load data
        self.pending = self._load_json(self.pending_file)
        self.approved = self._load_json(self.approved_file)
        self.history = self._load_json(self.history_file, default={'reviews': []})
    
    def _load_json(self, filepath: str, default: Dict = None) -> Dict:
        """Load JSON file with fallback."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
            return default if default is not None else {}
        except Exception as e:
            print(f"Warning: Could not load {filepath}: {e}")
            return default if default is not None else {}
    
    def _save_json(self, data: Dict, filepath: str):
        """Save JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
    
    def has_pending_updates(self) -> bool:
        """Check if there are pending updates to review."""
        if not self.pending:
            return False
        
        # Check if any actual data exists
        has_data = (
            bool(self.pending.get('interests', {})) or
            bool(self.pending.get('demographics', {})) or
            bool(self.pending.get('relationships', {})) or
            bool(self.pending.get('trending', {}))
        )
        
        return has_data
    
    def show_pending_summary(self):
        """Display summary of pending updates."""
        print(f"\n{'='*70}")
        print("PENDING UPDATES SUMMARY")
        print(f"{'='*70}\n")
        
        if not self.has_pending_updates():
            print("No pending updates to review.")
            print(f"{'='*70}\n")
            return
        
        metadata = self.pending.get('metadata', {})
        print(f"Update Date: {metadata.get('update_date', 'Unknown')}")
        print(f"Sources: {', '.join(metadata.get('sources', []))}")
        print(f"Status: {metadata.get('status', 'Unknown')}\n")
        
        # Count updates by category
        interests_count = len(self.pending.get('interests', {}))
        demographics_count = len(self.pending.get('demographics', {}))
        relationships_count = len(self.pending.get('relationships', {}))
        trending_count = len(self.pending.get('trending', {}))
        
        print("Updates by Category:")
        if interests_count > 0:
            print(f"  • Interests: {interests_count} items")
        if demographics_count > 0:
            print(f"  • Demographics: {demographics_count} items")
        if relationships_count > 0:
            print(f"  • Relationships: {relationships_count} items")
        if trending_count > 0:
            print(f"  • Trending: {trending_count} items")
        
        total_updates = interests_count + demographics_count + relationships_count + trending_count
        print(f"\nTotal Updates: {total_updates}")
        print(f"{'='*70}\n")
    
    def show_detailed_changes(self):
        """Show detailed view of what changed."""
        print(f"\n{'='*70}")
        print("DETAILED CHANGES")
        print(f"{'='*70}\n")
        
        if not self.has_pending_updates():
            print("No pending updates to review.")
            return
        
        # Show interest updates
        interests = self.pending.get('interests', {})
        if interests:
            print(f"\n{'─'*70}")
            print("INTEREST UPDATES")
            print(f"{'─'*70}\n")
            
            for interest, data in list(interests.items())[:5]:  # Show first 5
                print(f"Interest: {interest}")
                
                # Check if this is new or updated
                if interest in self.approved.get('interests', {}):
                    print("  Status: UPDATED (existing interest)")
                    # Show diff
                    old_data = self.approved['interests'][interest]
                    self._show_diff(old_data, data)
                else:
                    print("  Status: NEW interest")
                    print(f"  Source: {data.get('source', 'Unknown')}")
                    if 'reddit_insights' in data:
                        print(f"  Reddit Insights: {len(data['reddit_insights'])} items")
                
                print()
            
            if len(interests) > 5:
                print(f"... and {len(interests) - 5} more interest updates\n")
        
        # Show trending updates
        trending = self.pending.get('trending', {})
        if trending:
            print(f"\n{'─'*70}")
            print("TRENDING UPDATES")
            print(f"{'─'*70}\n")
            
            for category, data in list(trending.items())[:3]:  # Show first 3
                print(f"Category: {category}")
                print(f"  Source: {data.get('source', 'Unknown')}")
                if 'trending_items' in data:
                    items = data['trending_items']
                    if items:
                        print(f"  Items: {', '.join(items[:5])}")
                print()
            
            if len(trending) > 3:
                print(f"... and {len(trending) - 3} more trending categories\n")
    
    def _show_diff(self, old_data: Dict, new_data: Dict):
        """Show differences between old and new data."""
        old_json = json.dumps(old_data, indent=2, sort_keys=True)
        new_json = json.dumps(new_data, indent=2, sort_keys=True)
        
        diff = unified_diff(
            old_json.splitlines(),
            new_json.splitlines(),
            lineterm='',
            n=0
        )
        
        diff_lines = list(diff)
        if len(diff_lines) > 5:
            print("  Changes:")
            for line in diff_lines[3:8]:  # Show first few changes
                if line.startswith('+') and not line.startswith('+++'):
                    print(f"    Added: {line[1:].strip()}")
                elif line.startswith('-') and not line.startswith('---'):
                    print(f"    Removed: {line[1:].strip()}")
    
    def approve_updates(self, categories: Optional[List[str]] = None):
        """
        Approve pending updates (all or specific categories).
        
        Args:
            categories: List of categories to approve, or None for all
                       Options: ['interests', 'demographics', 'relationships', 'trending']
        """
        if not self.has_pending_updates():
            print("No pending updates to approve.")
            return False
        
        # If no categories specified, approve all
        if categories is None:
            categories = ['interests', 'demographics', 'relationships', 'trending']
        
        # Merge approved updates with existing approved data
        for category in categories:
            if category in self.pending and self.pending[category]:
                if category not in self.approved:
                    self.approved[category] = {}
                
                # Merge new data into approved
                self.approved[category].update(self.pending[category])
                
                print(f"✓ Approved {len(self.pending[category])} {category} updates")
        
        # Update metadata
        self.approved['metadata'] = {
            'last_approved': datetime.now().isoformat(),
            'approved_categories': categories,
            'status': 'active'
        }
        
        # Save approved updates
        self._save_json(self.approved, self.approved_file)
        
        # Log to history
        self._log_review_action('approved', categories)
        
        # Clear pending (if all categories approved)
        if set(categories) == {'interests', 'demographics', 'relationships', 'trending'}:
            self._clear_pending()
        
        print(f"\n✓ Updates approved and now active!")
        print(f"  Saved to: {self.approved_file}")
        
        return True
    
    def reject_updates(self, reason: str = ""):
        """
        Reject pending updates.
        
        Args:
            reason: Optional reason for rejection
        """
        if not self.has_pending_updates():
            print("No pending updates to reject.")
            return False
        
        # Archive rejected updates
        rejected = {
            'data': self.pending,
            'rejected_date': datetime.now().isoformat(),
            'reason': reason
        }
        
        # Load existing rejected updates
        all_rejected = self._load_json(self.rejected_file, default={'rejected': []})
        all_rejected['rejected'].append(rejected)
        
        # Save rejected updates
        self._save_json(all_rejected, self.rejected_file)
        
        # Log to history
        self._log_review_action('rejected', reason=reason)
        
        # Clear pending
        self._clear_pending()
        
        print(f"\n✓ Updates rejected and archived")
        print(f"  Reason: {reason if reason else 'Not specified'}")
        
        return True
    
    def _clear_pending(self):
        """Clear pending updates file."""
        try:
            if os.path.exists(self.pending_file):
                os.remove(self.pending_file)
            self.pending = {}
        except Exception as e:
            print(f"Warning: Could not clear pending file: {e}")
    
    def _log_review_action(self, action: str, categories: Optional[List[str]] = None, reason: str = ""):
        """Log review action to history."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'categories': categories or [],
            'reason': reason
        }
        
        self.history['reviews'].append(log_entry)
        self._save_json(self.history, self.history_file)
    
    def show_review_history(self, limit: int = 10):
        """Show recent review history."""
        print(f"\n{'='*70}")
        print("REVIEW HISTORY")
        print(f"{'='*70}\n")
        
        reviews = self.history.get('reviews', [])
        
        if not reviews:
            print("No review history available.")
            return
        
        # Show most recent reviews
        recent = reviews[-limit:]
        for review in reversed(recent):
            timestamp = review.get('timestamp', 'Unknown')
            action = review.get('action', 'Unknown')
            categories = review.get('categories', [])
            reason = review.get('reason', '')
            
            print(f"Date: {timestamp}")
            print(f"Action: {action.upper()}")
            if categories:
                print(f"Categories: {', '.join(categories)}")
            if reason:
                print(f"Reason: {reason}")
            print(f"{'─'*70}\n")


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def interactive_review():
    """Interactive command-line review interface."""
    reviewer = UpdateReviewer()
    
    # Check for pending updates
    if not reviewer.has_pending_updates():
        print("\nNo pending updates to review.")
        print("Run enrichment_updater.py to fetch fresh updates.\n")
        return
    
    # Show summary
    reviewer.show_pending_summary()
    
    # Ask if user wants details
    while True:
        response = input("Show detailed changes? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            reviewer.show_detailed_changes()
            break
        elif response in ['n', 'no']:
            break
    
    # Ask for approval
    print(f"\n{'='*70}")
    print("REVIEW DECISION")
    print(f"{'='*70}\n")
    print("Options:")
    print("  1. Approve all updates")
    print("  2. Approve specific categories")
    print("  3. Reject all updates")
    print("  4. Cancel (review later)\n")
    
    choice = input("Your choice (1-4): ").strip()
    
    if choice == '1':
        reviewer.approve_updates()
    elif choice == '2':
        print("\nAvailable categories:")
        print("  - interests")
        print("  - demographics")
        print("  - relationships")
        print("  - trending")
        categories_input = input("\nEnter categories to approve (comma-separated): ").strip()
        categories = [c.strip() for c in categories_input.split(',')]
        reviewer.approve_updates(categories=categories)
    elif choice == '3':
        reason = input("\nReason for rejection (optional): ").strip()
        reviewer.reject_updates(reason=reason)
    elif choice == '4':
        print("\nReview cancelled. Updates remain pending.")
    else:
        print("\nInvalid choice. Review cancelled.")


# =============================================================================
# PROGRAMMATIC INTERFACE
# =============================================================================

def auto_approve_updates() -> bool:
    """
    Automatically approve all pending updates (for moving from B to A mode).
    
    Usage:
        from update_reviewer import auto_approve_updates
        success = auto_approve_updates()
    """
    reviewer = UpdateReviewer()
    if reviewer.has_pending_updates():
        return reviewer.approve_updates()
    return False


def quick_review() -> Dict:
    """
    Quick review - just show summary and return data for programmatic use.
    
    Returns:
        Dictionary with pending update info
    """
    reviewer = UpdateReviewer()
    
    return {
        'has_pending': reviewer.has_pending_updates(),
        'interests_count': len(reviewer.pending.get('interests', {})),
        'demographics_count': len(reviewer.pending.get('demographics', {})),
        'relationships_count': len(reviewer.pending.get('relationships', {})),
        'trending_count': len(reviewer.pending.get('trending', {})),
        'update_date': reviewer.pending.get('metadata', {}).get('update_date', 'Unknown'),
        'sources': reviewer.pending.get('metadata', {}).get('sources', [])
    }


# =============================================================================
# FLASK INTEGRATION
# =============================================================================

def add_review_route(app):
    """
    Add review interface as a Flask route.
    
    Usage in giftwise_app.py:
        from update_reviewer import add_review_route
        add_review_route(app)
    
    Accessible at: /admin/review-updates
    """
    from flask import render_template, request, redirect, url_for, flash
    
    @app.route('/admin/review-updates', methods=['GET', 'POST'])
    def review_updates():
        """Web interface for reviewing updates."""
        reviewer = UpdateReviewer()
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'approve':
                reviewer.approve_updates()
                flash('Updates approved successfully!', 'success')
            elif action == 'reject':
                reason = request.form.get('reason', '')
                reviewer.reject_updates(reason=reason)
                flash('Updates rejected', 'info')
            
            return redirect(url_for('review_updates'))
        
        # GET request - show review interface
        has_pending = reviewer.has_pending_updates()
        summary = quick_review() if has_pending else None
        
        return render_template(
            'admin/review_updates.html',
            has_pending=has_pending,
            summary=summary
        )


# =============================================================================
# MAIN INTERFACE
# =============================================================================

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--summary':
            # Just show summary
            reviewer = UpdateReviewer()
            reviewer.show_pending_summary()
        
        elif command == '--details':
            # Show detailed changes
            reviewer = UpdateReviewer()
            reviewer.show_pending_summary()
            reviewer.show_detailed_changes()
        
        elif command == '--approve':
            # Quick approve
            reviewer = UpdateReviewer()
            reviewer.approve_updates()
        
        elif command == '--reject':
            # Quick reject
            reason = sys.argv[2] if len(sys.argv) > 2 else ""
            reviewer = UpdateReviewer()
            reviewer.reject_updates(reason=reason)
        
        elif command == '--history':
            # Show history
            reviewer = UpdateReviewer()
            reviewer.show_review_history()
        
        elif command == '--auto':
            # Enable auto-approval mode (A mode)
            print("\n⚠️  AUTO-APPROVAL MODE")
            print("="*70)
            print("This will automatically approve all future updates.")
            print("Updates will go live without manual review.")
            confirm = input("\nAre you sure? (yes/no): ").strip().lower()
            
            if confirm == 'yes':
                # Create marker file for auto-approval
                marker = '/mnt/user-data/staged_updates/.auto_approve'
                with open(marker, 'w') as f:
                    f.write(datetime.now().isoformat())
                print("\n✓ Auto-approval enabled")
                print("To disable, delete: " + marker)
            else:
                print("\nCancelled")
        
        else:
            print(f"Unknown command: {command}")
    
    else:
        # Interactive mode
        interactive_review()
