#!/usr/bin/env python3
"""
Batch convert templates to use base.html inheritance.
Removes duplicated nav/footer/Skimlinks, wraps content in {% extends %} and {% block %}.
"""

import os
import re
from pathlib import Path

TEMPLATES_DIR = Path("/home/user/GiftWise/templates")

# Templates to skip (already converted or special cases)
SKIP_TEMPLATES = {
    'base.html', 'nav.html', 'footer.html',
    'index.html',  # Already manually converted
    'recommendations.html',  # Complex template - needs manual conversion
    'New Text Document (2).txt', 'New Text Document.txt',  # Not templates
}

def extract_title(template_content: str) -> str:
    """Extract page title from template"""
    match = re.search(r'<title>(.*?)</title>', template_content, re.DOTALL)
    if match:
        title = match.group(1).strip()
        # Clean up multi-line titles
        title = ' '.join(title.split())
        return title
    return "Giftwise"

def extract_meta_description(template_content: str) -> str:
    """Extract meta description if present"""
    match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', template_content)
    if match:
        return match.group(1)
    return None

def extract_content(template_content: str) -> str:
    """Extract main content between body tags, removing nav/footer/scripts"""
    content = template_content

    # Remove everything before <body> (doctype, head, opening body tag)
    content = re.sub(r'<!DOCTYPE[^>]*>.*?<body[^>]*>', '', content, flags=re.DOTALL | re.IGNORECASE)

    # Remove navigation (various patterns)
    content = re.sub(r'<div\s+class="nav">.*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<nav[^>]*>.*?</nav>', '', content, flags=re.DOTALL)

    # Remove header with logo (from recommendations.html pattern)
    content = re.sub(r'<div\s+class="header">.*?</div>\s*</div>', '', content, flags=re.DOTALL)

    # Remove footer
    content = re.sub(r'<div\s+class="footer">.*?</div>\s*</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<footer[^>]*>.*?</footer>', '', content, flags=re.DOTALL)

    # Remove Skimlinks script (various patterns)
    content = re.sub(r'<script[^>]*skimlinks[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*298548X178612[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*src="https://s\.skimresources\.com[^"]*"[^>]*></script>', '', content, flags=re.DOTALL)

    # Remove closing body/html tags
    content = re.sub(r'</body>.*', '', content, flags=re.DOTALL | re.IGNORECASE)

    return content.strip()

def extract_extra_css(template_content: str) -> str:
    """Extract page-specific CSS that should go in extra_css block"""
    # Find style tag content
    match = re.search(r'<style[^>]*>(.*?)</style>', template_content, re.DOTALL)
    if match:
        css = match.group(1)
        # Remove global styles that are already in base.html
        # Keep only page-specific styles
        # This is a heuristic - manual review recommended

        # Remove common resets and global styles
        css = re.sub(r'\*\s*\{[^}]+\}', '', css)  # Remove * { } rules
        css = re.sub(r'body\s*\{[^}]+\}', '', css)  # Remove body { } rules (unless page-specific)

        # If there's significant CSS left, return it
        css = css.strip()
        if len(css) > 100:  # Arbitrary threshold
            return css

    return None

def convert_template(template_path: Path) -> str:
    """Convert template to use base.html inheritance"""
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    title = extract_title(content)
    meta_desc = extract_meta_description(content)
    main_content = extract_content(content)
    extra_css = extract_extra_css(content)

    # Build the new template
    new_template = f'{{% extends "base.html" %}}\n\n'
    new_template += f'{{% block title %}}{title}{{% endblock %}}\n\n'

    if meta_desc:
        new_template += f'{{% block meta %}}\n<meta name="description" content="{meta_desc}">\n{{% endblock %}}\n\n'

    if extra_css:
        new_template += f'{{% block extra_css %}}\n{extra_css}\n{{% endblock %}}\n\n'

    new_template += f'{{% block content %}}\n{main_content}\n{{% endblock %}}\n'

    return new_template

def main():
    templates = list(TEMPLATES_DIR.glob("*.html"))

    print(f"Found {len(templates)} total template files")
    print(f"Skipping {len(SKIP_TEMPLATES)} templates (already converted or special cases)")
    print()

    converted_count = 0
    failed_count = 0

    for template_path in sorted(templates):
        if template_path.name in SKIP_TEMPLATES:
            print(f"⊘ Skipping {template_path.name} (in skip list)")
            continue

        print(f"Converting {template_path.name}...", end=" ")

        try:
            new_content = convert_template(template_path)

            # Backup original
            backup_path = template_path.with_suffix('.html.bak')
            if not backup_path.exists():  # Don't overwrite existing backups
                template_path.rename(backup_path)

                # Write new version
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                converted_count += 1
                print(f"✓ Converted (backup: {backup_path.name})")
            else:
                print(f"⊘ Skipped (backup already exists)")

        except Exception as e:
            failed_count += 1
            print(f"✗ Failed: {e}")

    print()
    print(f"{'='*60}")
    print(f"✓ Converted: {converted_count} templates")
    print(f"✗ Failed: {failed_count} templates")
    print(f"⊘ Skipped: {len(SKIP_TEMPLATES)} templates")
    print(f"{'='*60}")
    print()
    print("Next steps:")
    print("1. Review converted templates (especially complex ones)")
    print("2. Test pages in browser to ensure they render correctly")
    print("3. Delete .bak files once you've verified everything works")
    print("4. Manually convert recommendations.html (too complex for automation)")

if __name__ == "__main__":
    main()
