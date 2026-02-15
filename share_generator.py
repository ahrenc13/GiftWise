"""
SHARE GENERATOR
Creates shareable images and story cards for gift recommendations.

Uses pure SVG (no Pillow dependency). The /api/generate-share-image endpoint
returns an SVG that the browser can render or convert to PNG via canvas.

Author: Chad + Claude
Date: February 2026
"""

import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_share_image(user_name="Friend", rec_count=10, relationship="someone special"):
    """
    Generate a shareable card as SVG bytes.

    Returns:
        BytesIO containing SVG data (served as image/svg+xml)
    """
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f43f5e"/>
      <stop offset="100%" stop-color="#be123c"/>
    </linearGradient>
  </defs>
  <rect width="600" height="400" rx="20" fill="url(#bg)"/>
  <text x="300" y="80" text-anchor="middle" font-family="sans-serif" font-size="48" fill="white" font-weight="800">Giftwise</text>
  <text x="300" y="160" text-anchor="middle" font-family="sans-serif" font-size="22" fill="rgba(255,255,255,0.95)">I just found {rec_count} perfect gifts</text>
  <text x="300" y="195" text-anchor="middle" font-family="sans-serif" font-size="22" fill="rgba(255,255,255,0.95)">for {relationship} with AI</text>
  <rect x="175" y="230" width="250" height="50" rx="12" fill="white"/>
  <text x="300" y="262" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#be123c" font-weight="700">Try it free at giftwise.fit</text>
  <text x="300" y="380" text-anchor="middle" font-family="sans-serif" font-size="12" fill="rgba(255,255,255,0.6)">AI-powered gift recommendations from social media</text>
</svg>'''

    buf = io.BytesIO(svg.encode('utf-8'))
    buf.seek(0)
    return buf


def generate_story_image(user_name="Friend", gift_names=None, relationship="someone special"):
    """
    Generate a vertical story-format card (1080x1920 aspect ratio, returned as SVG).

    Args:
        user_name: First name of the user
        gift_names: Optional list of gift name strings to feature
        relationship: Relationship description

    Returns:
        BytesIO containing SVG data
    """
    gift_lines = ""
    if gift_names:
        y = 900
        for i, name in enumerate(gift_names[:5]):
            # Truncate long names
            display = name[:35] + "..." if len(name) > 35 else name
            gift_lines += f'<text x="540" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="36" fill="white">{i+1}. {display}</text>\n'
            y += 60

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.5" y2="1">
      <stop offset="0%" stop-color="#f43f5e"/>
      <stop offset="100%" stop-color="#881337"/>
    </linearGradient>
  </defs>
  <rect width="1080" height="1920" fill="url(#bg)"/>
  <text x="540" y="300" text-anchor="middle" font-family="sans-serif" font-size="80" fill="white" font-weight="800">Giftwise</text>
  <text x="540" y="500" text-anchor="middle" font-family="sans-serif" font-size="44" fill="rgba(255,255,255,0.95)">AI found the perfect gifts</text>
  <text x="540" y="560" text-anchor="middle" font-family="sans-serif" font-size="44" fill="rgba(255,255,255,0.95)">for {relationship}</text>
  <line x1="390" y1="650" x2="690" y2="650" stroke="rgba(255,255,255,0.3)" stroke-width="2"/>
  <text x="540" y="760" text-anchor="middle" font-family="sans-serif" font-size="38" fill="rgba(255,255,255,0.8)">Top picks:</text>
  {gift_lines}
  <rect x="290" y="1500" width="500" height="80" rx="16" fill="white"/>
  <text x="540" y="1550" text-anchor="middle" font-family="sans-serif" font-size="32" fill="#be123c" font-weight="700">giftwise.fit</text>
  <text x="540" y="1700" text-anchor="middle" font-family="sans-serif" font-size="24" fill="rgba(255,255,255,0.5)">AI-powered gift recommendations</text>
</svg>'''

    buf = io.BytesIO(svg.encode('utf-8'))
    buf.seek(0)
    return buf
