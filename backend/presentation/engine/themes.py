from backend.presentation.schemas import Theme

THEMES = {
    "tech-blue": Theme(
        theme_id="tech-blue",
        colors={
            "bg-color": "#0a192f",
            "text-main": "#ccd6f6",
            "text-accent": "#64ffda",
            "surface-1": "#112240",
            "border": "#233554",
        },
        typography={
            "font-family": "'Inter', 'Segoe UI', sans-serif",
            "heading-weight": "700",
            "body-weight": "400",
            "title-size": "3.5rem",
            "subtitle-size": "2rem",
            "body-size": "1.25rem",
        },
        spacing={
            "padding-main": "40px",
            "gap-lg": "32px",
            "gap-md": "16px",
            "gap-sm": "8px",
            "border-radius": "12px",
        }
    ),
    "minimal-dark": Theme(
        theme_id="minimal-dark",
        colors={
            "bg-color": "#121212",
            "text-main": "#ffffff",
            "text-accent": "#a1a1aa",
            "surface-1": "#1f1f1f",
            "border": "#333333",
        },
        typography={
            "font-family": "'Helvetica Neue', Arial, sans-serif",
            "heading-weight": "600",
            "body-weight": "300",
            "title-size": "3.2rem",
            "subtitle-size": "1.8rem",
            "body-size": "1.1rem",
        },
        spacing={
            "padding-main": "50px",
            "gap-lg": "40px",
            "gap-md": "20px",
            "gap-sm": "10px",
            "border-radius": "8px",
        }
    ),
    "creative-gradient": Theme(
        theme_id="creative-gradient",
        colors={
            "bg-color": "linear-gradient(135deg, #f6d365 0%, #fda085 100%)",
            "text-main": "#2d3748",
            "text-accent": "#c53030",
            "surface-1": "rgba(255, 255, 255, 0.6)",
            "border": "rgba(0, 0, 0, 0.1)",
        },
        typography={
            "font-family": "'Poppins', sans-serif",
            "heading-weight": "800",
            "body-weight": "500",
            "title-size": "4rem",
            "subtitle-size": "2.2rem",
            "body-size": "1.3rem",
        },
        spacing={
            "padding-main": "60px",
            "gap-lg": "30px",
            "gap-md": "15px",
            "gap-sm": "8px",
            "border-radius": "24px",
        }
    )
}

def get_theme(theme_id: str) -> Theme:
    return THEMES.get(theme_id, THEMES["tech-blue"])
