#!/usr/bin/env python3
"""
Reddit Gift Scout — finds posts worth replying to or DMing and drafts
responses in Chad's voice. Output is a markdown file for manual review.
Nothing is posted or sent automatically.

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
    python scripts/reddit_scout.py                         # comment drafts, default subs
    python scripts/reddit_scout.py --mode dms              # DM drafts instead
    python scripts/reddit_scout.py --sub gifts --hours 48  # specific sub, longer window
    python scripts/reddit_scout.py --dry-run               # fetch + score, skip drafting

Modes:
    comments  — draft public replies (default). Use for subs where you haven't
                been flagged. r/GiftIdeas is BANNED for this account — do not use.
    dms       — draft private messages to post authors. Shorter, more direct.
                Appropriate for r/GiftIdeas posters (ban covers the sub, not DMs).
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
# Subreddit config
# ---------------------------------------------------------------------------

# ⚠️  BANNED FROM COMMENTING: r/GiftIdeas permanently banned this account
# for self-promotion. Do NOT add it to COMMENT_SUBREDDITS. DMs to individual
# posters from that sub are fine (ban covers the community, not private messages).

COMMENT_SUBREDDITS = [
    "gifts",              # smaller, less moderated than GiftIdeas
    "relationship_advice", # contextual — only reply when gift problem is explicit
]

DM_SUBREDDITS = [
    "GiftIdeas",          # banned for comments; DMs to posters are fine
    "gifts",
    "Mommit",             # mothers posting about what they want
    "daddit",             # dads asking what to get partners/moms
    "weddingplanning",    # people shopping for multiple people at once
    "AskWomen",
    "AskMen",
]

# Default sub for a single-sub run (--sub flag)
DEFAULT_SUBREDDIT = "gifts"

# Skip posts with more than this many comments — too buried to matter
MAX_COMMENTS = 40

# Skip posts older than this many hours
DEFAULT_HOURS = 24

# Max posts to process per run (per subreddit)
DEFAULT_LIMIT = 20

# Max drafts to output (pick the best candidates across all subs)
MAX_DRAFTS = 5

# Minimum post score to bother with (upvotes - downvotes)
MIN_SCORE = 0

# Output dir for draft files
OUTPUT_DIR = Path(__file__).parent.parent / "scripts" / "drafts"

# Claude model for drafting
DRAFT_MODEL = os.getenv("CLAUDE_PROFILE_MODEL", "claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# Voice prompts — grounded in VOICE.md
# ---------------------------------------------------------------------------

def get_comment_prompt(ref_slug: str) -> str:
    return f"""You are drafting Reddit replies for Chad, who built GiftWise (giftwise.fit) — an AI gift recommendation tool that analyzes someone's social media to find gifts that actually fit them.

Chad's voice on Reddit (comments):
- Short. 3-6 sentences max.
- Specific to the actual situation in the post. Reference details they mentioned. Never generic.
- Genuinely helpful first. Concrete suggestion before any tool mention.
- Never speak as an authority on a recipient you've never met. Offer possibilities, not verdicts. Use "I think", "I figure", "maybe", "I sometimes wonder if".
- GiftWise mention is casual: "I found a tool at giftwise.fit/?ref={ref_slug} where you paste their handle and it builds a list from what they actually post about. it's free as far as I can tell"
- Typographic looseness is intentional — inconsistent caps, no trailing period. Reads as human, not bot.
- Self-referential entry works well: start with something personal before the suggestion.
- No performed warmth. No em dashes. No bullet lists. No conclusion sentence.
- End flat.

Adapt the GiftWise line to fit the situation. Always include the ?ref={ref_slug} parameter. Don't mention it if the post has a clear specific answer that doesn't need the tool."""


def get_dm_prompt(ref_slug: str) -> str:
    return f"""You are drafting Reddit DMs for Chad, who built GiftWise (giftwise.fit) — an AI gift recommendation tool that analyzes someone's social media to find gifts that actually fit them.

Chad's voice in DMs (private messages to post authors):
- Even shorter than comment replies. 2-4 sentences.
- Lead with something specific from their post that proves you read it. One observation or concrete suggestion.
- More direct than a public comment — no audience to perform for.
- Tool mention is optional and natural: "I built something that might help with this if they have any social media — giftwise.fit/?ref={ref_slug}"
- Never speak as an authority on their person. Offer, don't tell.
- No opener like "Hey!" or "Hi there". Just start with the thing.
- No sign-off. End when the thought is done.
- Lowercase starts are fine. No trailing period on the last line.

Only mention GiftWise if it's genuinely useful to their situation. If the post has a clear specific answer, give it and stop."""


def build_draft_prompt(post: dict, mode: str) -> str:
    sub = post.get("subreddit", "Reddit")
    return f"""Draft a Reddit {mode} to this r/{sub} post.

POST TITLE: {post['title']}
FLAIR: {post.get('flair') or 'none'}
POST BODY:
{post['body'].strip() if post['body'].strip() else "(no body — title only)"}

Draft in Chad's voice. Be specific to this situation. {"3-6 sentences for a comment." if mode == "reply" else "2-4 sentences for a DM."} Lead with something concrete. Mention GiftWise only if genuinely relevant."""


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

