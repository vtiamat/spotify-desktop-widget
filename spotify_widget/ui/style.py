"""Design tokens and stylesheet definitions for the Spotify music card."""

# Dimensions
CARD_WIDTH = 340
CARD_HEIGHT = 260
ARTWORK_SIZE = 104
CORNER_RADIUS = 16
ART_CORNER_RADIUS = 8

# Glass Base Colors (RGBA values for QPainter glass rendering)
GLASS_BG_TOP = (32, 34, 42, 215)          # Deep translucent charcoal (~84% opacity)
GLASS_BG_BOTTOM = (16, 17, 22, 228)       # Rich dark obsidian (~89% opacity)
GLASS_SHEEN_START = (255, 255, 255, 20)   # Subtle specular reflection across top edge
GLASS_SHEEN_END = (255, 255, 255, 0)

# Glass Border Specular Gradients
GLASS_BORDER_TOP_LEFT = (255, 255, 255, 46)     # ~18% white highlight at top-left
GLASS_BORDER_MID = (255, 255, 255, 20)          # ~8% mid
GLASS_BORDER_BOTTOM_RIGHT = (255, 255, 255, 8)  # ~3% subtle bottom-right shadow

# Accents (Restrained Spotify Green)
COLOR_SPOTIFY_GREEN = "#1DB954"
COLOR_SPOTIFY_GREEN_HOVER = "#1ED760"
COLOR_SPOTIFY_GREEN_PRESSED = "#179B46"

# Typography Colors
COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#D4D4D8"
COLOR_TEXT_MUTED = "#8E8E98"
COLOR_TEXT_TIMESTAMPS = "#8E8E98"

# Controls & Elements
PROGRESS_BG_COLOR = (255, 255, 255, 28)     # Translucent glass track
COLOR_PROGRESS_FILL = COLOR_SPOTIFY_GREEN

COLOR_BUTTON_FG = "#C4C4C8"
COLOR_BUTTON_HOVER = "#FFFFFF"
COLOR_BUTTON_BG_HOVER = "rgba(255, 255, 255, 0.08)"
COLOR_BUTTON_DISABLED = "#484852"

COLOR_CLOSE_FG = "#8E8E98"
COLOR_CLOSE_HOVER_FG = "#FF5555"
COLOR_CLOSE_HOVER_BG = "rgba(255, 85, 85, 0.15)"

# Global Stylesheet
CARD_STYLESHEET = f"""
QWidget#MusicCardRoot {{
    background: transparent;
}}

QLabel#SpotifyBrand {{
    color: rgba(255, 255, 255, 0.70);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}

QPushButton#CloseButton {{
    background: transparent;
    border: none;
    color: {COLOR_CLOSE_FG};
    font-size: 13px;
    font-weight: 700;
    border-radius: 11px;
    padding: 0px;
}}

QPushButton#CloseButton:hover {{
    color: {COLOR_CLOSE_HOVER_FG};
    background-color: {COLOR_CLOSE_HOVER_BG};
}}

QLabel#TrackTitle {{
    color: {COLOR_TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 700;
}}

QLabel#TrackArtist {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
}}

QLabel#TrackAlbum {{
    color: {COLOR_TEXT_MUTED};
    font-size: 11px;
    font-style: italic;
}}

QLabel#TimeLabel {{
    color: {COLOR_TEXT_TIMESTAMPS};
    font-size: 11px;
    font-family: monospace, monospace;
}}

QPushButton#SecondaryControl {{
    background: transparent;
    border: none;
    color: transparent;
    border-radius: 19px;
    padding: 0px;
    margin: 0px;
    text-align: center;
}}

QPushButton#SecondaryControl:hover {{
    color: transparent;
    background-color: {COLOR_BUTTON_BG_HOVER};
}}

QPushButton#SecondaryControl:pressed {{
    color: transparent;
    background-color: rgba(255, 255, 255, 0.04);
}}

QPushButton#SecondaryControl:disabled {{
    color: transparent;
}}

QPushButton#PlayPauseControl {{
    background-color: {COLOR_SPOTIFY_GREEN};
    border: none;
    color: transparent;
    border-radius: 19px;
    padding: 0px;
    margin: 0px;
    text-align: center;
}}

QPushButton#PlayPauseControl:hover {{
    background-color: {COLOR_SPOTIFY_GREEN_HOVER};
}}

QPushButton#PlayPauseControl:pressed {{
    background-color: {COLOR_SPOTIFY_GREEN_PRESSED};
}}

QPushButton#PlayPauseControl:disabled {{
    background-color: rgba(29, 185, 84, 0.20);
    color: transparent;
}}
"""
