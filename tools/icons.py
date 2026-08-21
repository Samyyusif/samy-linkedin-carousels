# Flat line icon library (24x24 viewBox, stroke-based, no fill) for carousel slides.
# Style: thin stroke, rounded caps/joins, single color (currentColor) - flat line style, no gradients/shadows.

ICONS = {
    "lightbulb": '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.6.6 1 1.4 1 2.3v.2h6v-.2c0-.9.4-1.7 1-2.3A6 6 0 0 0 12 3Z"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M19.4 13.5a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V19a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.6V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9c.2.7.8 1.2 1.6 1.2H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.6 1Z"/>',
    "chart_up": '<path d="M4 19V5M4 19h16"/><path d="M7 15l4-4 3 3 5-6"/><path d="M16 8h3v3"/>',
    "warning": '<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.5 2.5L16 9.5"/>',
    "brain": '<path d="M12 4.5c-2 0-3.6 1.4-3.9 3.2C6.4 8 5 9.6 5 11.5c0 1 .4 1.9 1 2.6-.2.5-.3 1-.3 1.6 0 2 1.5 3.6 3.4 3.8.5 1 1.5 1.7 2.7 1.7h.4c1.5 0 2.7-1.2 2.7-2.7V7.2c0-1.5-1.2-2.7-2.9-2.7Z"/><path d="M12 4.5c2 0 3.6 1.4 3.9 3.2C17.6 8 19 9.6 19 11.5c0 1-.4 1.9-1 2.6.2.5.3 1 .3 1.6 0 2-1.5 3.6-3.4 3.8-.4.8-1.1 1.4-2 1.6"/>',
    "link": '<path d="M9 15 15 9"/><path d="M10 6l1-1a4 4 0 0 1 5.7 5.7l-1.2 1.2"/><path d="M14 18l-1 1a4 4 0 0 1-5.7-5.7l1.2-1.2"/>',
    "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H12v18H6.5A2.5 2.5 0 0 1 4 18.5v-13Z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H12v18h5.5a2.5 2.5 0 0 0 2.5-2.5v-13Z"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.8"/><circle cx="12" cy="12" r="1.1" fill="currentColor" stroke="none"/>',
    "arrow_right": '<path d="M4 12h16"/><path d="m13 5 7 7-7 7"/>',
    "bookmark": '<path d="M6 3.5h12a.5.5 0 0 1 .5.5v16.3a.5.5 0 0 1-.77.42L12 16.9l-5.73 3.82A.5.5 0 0 1 5.5 20.3V4a.5.5 0 0 1 .5-.5Z"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.3 9a2.7 2.7 0 1 1 4.1 2.3c-.9.6-1.4 1-1.4 2.1"/><circle cx="12" cy="17.3" r="0.9" fill="currentColor" stroke="none"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.5l3.5 2"/>',
    "shield": '<path d="M12 3l7 3v6c0 4.5-3 8-7 9-4-1-7-4.5-7-9V6l7-3Z"/><path d="m9 12 2 2 4-4.5"/>',
    "layers": '<path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="M3 12l9 5 9-5"/><path d="M3 16l9 5 9-5"/>',
}


def icon_svg(name, size=48, color="#1a1a1a", stroke_width=1.6):
    body = ICONS.get(name, ICONS["lightbulb"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'xmlns="http://www.w3.org/2000/svg">{body}</svg>'
    )