# Seasonal boost — Mother's Day window (April–May)
MOTHERS_DAY_SIGNALS = [
    "mom", "mother", "mum", "mother's day", "mothers day",
    "my mom", "for my mom", "gift for mom",
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

    # Seasonal boost
    for signal in MOTHERS_DAY_SIGNALS:
        if signal in combined:
            score += 2
            break  # only boost once

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

def fetch_posts(reddit, subreddit_name: str, hours: int, limit: int) -> list:
    """Fetch recent posts from a subreddit."""
    subreddit = reddit.subreddit(subreddit_name)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    ref_slug = f"reddit_{subreddit_name.lower()}"

    posts = []
    seen_flairs = set()

    print(f"Fetching r/{subreddit_name} (last {hours}h)...")

    for post in subreddit.new(limit=limit * 3):
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
            "author": str(post.author) if post.author else "[deleted]",
            "subreddit": subreddit_name,
            "ref_slug": ref_slug,
            "score": post.score,
            "comments": post.num_comments,
            "created": created,
            "priority": score,
        })

    if seen_flairs and len(seen_flairs) > 1:
        print(f"  Flairs: {', '.join(sorted(seen_flairs))}")

    return posts


def draft_reply(client: anthropic.Anthropic, post: dict, mode: str) -> str:
    """Call Claude to draft a comment reply or DM."""
    ref_slug = post.get("ref_slug", "reddit")
    system = get_comment_prompt(ref_slug) if mode == "comments" else get_dm_prompt(ref_slug)
    prompt = build_draft_prompt(post, "reply" if mode == "comments" else "DM")

    message = client.messages.create(
        model=DRAFT_MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def write_output(posts_with_drafts: list, hours: int, mode: str) -> Path:
    """Write the draft file and return its path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    outfile = OUTPUT_DIR / f"drafts_{mode}_{timestamp}.md"

    mode_label = "Comment Replies" if mode == "comments" else "DM Drafts"
    lines = [
        f"# GiftWise Reddit Scout — {mode_label}",
        f"Generated: {datetime.now().strftime('%b %d, %Y %I:%M %p')} | Last {hours}h | {len(posts_with_drafts)} drafts",
        "",
        "---",
        "",
    ]

    for i, item in enumerate(posts_with_drafts, 1):
        post = item["post"]
        draft = item.get("draft", "(dry run — no draft generated)")

        age_hours = (datetime.now(timezone.utc) - post["created"]).total_seconds() / 3600
        age_str = f"{age_hours:.0f}h ago"

        dm_note = f" | DM u/{post['author']}" if mode == "dms" else ""

        lines += [
            f"## {i}. [{post['subreddit']}] {post['title']}",
            f"",
            f"**URL:** {post['url']}{dm_note}  ",
            f"**Flair:** {post['flair'] or '(none)'}  ",
            f"**Stats:** {post['score']} pts · {post['comments']} comments · {age_str}  ",
            f"**Priority score:** {post['priority']} | **Ref:** ?ref={post['ref_slug']}",
            f"",
        ]

        if post["body"]:
            body_preview = post["body"][:300].replace("\n", " ").strip()
            if len(post["body"]) > 300:
                body_preview += "..."
            lines += [f"> {body_preview}", ""]

        lines += [
            f"**DRAFT {'REPLY' if mode == 'comments' else 'DM'}:**",
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
    parser.add_argument("--mode", choices=["comments", "dms"], default="comments",
                        help="Draft public comment replies or private DMs (default: comments)")
    parser.add_argument("--sub", type=str, default=None,
                        help="Target a single subreddit (overrides default list)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Max posts to evaluate per subreddit (default {DEFAULT_LIMIT})")
    parser.add_argument("--hours", type=int, default=DEFAULT_HOURS,
                        help=f"How many hours back to look (default {DEFAULT_HOURS})")
    parser.add_argument("--drafts", type=int, default=MAX_DRAFTS,
                        help=f"Max drafts to generate total (default {MAX_DRAFTS})")
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

    # Determine which subs to scan
    if args.sub:
        subreddits = [args.sub]
    elif args.mode == "dms":
        subreddits = DM_SUBREDDITS
    else:
        subreddits = COMMENT_SUBREDDITS

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

    # Fetch from all target subs, merge, re-sort by priority
    all_posts = []
    for sub in subreddits:
        posts = fetch_posts(reddit, sub, hours=args.hours, limit=args.limit)
        all_posts.extend(posts)
        print(f"  → {len(posts)} qualifying posts from r/{sub}")

    if not all_posts:
        print("No qualifying posts found.")
        return

    all_posts.sort(key=lambda p: (p["priority"], p["created"]), reverse=True)
    top = all_posts[:args.drafts]

    print(f"\nTop {len(top)} across all subs:")
    for p in top:
        print(f"  [{p['priority']}] r/{p['subreddit']}: {p['title'][:60]} ({p['comments']} comments)")

    # Draft replies
    posts_with_drafts = []

    if args.dry_run:
        print(f"\n--dry-run: skipping Claude drafting")
        posts_with_drafts = [{"post": p} for p in top]
    else:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        print(f"\nDrafting {len(top)} {'replies' if args.mode == 'comments' else 'DMs'}...")

        for i, post in enumerate(top, 1):
            print(f"  {i}/{len(top)}: r/{post['subreddit']} — {post['title'][:55]}...")
            try:
                draft = draft_reply(client, post, args.mode)
                posts_with_drafts.append({"post": post, "draft": draft})
            except Exception as e:
                print(f"    Draft failed: {e}")
                posts_with_drafts.append({"post": post, "draft": f"(draft failed: {e})"})

            if i < len(top):
                time.sleep(1)

    # Write output
    outfile = write_output(posts_with_drafts, hours=args.hours, mode=args.mode)
    print(f"\nDrafts written to: {outfile}")
    if args.mode == "dms":
        print("Review and send manually via Reddit. Nothing was submitted.")
    else:
        print("Review, edit, and post manually. Nothing was submitted to Reddit.")


if __name__ == "__main__":
    main()
