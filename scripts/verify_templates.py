#!/usr/bin/env python3
"""
Verify that all templates are using the inheritance system correctly.
Run after conversion to check for issues.
"""

import re
from pathlib import Path

TEMPLATES_DIR = Path("/home/user/GiftWise/templates")

# Templates that should NOT use inheritance (they ARE the inheritance system)
SYSTEM_TEMPLATES = {'base.html', 'nav.html', 'footer.html'}

# Non-template files
IGNORE_FILES = {'New Text Document.txt', 'New Text Document (2).txt'}

def check_template(template_path: Path) -> dict:
    """Check a template for common issues"""
    issues = []
    warnings = []

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if using inheritance
    if not re.search(r'{%\s*extends\s+["\']base\.html["\']\s*%}', content):
        issues.append("Does not extend base.html")

    # Check for duplicate Skimlinks (should only be in base.html)
    if re.search(r'skimlinks', content, re.IGNORECASE):
        warnings.append("Contains Skimlinks snippet (should be in base.html only)")

    # Check for old-style nav/footer
    if re.search(r'<div\s+class=["\']nav["\']>', content):
        warnings.append("Contains old nav HTML (should use nav.html include)")

    if re.search(r'<div\s+class=["\']footer["\']>', content):
        warnings.append("Contains old footer HTML (should use footer.html include)")

    # Check for DOCTYPE (shouldn't be in child templates)
    if '<!DOCTYPE' in content:
        issues.append("Contains DOCTYPE (should only be in base.html)")

    # Check for closing </html> tag
    if '</html>' in content:
        issues.append("Contains closing </html> tag (should only be in base.html)")

    # Check for <head> tag
    if '<head>' in content or '<head ' in content:
        issues.append("Contains <head> tag (should only be in base.html)")

    return {
        'issues': issues,
        'warnings': warnings,
        'ok': len(issues) == 0
    }

def main():
    templates = list(TEMPLATES_DIR.glob("*.html"))

    print("=" * 70)
    print("TEMPLATE INHERITANCE VERIFICATION")
    print("=" * 70)
    print()

    total_count = 0
    ok_count = 0
    warning_count = 0
    error_count = 0

    for template_path in sorted(templates):
        # Skip system templates and non-templates
        if template_path.name in SYSTEM_TEMPLATES or template_path.name in IGNORE_FILES:
            continue

        total_count += 1
        result = check_template(template_path)

        if result['ok'] and not result['warnings']:
            ok_count += 1
            print(f"✓ {template_path.name}")
        elif result['ok'] and result['warnings']:
            warning_count += 1
            print(f"⚠ {template_path.name}")
            for warning in result['warnings']:
                print(f"    Warning: {warning}")
        else:
            error_count += 1
            print(f"✗ {template_path.name}")
            for issue in result['issues']:
                print(f"    ERROR: {issue}")
            for warning in result['warnings']:
                print(f"    Warning: {warning}")

    print()
    print("=" * 70)
    print(f"SUMMARY")
    print("=" * 70)
    print(f"Total templates checked: {total_count}")
    print(f"✓ OK: {ok_count}")
    print(f"⚠ Warnings: {warning_count}")
    print(f"✗ Errors: {error_count}")
    print()

    if error_count == 0 and warning_count == 0:
        print("🎉 All templates are using inheritance correctly!")
    elif error_count == 0:
        print("✓ No errors, but some warnings to review")
    else:
        print("⚠ Please fix the errors above")

    print()

if __name__ == "__main__":
    main()
