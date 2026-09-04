#!/usr/bin/env python3
"""
Generate a LinkedIn carousel (multi-page PDF + cover PNG) from a JSON spec.

Design system: "v5 glass" - a frosted pane floating over a warm abstract
light field, with ambient light living inside the pane. Approved 2026-08-21.

Usage:
    python3 generate_carousel.py spec.json out_dir

Prints JSON {"pdf": "<path>", "thumbnail": "<path>", "slides": N} on success.

--------------------------------------------------------------------------
SPEC SHAPE  (all slide copy is ENGLISH - the Arabic lives in the LinkedIn
             caption, which is passed separately to post_carousel.py)

{
  "slug": "rag-explained-2026-08-21",
  "ref":  "REF. 2026-014",                  # optional, a quiet document code
  "cover": {
    "tag": "AI Engineering",                # 1-3 words, shown uppercase
    "headline": "RAG is not magic. It is a fix for a <hot>lazy model</hot>.",
    "sub": "Why retrieval exists, and what it actually costs you.",
    "icon": "brain"
  },
  "slides": [
    {"type": "point",  "tag": "The Problem", "icon": "warning",
     "headline": "...", "body": "..."},
    {"type": "point",  "tag": "Step 1", "icon": "gear",
     "headline": "...", "cmd": "npx skills add owner/repo", "body": "..."},
    {"type": "figure", "tag": "The Cost",    "icon": "chart_up",
     "figure": "61%",   "note": "..."}
  ],

An optional "cmd" on a point slide renders as a monospace command block between
the headline and the body - use it for anything the reader is meant to type.
Keep it under ~60 characters so it stays on one or two lines.
  "cta": {                                   # optional but recommended
    "tag": "Save This", "icon": "bookmark",
    "headline": "...", "body": "..."
  }
}

Wrap at most ONE phrase per headline in <hot>...</hot> to tint it amber.
Icons available: see icons.py (lightbulb, gear, chart_up, warning, check,
brain, link, book, target, arrow_right, bookmark, question, clock, shield,
layers).

LENGTH BUDGETS (exceeding these breaks the layout):
  cover.headline   <= 78 chars      cover.sub    <= 68 chars
  point.headline   <= 88 chars      point.body   <= 210 chars
  figure.figure    <= 6 chars       figure.note  <= 130 chars
  tag              <= 18 chars
--------------------------------------------------------------------------

EXPORT NOTE: Chromium's PDF printer silently drops backdrop-filter, which
would flatten the glass entirely. Verified directly. So each slide is
screenshotted as a PNG (where the blur is real) and the PDF is assembled
from those images with img2pdf. Never use page.pdf() here.
"""
import sys
import os
import json
import base64
import html as htmllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icons import icon_svg  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
import img2pdf  # noqa: E402

W, H = 1080, 1350
BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE, "fonts")
AVATAR = os.path.join(BASE, "assets", "samy-avatar.png")
THREE_JS = os.path.join(BASE, "assets", "three.min.js")

NAME = "Samy Yusif"
ROLE = "AI Products Section Head"

INK = "#ffffff"
MUTE = "rgba(255,255,255,0.62)"
FAINT = "rgba(255,255,255,0.40)"
EMBER = "#ff5c2b"
AMBER = "#ffa53d"
CRIMSON = "#c81f14"

# brand-colored engineering grid, tiled behind photo covers - see the
# ".photo cover" block in CSS below for why this exists.
_GRID_PATTERN_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>
  <defs>
    <pattern id='grid' width='40' height='40' patternUnits='userSpaceOnUse'>
      <path d='M 40 0 L 0 0 0 40' fill='none' stroke='rgba(255,165,61,0.55)' stroke-width='1.1'/>
    </pattern>
  </defs>
  <rect width='240' height='240' fill='url(#grid)'/>
  <path d='M0 0 L240 240 M240 0 L0 240' stroke='rgba(255,92,43,0.40)' stroke-width='1.1'/>
  <circle cx='0' cy='0' r='3.6' fill='none' stroke='rgba(255,165,61,0.95)' stroke-width='1.8'/>
  <circle cx='240' cy='240' r='3.6' fill='none' stroke='rgba(255,165,61,0.95)' stroke-width='1.8'/>
  <path d='M8 0 L8 8 L0 8' fill='none' stroke='rgba(255,92,43,0.75)' stroke-width='1.8'/>
  <path d='M232 240 L232 232 L240 232' fill='none' stroke='rgba(255,92,43,0.75)' stroke-width='1.8'/>
