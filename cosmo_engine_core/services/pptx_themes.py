"""
Dynamic Theming System for COSMO Direct PPTX Builder.

Each theme defines colors, fonts and style that match a specific topic domain.
The `guess_theme` function picks the best theme based on presentation title/content.
"""
from pptx.dml.color import RGBColor


class Theme:
    """Visual theme for a presentation."""

    def __init__(
        self,
        name: str,
        bg_color: str,
        heading_color: str,
        body_color: str,
        muted_color: str,
        accent_color: str,
        card_bg_color: str,
        divider_color: str,
        font_heading: str = "Georgia",
        font_body: str = "Calibri",
    ):
        self.name = name
        self.bg = self._hex(bg_color)
        self.heading = self._hex(heading_color)
        self.body = self._hex(body_color)
        self.muted = self._hex(muted_color)
        self.accent = self._hex(accent_color)
        self.card_bg = self._hex(card_bg_color)
        self.divider = self._hex(divider_color)
        self.font_heading = font_heading
        self.font_body = font_body

    @staticmethod
    def _hex(hex_str: str) -> RGBColor:
        hex_str = hex_str.lstrip("#")
        return RGBColor(int(hex_str[:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


# ──────────────────────────────────────────────────────────────
# Theme Library — each themed for a specific content domain
# ──────────────────────────────────────────────────────────────

THEMES = {
    # 1. Classic Editorial (white bg, dark-red accent) — matches Kimi reference
    "editorial": Theme(
        name="editorial",
        bg_color="FFFFFF",
        heading_color="1F2937",
        body_color="1F2937",
        muted_color="6B7280",
        accent_color="8B0000",
        card_bg_color="F9FAFB",
        divider_color="E5E7EB",
        font_heading="Georgia",
        font_body="Calibri",
    ),
    # 2. Dark Tech (dark bg, cyan accent) — space, technology, AI
    "dark_tech": Theme(
        name="dark_tech",
        bg_color="0F172A",
        heading_color="F1F5F9",
        body_color="CBD5E1",
        muted_color="64748B",
        accent_color="06B6D4",
        card_bg_color="1E293B",
        divider_color="334155",
        font_heading="Georgia",
        font_body="Calibri",
    ),
    # 3. Warm Nature (cream bg, forest-green accent) — biology, ecology, environment
    "warm_nature": Theme(
        name="warm_nature",
        bg_color="FEFDF8",
        heading_color="1B4332",
        body_color="2D3748",
        muted_color="718096",
        accent_color="2D6A4F",
        card_bg_color="F0FFF4",
        divider_color="C6F6D5",
        font_heading="Georgia",
        font_body="Calibri",
    ),
    # 4. Ocean Blue (white bg, deep-blue accent) — business, finance, corporate
    "ocean_blue": Theme(
        name="ocean_blue",
        bg_color="FFFFFF",
        heading_color="1E3A5F",
        body_color="2D3748",
        muted_color="718096",
        accent_color="1E40AF",
        card_bg_color="EFF6FF",
        divider_color="BFDBFE",
        font_heading="Georgia",
        font_body="Calibri",
    ),
    # 5. Warm Amber (light bg, amber accent) — history, culture, education
    "warm_amber": Theme(
        name="warm_amber",
        bg_color="FFFBF5",
        heading_color="44403C",
        body_color="57534E",
        muted_color="78716C",
        accent_color="B45309",
        card_bg_color="FFF7ED",
        divider_color="FED7AA",
        font_heading="Georgia",
        font_body="Calibri",
    ),
    # 6. Medical/Science (white bg, teal accent) — health, medicine, biology
    "medical": Theme(
        name="medical",
        bg_color="FFFFFF",
        heading_color="134E4A",
        body_color="1F2937",
        muted_color="6B7280",
        accent_color="0D9488",
        card_bg_color="F0FDFA",
        divider_color="99F6E4",
        font_heading="Georgia",
        font_body="Calibri",
    ),
    # 7. Creative Purple (white bg, purple accent) — art, design, marketing
    "creative": Theme(
        name="creative",
        bg_color="FFFFFF",
        heading_color="312E81",
        body_color="1F2937",
        muted_color="6B7280",
        accent_color="7C3AED",
        card_bg_color="F5F3FF",
        divider_color="DDD6FE",
        font_heading="Georgia",
        font_body="Calibri",
    ),
}

# ──────────────────────────────────────────────────────────────
# Keyword-based theme selector
# ──────────────────────────────────────────────────────────────

_THEME_KEYWORDS = {
    "dark_tech": [
        "space", "cosmos", "космос", "astronomy", "астрономия", "universe",
        "вселенная", "galaxy", "ai", "artificial intelligence", "machine learning",
        "neural", "нейро", "technology", "технолог", "quantum", "квантов",
        "programming", "программир", "cyber", "кибер", "robot", "робот",
        "computer", "компьютер", "nasa", "spacex", "nvidia", "gpu", "cpu",
        "software", "hardware", "data science", "blockchain", "crypto",
        "satellite", "спутник", "rocket", "ракет", "mars", "марс",
        "moon", "луна", "star", "звезд", "planet", "планет",
    ],
    "warm_nature": [
        "nature", "природ", "ecology", "эколог", "biology", "биолог",
        "animal", "животн", "plant", "растен", "forest", "лес",
        "ocean", "океан", "climate", "климат", "environment", "окружающ",
        "sustainable", "устойчив", "green", "зелен", "earth", "земл",
        "water", "вод", "wildlife", "дикая",
    ],
    "ocean_blue": [
        "business", "бизнес", "finance", "финанс", "market", "рынок",
        "investment", "инвестиц", "startup", "стартап", "management",
        "менеджмент", "strategy", "стратег", "corporate", "корпоратив",
        "economy", "экономик", "bank", "банк", "sales", "продаж",
        "leadership", "лидер", "consulting", "консалтинг",
    ],
    "warm_amber": [
        "history", "истори", "culture", "культур", "education", "образован",
        "ancient", "древн", "civilization", "цивилизац", "philosophy",
        "философи", "literature", "литератур", "art history", "archeolog",
        "археолог", "museum", "музей", "heritage", "наследи",
        "tradition", "традиц", "religion", "религи",
    ],
    "medical": [
        "health", "здоров", "medicine", "медицин", "doctor", "врач",
        "hospital", "больниц", "pharma", "фарма", "disease", "болезн",
        "surgery", "хирург", "clinical", "клинич", "therapy", "терапи",
        "genetics", "генетик", "dna", "днк", "virus", "вирус",
        "vaccine", "вакцин", "anatomy", "анатоми",
    ],
    "creative": [
        "design", "дизайн", "art", "искусств", "creative", "креатив",
        "marketing", "маркетинг", "brand", "бренд", "advertising", "реклам",
        "photography", "фотограф", "animation", "анимаци", "ux", "ui",
        "graphic", "графическ", "visual", "визуальн", "fashion", "мод",
    ],
}


def guess_theme(title: str, content_hint: str = "") -> Theme:
    """Pick the best theme by scanning title + content for keywords."""
    combined = f"{title} {content_hint}".lower()

    scores = {}
    for theme_key, keywords in _THEME_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[theme_key] = score

    if scores:
        best = max(scores, key=scores.get)
        return THEMES[best]

    # Default: editorial (classic white/dark-red like Kimi)
    return THEMES["editorial"]
