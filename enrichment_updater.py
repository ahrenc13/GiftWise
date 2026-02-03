"""
ENRICHMENT UPDATER
Weekly refresh tool that fetches fresh gift intelligence and stages for review.
Designed to fail gracefully - if updates fail, existing data still works.
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import time

class EnrichmentUpdater:
    """
    Fetches fresh gift intelligence from public sources.
    Stages updates for manual review before going live.
    """
    
    def __init__(self, staging_path='/mnt/user-data/staged_updates'):
        """
        Initialize updater.
        
        Args:
            staging_path: Where to store staged updates for review
        """
        self.staging_path = staging_path
        self.log_file = os.path.join(staging_path, 'update_log.json')
        self.staged_file = os.path.join(staging_path, 'pending_updates.json')
        
        # Create staging directory if it doesn't exist
        os.makedirs(staging_path, exist_ok=True)
        
        # Initialize log
        self.update_log = self._load_log()
    
    def _load_log(self) -> Dict:
        """Load update log history."""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            return {'updates': [], 'last_run': None}
        except Exception as e:
            print(f"Warning: Could not load log: {e}")
            return {'updates': [], 'last_run': None}
    
    def _save_log(self):
        """Save update log."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.update_log, f, indent=2)
        except Exception as e:
            print(f"Error saving log: {e}")
    
    def run_weekly_update(self) -> Dict:
        """
        Main update function - runs weekly to fetch fresh data.
        
        Returns:
            Summary of update results
        """
        print(f"\n{'='*60}")
        print(f"GIFTWISE INTELLIGENCE UPDATE")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'sources_attempted': [],
            'sources_successful': [],
            'sources_failed': [],
            'updates_staged': 0,
            'errors': []
        }
        
        # Attempt each data source
        staged_updates = {
            'interests': {},
            'demographics': {},
            'relationships': {},
            'trending': {},
            'metadata': {
                'update_date': datetime.now().isoformat(),
                'status': 'pending_review',
                'sources': []
            }
        }
        
        # Source 1: Reddit gift advice (web scraping, no auth needed)
        print("Fetching Reddit gift intelligence...")
        reddit_data = self._fetch_reddit_intelligence()
        if reddit_data:
            staged_updates['interests'].update(reddit_data.get('interests', {}))
            results['sources_successful'].append('reddit')
            results['sources_attempted'].append('reddit')
            staged_updates['metadata']['sources'].append('reddit')
        else:
            results['sources_failed'].append('reddit')
            results['sources_attempted'].append('reddit')
            results['errors'].append('Reddit scraping failed')
        
        # Source 2: Amazon trending (public bestseller pages)
        print("Fetching Amazon trending products...")
        amazon_data = self._fetch_amazon_trending()
        if amazon_data:
            staged_updates['trending'].update(amazon_data)
            results['sources_successful'].append('amazon')
            results['sources_attempted'].append('amazon')
            staged_updates['metadata']['sources'].append('amazon')
        else:
            results['sources_failed'].append('amazon')
            results['sources_attempted'].append('amazon')
            results['errors'].append('Amazon trending failed')
        
        # Source 3: Google Shopping trends (public data)
        print("Fetching Google Shopping trends...")
        google_data = self._fetch_google_trends()
        if google_data:
            staged_updates['trending'].update(google_data)
            results['sources_successful'].append('google')
            results['sources_attempted'].append('google')
            staged_updates['metadata']['sources'].append('google')
        else:
            results['sources_failed'].append('google')
            results['sources_attempted'].append('google')
            results['errors'].append('Google trends failed')
        
        # Save staged updates
        try:
            with open(self.staged_file, 'w') as f:
                json.dump(staged_updates, f, indent=2)
            results['updates_staged'] = len(staged_updates['interests']) + len(staged_updates['trending'])
            print(f"\n✓ Staged {results['updates_staged']} updates for review")
        except Exception as e:
            results['errors'].append(f"Failed to save staged updates: {e}")
            print(f"\n✗ Error staging updates: {e}")
        
        # Log this update run
        self.update_log['updates'].append(results)
        self.update_log['last_run'] = datetime.now().isoformat()
        self._save_log()
        
        # Print summary
        self._print_update_summary(results)
        
        return results
    
    def _fetch_reddit_intelligence(self) -> Optional[Dict]:
        """
        Fetch gift intelligence from Reddit.
        Uses web scraping of public pages (no auth needed).
        """
        try:
            # Use Reddit's public JSON API (no auth required)
            subreddits = [
                'GiftIdeas',
                'Gifts',
                'BuyItForLife',
                'ChristmasGifts'
            ]
            
            interests_data = {}
            
            for subreddit in subreddits:
                try:
                    # Fetch top posts from last month
                    url = f"https://www.reddit.com/r/{subreddit}/top.json?t=month&limit=25"
                    headers = {'User-Agent': 'GiftwiseBot/1.0'}
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code != 200:
                        continue
                    
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    # Extract gift advice from post titles and text
                    for post in posts:
                        post_data = post.get('data', {})
                        title = post_data.get('title', '').lower()
                        selftext = post_data.get('selftext', '').lower()
                        
                        # Look for interest keywords
                        # (In production, you'd have more sophisticated NLP here)
                        if 'basketball' in title or 'basketball' in selftext:
                            if 'basketball' not in interests_data:
                                interests_data['basketball'] = {
                                    'reddit_insights': [],
                                    'source': 'reddit',
                                    'update_date': datetime.now().isoformat()
                                }
                            insights = self._extract_insights(title, selftext)
                            interests_data['basketball']['reddit_insights'].extend(insights)
                    
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"  Warning: Failed to fetch r/{subreddit}: {e}")
                    continue
            
            if interests_data:
                print(f"  ✓ Fetched insights for {len(interests_data)} interests from Reddit")
                return {'interests': interests_data}
            else:
                print("  ✗ No Reddit data fetched")
                return None
                
        except Exception as e:
            print(f"  ✗ Reddit fetch failed: {e}")
            return None
    
    def _fetch_amazon_trending(self) -> Optional[Dict]:
        """
        Fetch trending products from Amazon public bestseller pages.
        """
        try:
            # Note: In production, you'd scrape Amazon's public bestseller pages
            # For now, this is a placeholder that shows the structure
            
            trending_data = {
                'electronics': {
                    'trending_items': [],
                    'source': 'amazon_bestsellers',
                    'update_date': datetime.now().isoformat()
                },
                'home': {
                    'trending_items': [],
                    'source': 'amazon_bestsellers',
                    'update_date': datetime.now().isoformat()
                }
            }
            
            # In production, you would:
            # 1. Fetch Amazon bestseller pages (public, no auth)
            # 2. Parse HTML to extract product names
            # 3. Categorize by interest area
            # 4. Return structured data
            
            # For now, returning None to indicate "not implemented yet"
            # This allows the system to work without Amazon data
            print("  ℹ Amazon trending not yet implemented (optional)")
            return None
            
        except Exception as e:
            print(f"  ✗ Amazon fetch failed: {e}")
            return None
    
    def _fetch_google_trends(self) -> Optional[Dict]:
        """
        Fetch Google Shopping trends (public data).
        """
        try:
            # Note: This would use Google Trends public data or Shopping insights
            # For now, placeholder to show structure
            
            # In production, you could use:
            # 1. pytrends library (unofficial Google Trends)
            # 2. Google Shopping public search pages
            # 3. Manual curation of trending gift categories
            
            print("  ℹ Google trends not yet implemented (optional)")
            return None
            
        except Exception as e:
            print(f"  ✗ Google trends failed: {e}")
            return None
    
    def _extract_insights(self, title: str, text: str) -> List[str]:
        """
        Extract actionable gift insights from Reddit post.
        Simple keyword-based extraction for now.
        """
        insights = []
        
        # Look for positive recommendations
        if any(word in title or word in text for word in ['recommend', 'suggest', 'best gift', 'perfect for']):
            # Extract the recommended item (simplified)
            # In production, you'd use NLP here
            pass
        
        # Look for warnings/anti-recommendations
        if any(word in title or word in text for word in ['avoid', 'don\'t buy', 'worst gift', 'mistake']):
            # Extract the warning
            pass
        
        return insights
    
    def _print_update_summary(self, results: Dict):
        """Print summary of update run."""
        print(f"\n{'='*60}")
        print("UPDATE SUMMARY")
        print(f"{'='*60}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Sources Attempted: {len(results['sources_attempted'])}")
        print(f"Sources Successful: {len(results['sources_successful'])}")
        print(f"Sources Failed: {len(results['sources_failed'])}")
        print(f"Updates Staged: {results['updates_staged']}")
        
        if results['sources_successful']:
            print(f"\n✓ Successful Sources:")
            for source in results['sources_successful']:
                print(f"  - {source}")
        
        if results['sources_failed']:
            print(f"\n✗ Failed Sources:")
            for source in results['sources_failed']:
                print(f"  - {source}")
        
        if results['errors']:
            print(f"\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")
        
        print(f"\n{'='*60}")
        print(f"Status: Updates staged at {self.staged_file}")
        print(f"Next Step: Review updates using update_reviewer.py")
        print(f"{'='*60}\n")