</svg>
"""
GRID_PATTERN_URI = "data:image/svg+xml;base64," + base64.b64encode(_GRID_PATTERN_SVG.encode()).decode()

FONT_FACES = f"""
@font-face {{ font-family:'Plex'; src:url('file://{FONT_DIR}/IBMPlexSans-Regular.ttf'); font-weight:400; }}
@font-face {{ font-family:'Plex'; src:url('file://{FONT_DIR}/IBMPlexSans-Medium.ttf'); font-weight:500; }}
@font-face {{ font-family:'Plex'; src:url('file://{FONT_DIR}/IBMPlexSans-SemiBold.ttf'); font-weight:600; }}
@font-face {{ font-family:'Plex'; src:url('file://{FONT_DIR}/IBMPlexSans-Bold.ttf'); font-weight:700; }}
@font-face {{ font-family:'PlexMono'; src:url('file://{FONT_DIR}/IBMPlexMono-Regular.ttf'); font-weight:400; }}
@font-face {{ font-family:'PlexMono'; src:url('file://{FONT_DIR}/IBMPlexMono-Medium.ttf'); font-weight:500; }}
@font-face {{ font-family:'Cairo'; src:url('file://{FONT_DIR}/Cairo-Var.ttf'); font-weight:200 1000; }}
"""

CSS = FONT_FACES + f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{W}px; background:#050406; }}
.slide {{
  width:{W}px; height:{H}px; position:relative; overflow:hidden;
  background:#07060a; font-family:'Plex', sans-serif; color:{INK};
  direction:ltr; text-align:left;
}}

/* ---- abstract light field: this is what the glass actually blurs ---- */
.field {{ position:absolute; border-radius:50%; }}
.field.f1 {{
  width:1250px; height:1250px;
  background: radial-gradient(circle at 50% 50%, {EMBER} 0%, {EMBER}cc 18%, {CRIMSON}77 40%, transparent 70%);
  filter: blur(50px);
}}
.field.f2 {{
  width:820px; height:820px;
  background: radial-gradient(circle at 50% 50%, {AMBER}bb 0%, {AMBER}55 30%, transparent 68%);
  filter: blur(60px);
}}
.field.f3 {{
  width:700px; height:700px;
  background: radial-gradient(circle at 50% 50%, {CRIMSON}aa 0%, transparent 65%);
  filter: blur(70px);
}}
.beam {{
  position:absolute; inset:0;
  background: repeating-linear-gradient(90deg,
    transparent 0px, transparent 22px,
    rgba(255,175,95,0.62) 22px, rgba(255,175,95,0.62) 33px,
    transparent 33px, transparent 58px,
    rgba(255,92,43,0.50) 58px, rgba(255,92,43,0.50) 66px,
    transparent 66px, transparent 104px,
    rgba(255,255,255,0.16) 104px, rgba(255,255,255,0.16) 110px,
    transparent 110px, transparent 152px
  );
  filter: blur(4px);
}}
.noise {{ position:absolute; inset:0;
  background: radial-gradient(circle at 20% 78%, rgba(255,255,255,0.055), transparent 45%); }}
.vignette {{ position:absolute; inset:0;
  background: radial-gradient(ellipse at 50% 45%, transparent 46%, rgba(0,0,0,0.42) 100%); }}

/* ---- the glass pane and its light ---- */
.pane {{ position:absolute; left:78px; right:78px; top:96px; bottom:96px;
         border-radius:42px; pointer-events:none; }}
.card {{
  background: linear-gradient(158deg,
      rgba(255,255,255,0.19) 0%, rgba(255,255,255,0.075) 45%, rgba(255,255,255,0.115) 100%);
  backdrop-filter: blur(46px) saturate(140%) brightness(1.06);
  -webkit-backdrop-filter: blur(46px) saturate(140%) brightness(1.06);
  border: 1px solid rgba(255,255,255,0.26);
  box-shadow:
     0 42px 110px rgba(0,0,0,0.55),
     0 0 100px rgba(255,140,70,0.20),
     inset 0 2px 0 rgba(255,255,255,0.42),
     inset 0 -1.5px 0 rgba(255,255,255,0.14),
     inset 2px 0 0 rgba(255,255,255,0.10),
     inset -2px 0 0 rgba(255,255,255,0.10);
}}
.ambient {{ overflow:hidden; }}
.ambient::before {{
  content:''; position:absolute; width:820px; height:600px; top:-190px; right:-150px;
  background: radial-gradient(ellipse at 50% 50%,
      rgba(255,196,140,0.40) 0%, rgba(255,150,90,0.18) 45%, transparent 72%);
  filter: blur(34px);
}}
.ambient::after {{
  content:''; position:absolute; width:560px; height:440px; bottom:-140px; left:-120px;
  background: radial-gradient(ellipse at 50% 50%, rgba(190,205,255,0.16) 0%, transparent 70%);
  filter: blur(40px);
}}
.scrim {{
  background: linear-gradient(180deg,
      rgba(8,6,11,0.22) 0%, rgba(8,6,11,0.06) 20%, rgba(8,6,11,0.10) 38%,
      rgba(8,6,11,0.34) 62%, rgba(8,6,11,0.46) 84%, rgba(8,6,11,0.40) 100%);
}}
.specular {{
  background: linear-gradient(122deg,
      rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.03) 22%,
      transparent 46%, transparent 68%, rgba(255,255,255,0.07) 100%);
}}

/* ---- content ---- */
.inner {{ position:absolute; left:78px; right:78px; top:96px; bottom:96px;
          padding:62px 60px 54px; display:flex; flex-direction:column; }}
.top {{ display:flex; justify-content:space-between; align-items:center; }}
.tag {{ display:flex; align-items:center; gap:11px; }}
.tag span {{ font-weight:600; font-size:19px; letter-spacing:1.6px; text-transform:uppercase; color:{MUTE}; }}
.ref {{ font-weight:400; font-size:17px; color:{FAINT}; letter-spacing:0.4px; }}
.hair {{ height:1px; background:rgba(255,255,255,0.16); margin-top:24px; }}

.mid {{ flex:1; display:flex; flex-direction:column; justify-content:center; }}

.h1 {{ font-weight:700; font-size:64px; line-height:1.16; letter-spacing:-1.2px;
       text-shadow: 0 2px 30px rgba(0,0,0,0.55); }}
.h2 {{ font-weight:700; font-size:52px; line-height:1.22; letter-spacing:-0.8px;
       text-shadow: 0 2px 30px rgba(0,0,0,0.55); }}
.hot {{ color:{AMBER}; }}
.sub {{ font-weight:400; font-size:26px; line-height:1.55; color:{MUTE}; margin-top:26px; max-width:660px; }}
/* ---- cover illustration: a bigger flat-line scene, not a photo -----------
   Added 2026-09-04 after Samy asked for the cover to feel less like a text
   card. Stock photography was ruled out (generic, undercuts the custom
   glass identity) - this composes the same stroke-based icon language
   (icons.py) at a larger scale into a small scene specific to the idea,
   sitting above the headline. One named illustration per spec via
   cover.illustration; unnamed covers render exactly as before. */
.cover-illus {{ margin-bottom:8px; }}
.cover-illus svg, .cover-illus canvas {{ display:block; }}
.body {{ font-weight:400; font-size:27px; line-height:1.6; color:{MUTE}; margin-top:28px; max-width:680px; }}
/* command block - for step-by-step slides. monospace so a reader can copy it
   accurately, on its own ground so it reads as "type this", not as prose. */
.cmd {{
  font-family:'PlexMono', monospace; font-weight:500; font-size:24px;
  color:#ffd8a6; background:rgba(255,255,255,0.08);
  border:1px solid rgba(255,255,255,0.18); border-radius:12px;
  padding:18px 22px; margin-top:26px; align-self:flex-start;
  max-width:100%; word-break:break-word; line-height:1.4;
}}
/* ---- manual-page mode: numbered steps + a glossary strip -----------------
   Added 2026-09-04: the spec shape documented in carousel-slide-model.md
   (steps / terms) had no renderer at all - point/cta slides silently
   dropped both fields and fell back to an empty body. This is the fix. */
.steps {{ margin-top:28px; max-width:680px; display:flex; flex-direction:column; gap:16px; }}
.step {{ display:flex; align-items:flex-start; gap:16px; }}
.step-n {{
  font-family:'PlexMono', monospace; font-weight:600; font-size:18px; color:{AMBER};
  background:rgba(255,165,61,0.14); border:1px solid rgba(255,165,61,0.38);
  border-radius:9px; width:32px; height:32px; flex:none; margin-top:2px;
  display:flex; align-items:center; justify-content:center;
}}
.step-txt {{ font-weight:400; font-size:25px; line-height:1.5; color:{MUTE}; padding-top:3px; }}
.terms {{
  margin-top:26px; padding-top:22px; border-top:1px solid rgba(255,255,255,0.16);
  display:flex; flex-direction:column; gap:12px; max-width:680px;
}}
.term {{ font-size:20px; line-height:1.55; color:{MUTE}; }}
.term b {{
  color:{AMBER}; font-weight:600; font-family:'PlexMono', monospace;
  direction:ltr; unicode-bidi:isolate;
}}
/* ---- news slide: one story per slide, led by its number ---- */
/* Per the dataviz form heuristic, a single headline value is a hero figure,
   not a one-bar chart; a before/after pair is a dumbbell in ONE hue at two
   shades. No stock photography - a photo next to "+629%" carries no data. */
.n-fig {{ font-weight:700; font-size:104px; line-height:1; letter-spacing:-3px;
          color:{AMBER}; text-shadow:0 4px 34px rgba(0,0,0,0.45); }}
.n-head {{ font-weight:700; font-size:40px; line-height:1.24; letter-spacing:-0.5px;
           margin-top:16px; text-shadow:0 2px 24px rgba(0,0,0,0.5); }}
.n-body {{ font-weight:400; font-size:24px; line-height:1.55; color:{MUTE};
           margin-top:20px; max-width:720px; }}
.n-src {{ font-family:'PlexMono', monospace; font-size:16px; color:{FAINT};
          margin-top:22px; letter-spacing:0.4px; }}

/* optional story image, paired with the hero number. Local files only -
   supply press-kit or licensed art; never scraped news photos. */
.n-row {{ display:flex; align-items:flex-start; gap:32px; }}
.n-col {{ flex:1; min-width:0; }}
.n-img {{
  width:300px; height:300px; flex:none; border-radius:20px; object-fit:cover;
  border:1px solid rgba(255,255,255,0.22);
  box-shadow:0 14px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.25);
}}

.cmp {{ margin-top:26px; display:flex; flex-direction:column; gap:12px; }}
.cmp-row {{ display:flex; align-items:center; gap:16px; }}
.cmp-lbl {{ font-size:19px; color:{FAINT}; width:130px; flex:none; text-align:right; }}
.cmp-track {{ flex:1; height:20px; display:flex; align-items:center; }}
.cmp-fill {{ height:20px; border-radius:4px; background:{AMBER}; }}
.cmp-fill.dim {{ background:rgba(255,165,61,0.34); }}
.cmp-val {{ font-family:'PlexMono', monospace; font-weight:500; font-size:20px;
            color:{INK}; width:150px; flex:none; }}

.figure {{ font-weight:700; font-size:172px; line-height:0.94; letter-spacing:-5px;
           text-shadow: 0 4px 40px rgba(0,0,0,0.5); }}
.figure-note {{ font-weight:400; font-size:25px; line-height:1.5; color:{MUTE}; margin-top:24px; max-width:600px; }}

.bot {{ display:flex; justify-content:space-between; align-items:center; }}
.sig {{ display:flex; align-items:center; gap:16px; }}
.avatar {{
  width:56px; height:56px; border-radius:50%; object-fit:cover; flex:none;
  border:1.5px solid rgba(255,255,255,0.34);
  box-shadow: 0 4px 18px rgba(0,0,0,0.45), 0 0 22px rgba(255,150,90,0.22);
}}
.sig-txt {{ display:flex; flex-direction:column; gap:3px; }}
.who {{ font-weight:600; font-size:20px; color:rgba(255,255,255,0.90); letter-spacing:0.1px; }}
.role {{ font-weight:400; font-size:16px; color:{FAINT}; letter-spacing:0.5px; }}
.pg {{ font-weight:500; font-size:18px; color:{FAINT}; }}

.bot.lead .sig {{ gap:22px; }}
.bot.lead .avatar {{ width:96px; height:96px; border-width:2px;
  box-shadow: 0 8px 28px rgba(0,0,0,0.50), 0 0 34px rgba(255,150,90,0.30); }}
.bot.lead .who {{ font-size:29px; }}
.bot.lead .role {{ font-size:21px; color:rgba(255,255,255,0.58); }}

/* ---- Arabic mode (spec: "lang": "ar") ------------------------------------
   Same design system, mirrored. Cairo is a variable font, so one file
   carries every weight the layout uses.
   Three things break if you only flip `direction`:
     - negative letter-spacing pulls Arabic glyphs into each other
     - text-transform:uppercase is meaningless and kills the tag's rhythm
     - the command block holds Latin formulas, so it stays LTR inside an
       otherwise RTL card
   Line-height also has to go up: Cairo's ascenders and descenders are
   taller than Plex's, and the Latin values clip diacritics. */
.slide.ar {{ font-family:'Cairo', sans-serif; direction:rtl; text-align:right; }}
.slide.ar .h1 {{ letter-spacing:0; line-height:1.34; font-size:60px; font-weight:700; }}
.slide.ar .h2 {{ letter-spacing:0; line-height:1.40; font-size:47px; font-weight:700; }}
.slide.ar .sub {{ line-height:1.8; font-size:25px; }}
.slide.ar .body {{ line-height:1.85; font-size:25px; max-width:100%; }}
.slide.ar .figure-note {{ line-height:1.75; }}
.slide.ar .tag span {{ text-transform:none; letter-spacing:0; font-size:21px; font-weight:600; }}
.slide.ar .ref {{ direction:ltr; }}
.slide.ar .pg {{ direction:ltr; }}
.slide.ar .who, .slide.ar .role {{ direction:ltr; text-align:right; }}
.slide.ar .figure {{ direction:ltr; }}
/* the formula block never mirrors - it is Latin and must read left to right */
.slide.ar .cmd {{ direction:ltr; text-align:left; font-size:23px; }}
.slide.ar .steps {{ max-width:100%; gap:18px; }}
.slide.ar .step-txt {{ font-size:24px; line-height:1.7; padding-top:1px; }}
.slide.ar .terms {{ max-width:100%; }}
.slide.ar .term {{ font-size:20px; line-height:1.75; }}

/* ---- photo cover (2026-09-04, replaces the 3D-shape experiment) ----------
   Samy's call after reviewing both: hand-modeled 3D icons kept reading as
   generic no matter how much the render quality improved, and a bare stock
   photo undercut the "real proof" positioning. This is the resolved
   version - a real photo of the actual thing, blurred through the same
   glass card so it reads as texture/light rather than a stranger's photo,
   with the brand's own engineering-grid pattern printed over it, the
   original ember/amber field lighting still driving the color (screen
   blend so it adds onto the photo instead of replacing it), and a
   drawing-sheet ruler + corner-bracket frame around the headline so the
   whole thing reads as an annotated document, not a mood board. */
.photo {{ position:absolute; inset:-40px; background-size:cover; background-repeat:no-repeat;
  filter:grayscale(0.5) sepia(0.25) saturate(1.3) brightness(0.6) contrast(1.08); }}
.pattern {{ position:absolute; inset:0; background-image:url('{GRID_PATTERN_URI}');
  background-size:240px 240px; background-repeat:repeat; opacity:0.95; }}
.field {{ mix-blend-mode:screen; }}
.beam {{ mix-blend-mode:screen; opacity:0.85; }}
.pane.card.photo-card {{
  backdrop-filter: blur(18px) saturate(150%) brightness(1.04) !important;
  -webkit-backdrop-filter: blur(18px) saturate(150%) brightness(1.04) !important;
}}
.text-frame {{ position:relative; padding:34px 40px; margin-top:6px; }}
.corner {{ position:absolute; width:26px; height:26px; border-color:{AMBER}; border-style:solid; border-width:0; opacity:0.95; }}
.corner.tl {{ top:0; right:0; border-top-width:2.5px; border-right-width:2.5px; }}
.corner.tr {{ top:0; left:0; border-top-width:2.5px; border-left-width:2.5px; }}
.corner.bl {{ bottom:0; right:0; border-bottom-width:2.5px; border-right-width:2.5px; }}
.corner.br {{ bottom:0; left:0; border-bottom-width:2.5px; border-left-width:2.5px; }}
.tick-line {{ display:flex; align-items:center; gap:10px; margin-bottom:22px; flex-direction:row-reverse; }}
.tick-line::before {{ content:''; width:38px; height:2px; background:{EMBER}; }}
.tick-lbl {{ font-family:'PlexMono', monospace; direction:ltr; unicode-bidi:isolate;
  font-size:15px; letter-spacing:1.5px; color:rgba(255,165,61,0.9); font-weight:500; }}
.ruler {{ position:absolute; top:96px; bottom:96px; right:32px; width:18px; }}
.ruler .tick {{ position:absolute; right:0; width:7px; height:1.4px; background:rgba(255,165,61,0.55); }}
.ruler .tick.major {{ width:16px; height:2px; background:rgba(255,146,66,0.85); }}
.ruler .tick-num {{ position:absolute; right:22px; transform:translateY(-50%);
  font-family:'PlexMono', monospace; font-size:11px; color:rgba(255,165,61,0.55);
  direction:ltr; letter-spacing:0.5px; }}
.stat-chip {{ position:absolute; left:60px; bottom:66px;
  font-family:'PlexMono', monospace; font-size:15px; font-weight:500;
  letter-spacing:1.6px; color:rgba(255,165,61,0.85); direction:ltr; }}
"""

