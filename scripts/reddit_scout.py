#!/usr/bin/env python3
"""
Reddit Gift Scout — finds r/GiftIdeas posts worth replying to and drafts
responses in Chad's voice. Output is a markdown file for manual review.
Nothing is posted automatically.

Setup:
    pip install praw
    Set in .env:
        REDDIT_CLIENT_ID
        REDDIT_CLIENT_SECRET
        REDDIT_USERNAME       (your Reddit handle, no u/)
        REDDIT_PASSWORD
        REDDIT_USER_AGENT     (e.g. "GiftWise Scout/1.0 by u/yourhandle")
        ANTHROPIC_API_KEY     (already set)

Usage:
    python scripts/reddit_scout.py
    python scripts/reddit_scout.py --limit 10 --hours 48
    python scripts/reddit_scout.py --dry-run   # fetch posts, skip drafting
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

try:
    import praw
except ImportError:
    print("PRAW not installed. Run: pip install praw")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("anthropic not installed. Run: pip install anthropic")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SUBREDDIT = "GiftIdeas"

# Flairs worth targeting. None = accept all flairs.
TARGET_FLAIRS = None  # will auto-detect on first run and log what's available

# Skip posts with more than this many comments — too buried to matter
MAX_COMMENTS = 40

# Skip posts older than this many hours
DEFAULT_HOURS = 24

# Max posts to process per run
DEFAULT_LIMIT = 20

# Max drafts to output (pick the best candidates)
MAX_DRAFTS = 5

# Minimum post score to bother with (upvotes - downvotes)
MIN_SCORE = 0

# Output dir for draft files
OUTPUT_DIR = Path(__file__).parent.parent / "scripts" / "drafts"

# Claude model for drafting
DRAFT_MODEL = os.getenv("CLAUDE_PROFILE_MODEL", "claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# Voice prompt — grounded in VOICE.md
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are drafting Reddit replies for Chad, who built GiftWise (giftwise.fit) — an AI gift recommendation tool that analyzes someone's social media to find gifts that actually fit them.

Chad's voice on Reddit:
- Short. 3-6 sentences max. Reddit isn't a blog.
- Specific to the actual situation in the post. Reference details they mentioned — the person's hobby, the budget, the relationship. Never generic.
- Genuinely helpful first. If there's a concrete suggestion worth making, make it before mentioning any tool.
- GiftWise mention is casual and optional-feeling. The framing: "take it or leave it, but I built something for exactly this." Never "check out my tool!" — more like mentioning something that exists that might help.
- No performed warmth. No "what a thoughtful gift giver you are!" No "hope this helps!"
- No em dashes. No bullet lists. Plain prose.
- Don't restate their situation back to them. They know what they wrote.
- If the post has enough detail (social media handle or rich description of interests), lead with GiftWise since it's directly applicable. If thin on details, lead with a concrete suggestion and mention GiftWise as a way to go deeper.
- End flat — no sign-off, no "good luck!", no conclusion sentence that restates what you just said.

GiftWise description for when you mention it:
"I built a tool — giftwise.fit — that pulls someone's Instagram or TikTok and turns their actual interests into a gift list. Take it or leave it, but it's free and it's fast."

Adapt that line to fit the situation. Don't always use the exact same phrasing."""


def build_draft_prompt(post_title: str, post_body: str, flair: str) -> str:
    return f"""Draft a Reddit reply to this r/GiftIdeas post.

POST TITLE: {post_title}
FLAIR: {flair or "none"}
POST BODY:
{post_body.strip() if post_body.strip() else "(no body — title only)"}

Draft a reply in Chad's voice. Be specific to this situation. 3-6 sentences. If there's a concrete gift suggestion that fits, lead with it. Mention GiftWise naturally if it's relevant. Don't be promotional."""


# ---------------------------------------------------------------------------
# Scoring — which posts are worth drafting for
# ---------------------------------------------------------------------------

SKIP_KEYWORDS = [
    "already bought", "already ordered", "already got", "i got them",
    "update:", "[update]", "thank you everyone", "thanks everyone",
    "giveaway", "i am a bot", "automoderator",
]

GOOD_SIGNALS = [
    "instagram", "tiktok", "social media", "handle", "profile",
    "she loves", "he loves", "they love", "obsessed with", "into",
    "hobby", "hobbies", "passion", "fanatic", "collector",
]


