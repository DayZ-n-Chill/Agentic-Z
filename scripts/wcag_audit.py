"""WCAG 2.1 contrast audit for the Agentic-Z wiki palette.

Computes contrast ratios for the foreground/background pairs actually used
in custom.css and index.module.css, and flags any that fail AA (4.5:1 normal,
3:1 large text / UI).
"""
from __future__ import annotations


def srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)


def contrast(fg: str, bg: str) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def blend_alpha(fg: str, bg: str, alpha: float) -> str:
    """Return the hex color of fg painted on bg at the given alpha."""
    fh, bh = fg.lstrip("#"), bg.lstrip("#")
    fr, fg_, fb = int(fh[0:2], 16), int(fh[2:4], 16), int(fh[4:6], 16)
    br, bg_g, bb = int(bh[0:2], 16), int(bh[2:4], 16), int(bh[4:6], 16)
    r = round(fr * alpha + br * (1 - alpha))
    g = round(fg_ * alpha + bg_g * (1 - alpha))
    b = round(fb * alpha + bb * (1 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"


PAIRS = [
    # (label, fg, bg, threshold)  threshold = 4.5 normal, 3.0 large/ui
    # ---- LIGHT MODE ----
    ("Light: body text on bg", "#2a2a20", "#f4f1e6", 4.5),
    ("Light: heading on bg", "#1a1a14", "#f4f1e6", 4.5),
    ("Light: primary link on bg", "#a0421f", "#f4f1e6", 4.5),
    ("Light: primary on surface", "#a0421f", "#ebe6d3", 4.5),
    ("Light: navbar OS badge text on bg", "#a0421f", "#f4f1e6", 4.5),
    ("Light: link (deep olive) on bg", "#3b3a26", "#f4f1e6", 4.5),
    ("Light: link on surface", "#3b3a26", "#ebe6d3", 4.5),
    # ---- AGENT EXAMPLE BLOCK ----
    ("Light: example label warm-gray on faint olive", "#3a3a2a", "#ecead9", 4.5),  # 6% olive over cream
    ("Light: example body on faint olive", "#2a2a20", "#ecead9", 4.5),
    ("Dark: example label cream-dim on faint olive", blend_alpha("#c9c4a8", "#1a1a14", 0.7), "#22231a", 4.5),  # 18% olive over dark bg
    ("Dark: example body cream on faint olive", "#c9c4a8", "#22231a", 4.5),
    # ---- SIDEBAR CATEGORY HEADERS (muted) ----
    ("Light: sidebar category header on sidebar bg", "#6b6655", "#ede8d6", 4.5),
    ("Dark: sidebar category header on sidebar bg", "#8a8576", "#1a1a14", 4.5),
    # ---- SIDEBAR SUB-ITEMS ----
    ("Light: sub-item olive on sidebar bg", "#2a2a20", "#ede8d6", 4.5),
    ("Dark: sub-item bone on sidebar bg", "#e8e4d4", "#1a1a14", 4.5),
    # ---- TABLE CELLS ----
    ("Light: table cell text on bg", "#2a2a20", "#f4f1e6", 4.5),
    ("Dark: table cell text on bg", "#c9c4a8", "#1a1a14", 4.5),
    ("Dark: table thead bg + body text", "#c9c4a8", "#26261d", 4.5),  # 15% olive over dark bg
    # ---- DARK MODE ----
    ("Dark: body text on bg", "#c9c4a8", "#1a1a14", 4.5),
    ("Dark: heading on bg", "#e8e4d4", "#1a1a14", 4.5),
    ("Dark: primary link on bg", "#cc6e2f", "#1a1a14", 4.5),
    ("Dark: primary on surface (was #cc6e2f)", "#e08855", "#2a2a20", 4.5),
    ("Dark: link (bone) on bg", "#e8e4d4", "#1a1a14", 4.5),
    ("Dark: link on surface", "#e8e4d4", "#2a2a20", 4.5),
    # ---- HERO (always dark) ----
    ("Hero: title accent on hero bg", "#cc6e2f", "#1a1a14", 4.5),
    ("Hero: subtitle on hero bg (opacity 0.85)", blend_alpha("#c9c4a8", "#1a1a14", 0.85), "#1a1a14", 4.5),
    ("Hero: tagline on hero bg", "#c9c4a8", "#1a1a14", 4.5),
    ("Hero: meta on hero bg (opacity 0.85)", blend_alpha("#c9c4a8", "#1a1a14", 0.85), "#1a1a14", 4.5),
    # ---- STATS BAND (#0f0f0a) ----
    ("Stats: number rust on stats bg", "#cc6e2f", "#0f0f0a", 4.5),
    ("Stats: label cream on stats bg (opacity 0.75)", blend_alpha("#c9c4a8", "#0f0f0a", 0.75), "#0f0f0a", 4.5),
    # ---- AGENT CARDS / ARCH CARDS ----
    ("Card: agent name on card bg", "#e8e4d4", "#22221a", 4.5),  # rgba(42,42,32,0.3) over #1a1a14 ~ #22221a
    ("Card: agent desc on card bg (opacity 0.8)", blend_alpha("#c9c4a8", "#22221a", 0.8), "#22221a", 4.5),
    ("Card: arch desc on dark section card bg", "#c9c4a8", "#26261d", 4.5),  # rgba(42,42,32,0.4) over #1a1a14
    ("Card: arch path rust on dark card", "#cc6e2f", "#0d0d08", 4.5),
    # ---- TERMINAL ----
    ("Terminal: comment on terminal bg", "#9a9275", "#0a0a06", 4.5),
    ("Terminal: prompt rust on terminal bg", "#cc6e2f", "#0a0a06", 4.5),
    ("Terminal: command cream on terminal bg", "#e8e4d4", "#0a0a06", 4.5),
    ("Terminal: body text on terminal bg", "#c9c4a8", "#0a0a06", 4.5),
    # ---- FOOTER (#0d0d09) ----
    ("Footer: link cream on footer bg", "#c9c4a8", "#0d0d09", 4.5),
    ("Footer: title bone on footer bg", "#e8e4d4", "#0d0d09", 4.5),
    ("Footer: copyright dim on footer bg", "#a8a288", "#0d0d09", 4.5),
    # ---- SECTION SUBTITLES ----
    ("Section subtitle on sectionDark", "#a8a288", "#1a1a14", 4.5),
    ("Section subtitle on sectionDarker", "#a8a288", "#0f0f0a", 4.5),
    # ---- BUTTONS (UI threshold = 3:1 for borders, but text needs 4.5) ----
    ("Btn primary text white on primary bg", "#ffffff", "#8b3a1f", 4.5),
    ("Btn secondary text cream on transparent (~bg)", "#c9c4a8", "#1a1a14", 4.5),
]


def main() -> None:
    width = max(len(p[0]) for p in PAIRS) + 2
    print(f"{'Pair':<{width}} {'fg':<9} {'bg':<9} {'ratio':>7}  {'AA':>4}  AAA")
    print("-" * (width + 40))
    fails = 0
    for label, fg, bg, thresh in PAIRS:
        r = contrast(fg, bg)
        aa = "PASS" if r >= thresh else "FAIL"
        aaa = "PASS" if r >= 7.0 else ("PASS*" if thresh < 4.5 and r >= 4.5 else "----")
        if aa == "FAIL":
            fails += 1
        print(f"{label:<{width}} {fg:<9} {bg:<9} {r:6.2f}:1  {aa}  {aaa}")
    print("-" * (width + 40))
    print(f"\n{fails} pair(s) FAIL WCAG AA at threshold.")


if __name__ == "__main__":
    main()