LAYOUTS = {
    "a": [("f1", "top:-430px; right:-330px;"),
          ("f2", "bottom:-260px; left:-220px;"),
          ("f3", "top:520px; right:-260px;")],
    "b": [("f1", "bottom:-460px; left:-300px;"),
          ("f2", "top:-230px; right:-150px;"),
          ("f3", "top:420px; left:-240px;")],
    "c": [("f1", "top:-380px; left:-360px;"),
          ("f2", "bottom:-300px; right:-190px;"),
          ("f3", "bottom:340px; left:420px;")],
}
BEAM_MASKS = {
    "a": "radial-gradient(ellipse 60% 55% at 76% 22%, #000 0%, transparent 68%)",
    "b": "radial-gradient(ellipse 62% 58% at 22% 80%, #000 0%, transparent 68%)",
    "c": "radial-gradient(ellipse 58% 60% at 26% 20%, #000 0%, transparent 66%)",
}
ROTATION = ["a", "b", "c"]


def rich(text):
    """Escape user copy, then re-enable only the <hot> accent tag."""
    if not text:
        return ""
    out = htmllib.escape(str(text))
    return out.replace("&lt;hot&gt;", '<span class="hot">').replace("&lt;/hot&gt;", "</span>")


# ---- cover illustrations -----------------------------------------------
# Bigger scenes in the same stroke-based, rounded-cap/join language as
# icons.py, composed to say something specific about the idea rather than
# a single small glyph. Named so a spec references one by key
# (cover.illustration) instead of embedding raw SVG - keeps every cover
# consistent with the rest of the design system. Add new ones here as
# ideas need them; there is no requirement that every deck use one.
LINE = "rgba(255,255,255,0.82)"
LINE_DIM = "rgba(255,255,255,0.42)"