def score_post(post) -> tuple[int, str]:
    """Return (score, reason). Higher = more worth replying to."""
    title_lower = post.title.lower()
    body_lower = (post.selftext or "").lower()
    combined = title_lower + " " + body_lower

    # Hard skips
    for kw in SKIP_KEYWORDS:
        if kw in combined:
            return -1, f"skip keyword: '{kw}'"

    if post.num_comments > MAX_COMMENTS:
        return -1, f"too many comments ({post.num_comments})"

    if "[deleted]" in (post.selftext or "") or "[removed]" in (post.selftext or ""):
        return -1, "deleted/removed"

    score = 0

    # Prefer posts with some body text (more context = better draft)
    if len(post.selftext or "") > 100:
        score += 2
    elif len(post.selftext or "") > 20:
        score += 1

    # Good signals boost priority
    for signal in GOOD_SIGNALS:
        if signal in combined:
            score += 1

    # Budget mentioned — more context
    if any(w in combined for w in ["$", "budget", "spend", "price"]):
        score += 1

    # Relationship context
    if any(w in combined for w in ["husband", "wife", "boyfriend", "girlfriend",
                                    "partner", "dad", "mom", "brother", "sister",
                                    "friend", "coworker", "boss"]):
        score += 1

    # Low engagement = our reply will be more visible
    if post.num_comments == 0:
        score += 2
    elif post.num_comments < 5:
        score += 1

    return score, "ok"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fetch_posts(reddit, hours: int, limit: int) -> list:
    """Fetch recent posts from the subreddit."""
    subreddit = reddit.subreddit(SUBREDDIT)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    posts = []
    seen_flairs = set()

    print(f"Fetching new posts from r/{SUBREDDIT} (last {hours}h)...")

    for post in subreddit.new(limit=limit * 3):  # fetch extra, we'll filter
        created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
        if created < cutoff:
            break

        flair = post.link_flair_text or ""
        seen_flairs.add(flair or "(none)")

        score, reason = score_post(post)
        if score < 0:
            continue

        posts.append({
            "id": post.id,
            "title": post.title,
            "body": post.selftext or "",
            "flair": flair,
            "url": f"https://reddit.com{post.permalink}",
            "score": post.score,
            "comments": post.num_comments,
            "created": created,
            "priority": score,
        })

    if seen_flairs:
        print(f"Flairs seen: {', '.join(sorted(seen_flairs))}")

    # Sort by priority desc, then recency
    posts.sort(key=lambda p: (p["priority"], p["created"]), reverse=True)
    return posts[:limit]


def draft_reply(client: anthropic.Anthropic, post: dict) -> str:
    """Call Claude to draft a reply."""
    prompt = build_draft_prompt(post["title"], post["body"], post["flair"])
    message = client.messages.create(
        model=DRAFT_MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def write_output(posts_with_drafts: list, hours: int) -> Path:
    """Write the draft file and return its path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    outfile = OUTPUT_DIR / f"drafts_{timestamp}.md"

    lines = [
        f"# r/GiftIdeas Scout — {datetime.now().strftime('%b %d, %Y %I:%M %p')}",
        f"Last {hours}h | {len(posts_with_drafts)} drafts",
        "",
        "---",
        "",
    ]

    for i, item in enumerate(posts_with_drafts, 1):
        post = item["post"]
        draft = item.get("draft", "(dry run — no draft generated)")

        age_hours = (datetime.now(timezone.utc) - post["created"]).total_seconds() / 3600
        age_str = f"{age_hours:.0f}h ago"

        lines += [
            f"## {i}. {post['title']}",
            f"",
            f"**URL:** {post['url']}  ",
            f"**Flair:** {post['flair'] or '(none)'}  ",
            f"**Stats:** {post['score']} pts · {post['comments']} comments · {age_str}  ",
            f"**Priority score:** {post['priority']}",
            f"",
        ]

        if post["body"]:
            body_preview = post["body"][:300].replace("\n", " ").strip()
            if len(post["body"]) > 300:
                body_preview += "..."
            lines += [f"> {body_preview}", ""]

        lines += [
            "**DRAFT REPLY:**",
            "",
            draft,
            "",
            "---",
            "",
        ]

    outfile.write_text("\n".join(lines))
    return outfile


def main():
    parser = argparse.ArgumentParser(description="Reddit Gift Scout")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Max posts to evaluate (default {DEFAULT_LIMIT})")
    parser.add_argument("--hours", type=int, default=DEFAULT_HOURS,
                        help=f"How many hours back to look (default {DEFAULT_HOURS})")
    parser.add_argument("--drafts", type=int, default=MAX_DRAFTS,
                        help=f"Max drafts to generate (default {MAX_DRAFTS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and score posts but skip Claude drafting")
    args = parser.parse_args()

    # Validate env
    required = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
                 "REDDIT_USERNAME", "REDDIT_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        print("Set these in your .env file.")
        sys.exit(1)

    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        print("Missing ANTHROPIC_API_KEY — needed for drafting. Use --dry-run to skip.")
        sys.exit(1)

    # Connect to Reddit
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT",
                             f"GiftWise Scout/1.0 by u/{os.getenv('REDDIT_USERNAME', 'unknown')}"),
    )

    # Verify auth
    try:
        me = reddit.user.me()
        print(f"Logged in as u/{me.name}")
    except Exception as e:
        print(f"Reddit auth failed: {e}")
        sys.exit(1)

    # Fetch posts
    posts = fetch_posts(reddit, hours=args.hours, limit=args.limit)

    if not posts:
        print("No qualifying posts found.")
        return

    print(f"\nFound {len(posts)} qualifying posts. Top {args.drafts} by priority:")
    for p in posts[:args.drafts]:
        print(f"  [{p['priority']}] {p['title'][:70]} ({p['comments']} comments)")

    # Draft replies
    draft_targets = posts[:args.drafts]
    posts_with_drafts = []

    if args.dry_run:
        print("\n--dry-run: skipping Claude drafting")
        posts_with_drafts = [{"post": p} for p in draft_targets]
    else:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        print(f"\nDrafting {len(draft_targets)} replies...")

        for i, post in enumerate(draft_targets, 1):
            print(f"  {i}/{len(draft_targets)}: {post['title'][:60]}...")
            try:
                draft = draft_reply(client, post)
                posts_with_drafts.append({"post": post, "draft": draft})
            except Exception as e:
                print(f"    Draft failed: {e}")
                posts_with_drafts.append({"post": post, "draft": f"(draft failed: {e})"})

            # Be polite to the API
            if i < len(draft_targets):
                time.sleep(1)

    # Write output
    outfile = write_output(posts_with_drafts, hours=args.hours)
    print(f"\nDrafts written to: {outfile}")
    print("Review, edit, and post manually. Nothing was submitted to Reddit.")


if __name__ == "__main__":
    main()
