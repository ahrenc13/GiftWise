# GiftWise Implementation Session

You are implementing architectural fixes to GiftWise, an AI-powered gift recommendation app. An architecture audit has been completed and two reference documents are in the repo:

1. **`CLAUDE.md`** — Read this FIRST. It contains the business model, revenue architecture, development principles, and architectural patterns you must follow for every decision in this session. This is your north star.

2. **`IMPLEMENTATION_PLAN.md`** — Read this SECOND. It contains 11 ordered, scoped changes with exact file locations, before/after code blocks, and a verification checklist. This is your work order.

## Your Mission

Implement all 11 changes from IMPLEMENTATION_PLAN.md, in order, on the current branch. Commit after each logical group (you can batch changes that touch the same file). Push when complete.

## How to Execute

1. Read `CLAUDE.md` in full. Internalize the revenue model and the "Patterns to Follow / Avoid" sections. These constrain how you implement — not just what you implement.

2. Read `IMPLEMENTATION_PLAN.md` in full before starting any changes. Understand the dependency order.

3. Implement changes 1-11 sequentially. For each change:
   - Read the target file(s) first
   - Make ONLY the specified change — do not refactor surrounding code, add comments, add docstrings, or "improve" adjacent logic
   - If the line numbers in the plan are slightly off (due to earlier changes shifting lines), use the code snippets to find the correct location — the before/after blocks are the source of truth, not the line numbers
   - Verify the file still imports cleanly before moving to the next change

4. After all 11 changes, run the full verification checklist at the bottom of IMPLEMENTATION_PLAN.md.

5. Commit and push.

## Rules

- **Do not deviate from the plan.** These changes were designed together as a system. Skipping one or "improving" one can break the others.
- **Do not add features.** No extra error handling, no bonus refactors, no "while I'm here" improvements. The plan is the plan.
- **Do not add comments explaining changes.** The code should be self-evident. If you feel a comment is needed, the code is wrong.
- **Do not touch files not mentioned in the plan** unless an import is needed (like `defaultdict` in change 6).
- **If something in the plan seems wrong or unclear**, flag it and ask rather than improvising. The plan was written with full knowledge of the codebase.

## Context You Should Know

- The two most expensive bugs are missing thumbnails (Change 1) and 100% Amazon results (Changes 2-6). These are the highest priority.
- The thumbnail bug persists because previous fixes tried to make the LLM copy URLs better. The correct fix (Change 1) is to stop asking the LLM to copy URLs at all. Do not reintroduce any path where image_url flows through the curator's JSON output.
- The Amazon-dominance bug persists because previous fixes added prompt instructions. The correct fix (Changes 2-6) addresses root causes: thin snippets, positional bias, and no programmatic enforcement. Do not rely on prompt wording to guarantee source diversity.
- `CLAUDE.md` will load automatically in future sessions. Every pattern you follow now sets the standard. Every shortcut you take now becomes tech debt.

## After Implementation

Once all changes are verified and pushed, briefly summarize:
- How many files were modified
- Any issues encountered and how they were resolved
- Confirmation that all verification steps passed