def _doc(x, lines=3):
    """One document card: rounded rect + a few text-line strokes inside."""
    rows = "".join(
        f'<path d="M{x+14} {58+i*16}h44" stroke="{LINE_DIM}" stroke-width="3"/>'
        for i in range(lines)
    )
    return (f'<rect x="{x}" y="30" width="70" height="140" rx="10" '
            f'fill="none" stroke="{LINE}" stroke-width="3.5"/>{rows}')

ILLUSTRATIONS = {
    # Three documents joined by one matched key - three-way match, cable
    # schedule cross-checks, any "N documents, one identifier" idea.
    "three_docs_match": f'''
      <svg width="300" height="200" viewBox="0 0 300 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        {_doc(15)}{_doc(115)}{_doc(215)}
        <path d="M85 100h130" stroke="{LINE_DIM}" stroke-width="3" stroke-linecap="round"/>
        <circle cx="150" cy="100" r="26" fill="#07060a" stroke="{AMBER}" stroke-width="4"/>
        <path d="m139 100 8 8 15-17" stroke="{AMBER}" stroke-width="4"
              stroke-linecap="round" stroke-linejoin="round"/>
      </svg>''',
}

def illustration_svg(name):
    return ILLUSTRATIONS.get(name, "")


# ---- optional 3D cover hero (experimental, 2026-09-04) --------------------
# Samy asked whether Three.js shapes were possible, tried a generic faceted
# gem, and pushed back: shapes must be *representational* - a real object
# tied to the idea, not an abstract polyhedron ("ابعد عن المجسمات البيزك").
# So each entry below builds a small scene out of a real-world object,
# composed from primitives in the same flat-shaded amber/ember material as
# the rest of the design system. Confirmed working via a standalone
# five-shape test render before wiring in. Opt in per cover via
# `"illustration3d": "<key>"`; a spec with neither `illustration` nor
# `illustration3d` renders exactly as before.

