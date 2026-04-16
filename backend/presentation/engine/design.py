import jinja2
from typing import Dict

from backend.presentation.schemas import SlideContent, Theme, RenderedSlide
from backend.presentation.engine.layouts import get_layout
from backend.presentation.engine.themes import get_theme

class DesignEngine:
    """
    Composes the final HTML/CSS per slide.
    Injects SlideContent into the chosen layout, styling it based on the Theme.
    """

    def __init__(self):
        # We set up a Jinja2 environment to parse layout strings
        self.jinja_env = jinja2.Environment(autoescape=True)

    def render_slide(self, content: SlideContent, theme_id: str, resolved_assets: Dict[str, str]) -> RenderedSlide:
        """
        Renders a single slide.
        resolved_assets must include elements fetched by Asset Service (e.g. {'background': 'url...'})
        """
        theme = get_theme(theme_id)
        layout_html_template = get_layout(content.layout_id)

        template = self.jinja_env.from_string(layout_html_template)
        rendered_html = template.render(
            slide=content,
            assets=resolved_assets,
            theme=theme
        )

        return RenderedSlide(
            html=rendered_html,
            css_classes=[f"theme-{theme_id}", content.layout_id],
            assets=resolved_assets
        )

    def generate_theme_css(self, theme: Theme) -> str:
        """
        Generates global CSS based on the given theme's tokens.
        """
        css = ":root {\n"
        for key, value in theme.colors.items():
            css += f"  --color-{key}: {value};\n"
        
        for key, value in theme.typography.items():
            css += f"  --type-{key}: {value};\n"
            
        for key, value in theme.spacing.items():
            css += f"  --space-{key}: {value};\n"
            
        css += "}\n"
        return css