# =============================================================================
# SCHEDULER INTEGRATION
# =============================================================================

def schedule_weekly_updates():
    """
    Set up weekly update schedule.
    
    Options:
    1. Railway Cron (if supported)
    2. Flask-APScheduler (runs in your app)
    3. Manual trigger (run when you want)
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = BackgroundScheduler()
    
    # Schedule for every Sunday at 2 AM
    scheduler.add_job(
        func=run_update_job,
        trigger='cron',
        day_of_week='sun',
        hour=2,
        minute=0
    )
    
    scheduler.start()
    print("✓ Weekly updates scheduled for Sundays at 2:00 AM")


def run_update_job():
    """Job function for scheduler."""
    try:
        updater = EnrichmentUpdater()
        results = updater.run_weekly_update()
        
        # Log results
        print(f"Update job completed: {results['updates_staged']} updates staged")
        
    except Exception as e:
        print(f"Update job failed: {e}")


# =============================================================================
# MANUAL TRIGGER
# =============================================================================

def trigger_update_now():
    """
    Manually trigger an update right now.
    
    Usage:
        from enrichment_updater import trigger_update_now
        results = trigger_update_now()
    """
    updater = EnrichmentUpdater()
    return updater.run_weekly_update()


# =============================================================================
# INTEGRATION WITH FLASK APP
# =============================================================================

def init_updater_in_flask(app):
    """
    Initialize updater in your Flask app.
    
    Add this to giftwise_app.py:
        from enrichment_updater import init_updater_in_flask
        init_updater_in_flask(app)
    """
    # Only schedule updates in production
    if not app.debug:
        schedule_weekly_updates()
        print("✓ Enrichment updater initialized")
    else:
        print("ℹ Updater disabled in debug mode (manual trigger only)")


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        # Run update immediately
        print("Running update now...\n")
        results = trigger_update_now()
        
        if results['updates_staged'] > 0:
            print(f"\n✓ Success! {results['updates_staged']} updates staged for review")
            print(f"\nNext step: Run update_reviewer.py to review and approve updates")
        else:
            print("\n✗ No updates staged (all sources may have failed)")
            print("Check errors above for details")
    else:
        print("""
ENRICHMENT UPDATER
==================

Usage:
  python enrichment_updater.py --now    Run update immediately
  
Scheduled Updates:
  Updates run automatically every Sunday at 2:00 AM
  
Manual Trigger:
  from enrichment_updater import trigger_update_now
  results = trigger_update_now()
  
Integration:
  Add to giftwise_app.py:
    from enrichment_updater import init_updater_in_flask
    init_updater_in_flask(app)
        """)