# Shared helpers + palette, emitted once per HTML doc (not per canvas).
THREE_HELPERS = """
const T_AMBER=0xffa53d, T_EMBER=0xff5c2b, T_DARK=0x1a1410, T_CREAM=0xffe3bd;
function t_mat(color, opts){ return new THREE.MeshStandardMaterial(Object.assign(
  {color, flatShading:true, metalness:0.25, roughness:0.4}, opts||{})); }
function t_check(p0,p1,p2,thick,color,z){
  const grp=new THREE.Group(); const m=t_mat(color,{metalness:0,roughness:0.6});
  function seg(a,b){
    const dx=b.x-a.x, dy=b.y-a.y, len=Math.hypot(dx,dy), ang=Math.atan2(dy,dx);
    const box=new THREE.Mesh(new THREE.BoxGeometry(len,thick,thick), m);
    box.position.set((a.x+b.x)/2,(a.y+b.y)/2,z); box.rotation.z=ang; return box;
  }
  grp.add(seg(p0,p1), seg(p1,p2)); return grp;
}
function t_renderCover(canvasId, camZ, buildFn){
  const c=document.getElementById(canvasId);
  const scene=new THREE.Scene();
  const camera=new THREE.PerspectiveCamera(38,1,0.1,100);
  camera.position.set(2.6,2.0,camZ); camera.lookAt(0,0,0);
  const renderer=new THREE.WebGLRenderer({canvas:c, antialias:true, alpha:true});
  renderer.setSize(c.width, c.height);
  const key=new THREE.DirectionalLight(0xffffff,2.2); key.position.set(5,6,5); scene.add(key);
  const fill=new THREE.DirectionalLight(0xff8a3d,0.6); fill.position.set(-4,-2,3); scene.add(fill);
  scene.add(new THREE.AmbientLight(0x40352c,1.1));
  scene.add(buildFn());
  renderer.render(scene, camera);
}
"""

