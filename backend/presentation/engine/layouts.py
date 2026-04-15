"""
HTML/CSS layouts for Presentation Engine.
These layouts use standard keys from SlideContent and Theme.
"""

LAYOUTS = {
    "title-bullets": """
    <div class="slide title-bullets">
        <div class="content-col">
            <h1 class="slide-title">{{ slide.title }}</h1>
            <ul class="slide-bullets">
            {% for bullet in slide.bullets %}
                <li>{{ bullet }}</li>
            {% endfor %}
            </ul>
            {% if slide.speaker_notes %}
            <div class="speaker-notes" style="display: none;">{{ slide.speaker_notes }}</div>
            {% endif %}
        </div>
        {% if assets.get('background') %}
        <div class="asset-col">
            <img src="{{ assets['background'] }}" class="slide-asset" alt="slide visual">
        </div>
        {% endif %}
    </div>
    """,

    "timeline": """
    <div class="slide timeline">
        <h1 class="slide-title center-text">{{ slide.title }}</h1>
        <div class="timeline-container">
            {% for bullet in slide.bullets %}
            <div class="timeline-item">
                <div class="timeline-marker"></div>
                <div class="timeline-content">{{ bullet }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
    """,

    "two-columns": """
    <div class="slide two-columns">
        <h1 class="slide-title full-width">{{ slide.title }}</h1>
        <div class="cols">
            <div class="col left-col">
                <ul class="slide-bullets">
                {% for bullet in slide.bullets %}
                    {% if loop.index0 % 2 == 0 %}
                    <li>{{ bullet }}</li>
                    {% endif %}
                {% endfor %}
                </ul>
            </div>
            <div class="col right-col">
                <ul class="slide-bullets">
                {% for bullet in slide.bullets %}
                    {% if loop.index0 % 2 != 0 %}
                    <li>{{ bullet }}</li>
                    {% endif %}
                {% endfor %}
                </ul>
            </div>
        </div>
    </div>
    """,

    "quote-full": """
    <div class="slide quote-full" {% if assets.get('background') %}style="background-image: url('{{ assets['background'] }}'); background-size: cover; background-position: center;"{% endif %}>
        <div class="overlay">
            <h1 class="slide-title quote">{{ slide.title }}</h1>
            {% if slide.bullets %}
            <p class="quote-author">- {{ slide.bullets[0] }}</p>
            {% endif %}
        </div>
    </div>
    """,

    "chart-grid": """
    <div class="slide chart-grid">
        <h1 class="slide-title">{{ slide.title }}</h1>
        <div class="grid-container">
            {% for bullet in slide.bullets %}
            <div class="grid-card">
                <p>{{ bullet }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
    """
}

def get_layout(layout_id: str) -> str:
    return LAYOUTS.get(layout_id, LAYOUTS["title-bullets"])