# Per-shape group-builders. Each returns a THREE.Group via `buildFn`, using
# the shared t_mat/t_check helpers and T_* palette above.
THREE_SCENES = {
    # Three fanned documents + a stamp with a checkmark - PO/GRN/invoice
    # reconciled, or any "N documents, one verified match" idea.
    "three_docs_stamp": {"cam_z": 4.2, "build": """function(){
        const g=new THREE.Group();
        for (let i=0;i<3;i++){
          const doc=new THREE.Mesh(new THREE.BoxGeometry(1.5,1.9,0.06), t_mat(i===1?T_CREAM:T_AMBER));
          doc.position.set((i-1)*0.55, -(i-1)*0.12, i*0.12); doc.rotation.z=(i-1)*0.13;
          g.add(doc);
        }
        const stamp=new THREE.Mesh(new THREE.CylinderGeometry(0.5,0.5,0.12,24), t_mat(T_EMBER,{roughness:0.3}));
        stamp.rotation.x=Math.PI/2; stamp.position.set(0.55,0.55,0.6); g.add(stamp);
        const check=t_check(new THREE.Vector2(-0.22,0.02), new THREE.Vector2(-0.03,-0.20),
                             new THREE.Vector2(0.30,0.22), 0.075, T_DARK, 0.68);
        check.position.x+=0.55; check.position.y+=0.55; g.add(check);
        g.rotation.set(0.35,0.5,0); return g;
    }"""},
    # A camera - progress verification against site photos.
    "camera_device": {"cam_z": 4.2, "build": """function(){
        const g=new THREE.Group();
        g.add(new THREE.Mesh(new THREE.BoxGeometry(2.0,1.3,0.75), t_mat(T_AMBER)));
        const lensOuter=new THREE.Mesh(new THREE.CylinderGeometry(0.48,0.48,0.5,24), t_mat(T_DARK,{metalness:0.4,roughness:0.3}));
        lensOuter.rotation.x=Math.PI/2; lensOuter.position.set(0,0,0.6); g.add(lensOuter);
        const lensInner=new THREE.Mesh(new THREE.CylinderGeometry(0.3,0.3,0.55,20), t_mat(T_EMBER,{metalness:0.5,roughness:0.2}));
        lensInner.rotation.x=Math.PI/2; lensInner.position.set(0,0,0.65); g.add(lensInner);
        const bump=new THREE.Mesh(new THREE.BoxGeometry(0.6,0.3,0.5), t_mat(T_CREAM));
        bump.position.set(-0.4,0.8,0); g.add(bump);
        const btn=new THREE.Mesh(new THREE.CylinderGeometry(0.09,0.09,0.12,10), t_mat(T_DARK,{metalness:0,roughness:0.6}));
        btn.position.set(0.75,0.95,0.15); g.add(btn);
        g.rotation.set(0.3,0.6,0); return g;
    }"""},
    # A coiled cable, straight leads at each end - cable schedule / SLD cross-check.
    "cable_coil": {"cam_z": 5.2, "build": """function(){
        const g=new THREE.Group();
        class HelixCurve extends THREE.Curve {
          getPoint(t){ const turns=4.2,r=0.85,h=2.4, a=t*turns*Math.PI*2;
            return new THREE.Vector3(Math.cos(a)*r, t*h-h/2, Math.sin(a)*r); }
        }
        const curve=new HelixCurve();
        g.add(new THREE.Mesh(new THREE.TubeGeometry(curve,140,0.16,8,false), t_mat(T_EMBER,{metalness:0.35,roughness:0.35})));
        const leadLen=0.7;
        [0,1].forEach((t)=>{
          const pt=curve.getPoint(t), tan=curve.getTangent(t).normalize();
          const dir = t===0 ? tan.clone().negate() : tan.clone();
          const lead=new THREE.Mesh(new THREE.CylinderGeometry(0.16,0.16,leadLen,8), t_mat(T_AMBER,{metalness:0.35,roughness:0.35}));
          lead.position.copy(pt.clone().add(dir.clone().multiplyScalar(leadLen/2)));
          lead.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), dir);
          g.add(lead);
        });
        g.rotation.set(0.25,0.4,0.15); return g;
    }"""},
    # A speech/commitment bubble with a checkmark - meeting -> verified action items.
    "speech_check": {"cam_z": 4.2, "build": """function(){
        const g=new THREE.Group();
        g.add(new THREE.Mesh(new THREE.BoxGeometry(2.0,1.4,0.5), t_mat(T_AMBER)));
        const tailShape=new THREE.Shape();
        tailShape.moveTo(0,0); tailShape.lineTo(0.5,0); tailShape.lineTo(0,-0.55); tailShape.closePath();
        const tail=new THREE.Mesh(new THREE.ExtrudeGeometry(tailShape,{depth:0.5,bevelEnabled:false}), t_mat(T_AMBER));
        tail.position.set(-0.85,-0.68,-0.25); g.add(tail);
        const check=t_check(new THREE.Vector2(-0.34,0.04), new THREE.Vector2(-0.06,-0.30),
                             new THREE.Vector2(0.44,0.32), 0.10, T_DARK, 0.32);
        g.add(check);
        g.rotation.set(0.3,0.5,0); return g;
    }"""},
    # An envelope with a routing arrow - inbox triage & draft-reply.
    "envelope_route": {"cam_z": 4.2, "build": """function(){
        const g=new THREE.Group();
        g.add(new THREE.Mesh(new THREE.BoxGeometry(2.1,1.4,0.12), t_mat(T_AMBER)));
        const flapShape=new THREE.Shape();
        flapShape.moveTo(-1.05,0); flapShape.lineTo(1.05,0); flapShape.lineTo(0,-0.85); flapShape.closePath();
        const flap=new THREE.Mesh(new THREE.ExtrudeGeometry(flapShape,{depth:0.1,bevelEnabled:false}), t_mat(T_CREAM));
        flap.position.set(0,0.7,0.09); g.add(flap);
        const arrow=new THREE.Group();
        const a1=new THREE.Mesh(new THREE.BoxGeometry(0.55,0.1,0.1), t_mat(T_DARK,{metalness:0,roughness:0.6}));
        const a2=new THREE.Mesh(new THREE.ConeGeometry(0.16,0.28,12), t_mat(T_DARK,{metalness:0,roughness:0.6}));
        a2.rotation.z=-Math.PI/2; a2.position.set(0.35,0,0);
        arrow.add(a1,a2); arrow.position.set(0.1,-0.05,0.2); arrow.rotation.z=-0.15;
        g.add(arrow);
        g.rotation.set(0.3,0.5,0); return g;
    }"""},
}

def three_cover_canvas(shape_key, canvas_id, size=340):
    shape = THREE_SCENES.get(shape_key)
    if not shape:
        return ""
    return (f'<canvas id="{canvas_id}" width="{size}" height="{size}"></canvas>'
            f'<script>t_renderCover("{canvas_id}", {shape["cam_z"]}, {shape["build"]});</script>')


def background(layout):
    fields = "".join(f'<div class="field {c}" style="{p}"></div>' for c, p in LAYOUTS[layout])
    mask = BEAM_MASKS[layout]
    beam = f'<div class="beam" style="-webkit-mask-image:{mask}; mask-image:{mask};"></div>'
    return f'{fields}{beam}<div class="noise"></div><div class="vignette"></div>'


def build_ruler(height=1158, minor=40, major=200):
    """Vertical scale strip in the margin outside the glass card, like the
    ruler printed on a drawing sheet. Minor ticks every `minor` px, a
    numbered major tick every `major` px."""
    ticks = []
    y, n = 0, 0
    step = max(1, major // minor)
    while y <= height:
        is_major = (n % step == 0)
        cls = "tick major" if is_major else "tick"
        ticks.append(f'<div class="{cls}" style="top:{y}px"></div>')
        if is_major:
            ticks.append(f'<div class="tick-num" style="top:{y}px">{y:03d}</div>')
        y += minor
        n += 1
    return f'<div class="ruler">{"".join(ticks)}</div>'


def frame(inner, layout, lang="en", photo=None):
    photo_html = ""
    if photo:
        photo_path = photo if os.path.isabs(photo) else os.path.join(BASE, photo)
        photo_html = f'<div class="photo" style="background-image:url(file://{photo_path})"></div><div class="pattern"></div>'
    card_cls = "pane card photo-card" if photo else "pane card"
    ruler_html = build_ruler() if photo else ""
    return f'''
    <div class="slide{" ar" if lang == "ar" else ""}">
      {photo_html}
      {background(layout)}
      <div class="{card_cls}"></div>
      <div class="pane ambient"></div>
      <div class="pane scrim"></div>
      <div class="pane specular"></div>
      {ruler_html}
      <div class="inner">{inner}</div>
    </div>'''


def top_bar(tag, ref, icon):
    ic = icon_svg(icon or "lightbulb", size=21, color="rgba(255,255,255,0.62)", stroke_width=1.7)
    return f'''
      <div class="top"><div class="tag">{ic}<span>{rich(tag)}</span></div>
      <span class="ref">{rich(ref)}</span></div>
      <div class="hair"></div>'''


def signature(idx, total, lead=False):
    return f'''<div class="bot{' lead' if lead else ''}">
      <div class="sig">
        <img class="avatar" src="file://{AVATAR}" />
        <div class="sig-txt"><span class="who">{NAME}</span><span class="role">{ROLE}</span></div>
      </div>
      <span class="pg">{idx} / {total}</span>
    </div>'''


def compare_block(c):
    """Before -> after as a two-row dumbbell in one hue at two shades.
    Bar length is proportional to the raw values, so the visual cannot
    disagree with the numbers printed beside it."""
    try:
        a = float(c["from"]["value"])
        b = float(c["to"]["value"])
    except (KeyError, TypeError, ValueError):
        return ""
    hi = max(abs(a), abs(b)) or 1.0
    rows = [("dim", c["from"], a), ("", c["to"], b)]
    out = '<div class="cmp">'
    for cls, side, val in rows:
        pct = max(2.0, abs(val) / hi * 100.0)
        out += (f'<div class="cmp-row">'
                f'<span class="cmp-lbl">{rich(side.get("label", ""))}</span>'
                f'<div class="cmp-track"><div class="cmp-fill {cls}" style="width:{pct:.1f}%"></div></div>'
                f'<span class="cmp-val">{rich(side.get("display", side.get("value")))}</span>'
                f'</div>')
    return out + "</div>"


def render_slide(kind, d, ref, idx, total, layout, lang="en"):
    if kind == "cover":
        photo = d.get("photo")
        if photo:
            # photo-cover mode (2026-09-04): headline sits in a bracketed
            # text-frame with a tick-line lead, and a stat chip goes near
            # the signature - see the ".photo cover" CSS block.
            mid = '<div class="text-frame">'
            mid += '<div class="corner tl"></div><div class="corner tr"></div>'
            mid += '<div class="corner bl"></div><div class="corner br"></div>'
            if d.get("tick"):
                mid += f'<div class="tick-line"><span class="tick-lbl">{htmllib.escape(d["tick"])}</span></div>'
            mid += (f'<div class="h1">{rich(d.get("headline"))}</div>'
                    f'<div class="sub">{rich(d.get("sub"))}</div>')
            mid += '</div>'
        else:
            illus = illustration_svg(d.get("illustration"))
            illus3d = three_cover_canvas(d.get("illustration3d"), "three-cover") if d.get("illustration3d") else ""
            mid = (f'<div class="cover-illus">{illus}{illus3d}</div>' if (illus or illus3d) else "")
            mid += (f'<div class="h1">{rich(d.get("headline"))}</div>'
                    f'<div class="sub">{rich(d.get("sub"))}</div>')
        sig = signature(idx, total, lead=True)
    elif kind == "news":
        inner = f'<div class="n-fig">{rich(d.get("figure"))}</div>'
        inner += f'<div class="n-head">{rich(d.get("headline"))}</div>'
        if d.get("compare"):
            inner += compare_block(d["compare"])
        if d.get("body"):
            inner += f'<div class="n-body">{rich(d["body"])}</div>'
        img = d.get("image")
        if img:
            path = img if os.path.isabs(img) else os.path.join(BASE, img)
            mid = (f'<div class="n-row"><div class="n-col">{inner}</div>'
                   f'<img class="n-img" src="file://{path}" /></div>')
        else:
            mid = inner
        if d.get("source"):
            mid += f'<div class="n-src">SOURCE: {rich(d["source"])}</div>'
        sig = signature(idx, total)
    elif kind == "figure":
        mid = (f'<div class="figure">{rich(d.get("figure"))}</div>'
               f'<div class="figure-note">{rich(d.get("note"))}</div>')
        sig = signature(idx, total)
    else:  # point / cta
        mid = f'<div class="h2">{rich(d.get("headline"))}</div>'
        if d.get("cmd"):
            mid += f'<div class="cmd">{htmllib.escape(str(d["cmd"]))}</div>'
        if d.get("body"):
            mid += f'<div class="body">{rich(d.get("body"))}</div>'
        if d.get("steps"):
            rows = "".join(
                f'<div class="step"><span class="step-n">{i + 1}</span>'
                f'<span class="step-txt">{rich(s)}</span></div>'
                for i, s in enumerate(d["steps"]))
            mid += f'<div class="steps">{rows}</div>'
        if d.get("terms"):
            rows = "".join(
                f'<div class="term"><b>{rich(t.get("t", ""))}</b> — {rich(t.get("d", ""))}</div>'
                for t in d["terms"])
            mid += f'<div class="terms">{rows}</div>'
        sig = signature(idx, total)
    inner = f'{top_bar(d.get("tag", ""), ref, d.get("icon"))}<div class="mid">{mid}</div>{sig}'
    if kind == "cover" and d.get("stat"):
        inner += f'<div class="stat-chip">{htmllib.escape(d["stat"])}</div>'
    photo = d.get("photo") if kind == "cover" else None
    return frame(inner, layout, lang, photo=photo)


def build(spec):
    ref = spec.get("ref", "")
    items = [("cover", spec["cover"])]
    for s in spec.get("slides", []):
        items.append((s.get("type", "point"), s))
    if spec.get("cta"):
        items.append(("point", spec["cta"]))
    total = len(items)
    lang = spec.get("lang", "en")   # "ar" flips the whole deck to RTL Cairo
    # Bug fixed 2026-09-04: the cover is always item 0, so `i % len(ROTATION)`
    # put every single deck's cover on layout "a" - every carousel in a feed
    # had an identical background composition. A per-deck offset (from the
    # slug, so it's stable across re-renders of the same spec) still keeps
    # consecutive slides within one deck rotating a/b/c, but makes different
    # decks start on different layouts.
    offset = sum(ord(c) for c in spec.get("slug", "")) % len(ROTATION)
    return [
        render_slide(kind, d, ref, i + 1, total, ROTATION[(i + offset) % len(ROTATION)], lang)
        for i, (kind, d) in enumerate(items)
    ], total


def main():
    spec_path, out_dir = sys.argv[1], sys.argv[2]
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    slug = spec.get("slug", "carousel")

    slides, total = build(spec)
    needs_three = bool(spec.get("cover", {}).get("illustration3d"))
    three_tag = (f"<script src='file://{THREE_JS}'></script><script>{THREE_HELPERS}</script>"
                 if needs_three else "")
    html = ("<!doctype html><html><head><meta charset='utf-8'>"
            f"<style>{CSS}</style>{three_tag}</head><body>{''.join(slides)}</body></html>")
    html_path = os.path.join(out_dir, f"{slug}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    pngs = []
    with sync_playwright() as p:
        # swiftshader args enable software WebGL in headless Chromium - only
        # exercised when a spec actually requests illustration3d, but harmless
        # to pass otherwise. Confirmed working 2026-09-04 with a standalone
        # Three.js render test before wiring this in.
        browser = p.chromium.launch(args=[
            "--use-gl=swiftshader", "--enable-webgl",
            "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader",
        ])
        # 1080x1350 is exactly LinkedIn's carousel spec - rendering at 2x just
        # quadrupled the PDF size (16MB for 5 slides) with no visible gain.
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(600 if needs_three else 300)
        for i in range(total):
            path = os.path.join(out_dir, f"{slug}-{i + 1:02d}.png")
            page.locator(".slide").nth(i).screenshot(path=path)
            pngs.append(path)
        browser.close()

    pdf_path = os.path.join(out_dir, f"{slug}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(pngs))

    thumb_path = os.path.join(out_dir, f"{slug}-cover.png")
    if os.path.abspath(pngs[0]) != os.path.abspath(thumb_path):
        with open(pngs[0], "rb") as src, open(thumb_path, "wb") as dst:
            dst.write(src.read())

    print(json.dumps({"pdf": pdf_path, "thumbnail": thumb_path, "slides": total}))


if __name__ == "__main__":
    main()
