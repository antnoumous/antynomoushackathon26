#!/usr/bin/env python3
"""Build the Driftwatch submission deck from scratch on an explicit 16:9 grid.

Run with the throwaway tooling venv:
    <venv>/bin/python scripts/build_deck.py docs/demo/driftwatch-deck.pptx

Why hand-built instead of layout placeholders: python-pptx's default template is 4:3, so a
16:9 slide keeps 4:3 placeholder geometry (9 in wide, starting at 0.5 in) and leaves the right
third of every slide empty. This script places every element on a 13.333 x 7.5 in grid instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# ---- grid -----------------------------------------------------------------------------------
W, H = 13.333, 7.5
MARGIN_L, MARGIN_R = 1.0, 1.0
TOP = 0.78
BODY_TOP = 2.05
BODY_W = W - MARGIN_L - MARGIN_R
FOOTER_TOP = H - 0.62

# ---- palette --------------------------------------------------------------------------------
BG = RGBColor(0x14, 0x16, 0x1C)
PANEL = RGBColor(0x1E, 0x22, 0x2C)
PANEL_ALT = RGBColor(0x24, 0x2A, 0x36)
TEXT = RGBColor(0xED, 0xEF, 0xF4)
MUTED = RGBColor(0x9B, 0xA6, 0xB8)
ACCENT = RGBColor(0x4F, 0xD1, 0xC5)
WARM = RGBColor(0xF2, 0xB3, 0x6B)
RULE = RGBColor(0x2A, 0x30, 0x40)
SANS = "Arial"
MONO = "Menlo"


def add_slide(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG
    return slide


def textbox(slide, left, top, width, height, *, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    return box


def write(frame, text, *, size, color=TEXT, bold=False, font=SANS, align=PP_ALIGN.LEFT,
          line_spacing=1.18, space_after=0.0, first=True):
    paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
    paragraph.alignment = align
    paragraph.line_spacing = line_spacing
    if space_after:
        paragraph.space_after = Pt(space_after)
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = font
    run.font.color.rgb = color
    return paragraph


def bullet(paragraph, char="\u2014", indent_in=0.30):
    """Give a paragraph a hanging-indent bullet, which python-pptx has no API for."""
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent_in))))
    pPr.set("indent", str(-int(Inches(indent_in))))
    for tag in ("a:buNone", "a:buAutoNum", "a:buChar"):
        for stale in pPr.findall(f"{{http://schemas.openxmlformats.org/drawingml/2006/main}}{tag.split(':')[1]}"):
            pPr.remove(stale)
    buFont = pPr.makeelement(
        "{http://schemas.openxmlformats.org/drawingml/2006/main}buFont", {"typeface": "Arial"})
    buChar = pPr.makeelement(
        "{http://schemas.openxmlformats.org/drawingml/2006/main}buChar", {"char": char})
    pPr.append(buFont)
    pPr.append(buChar)


def rect(slide, left, top, width, height, *, fill=PANEL, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
         line=None):
    box = slide.shapes.add_shape(shape, Inches(left), Inches(top), Inches(width), Inches(height))
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    if line is None:
        box.line.fill.background()
    else:
        box.line.color.rgb = line
        box.line.width = Pt(1)
    box.shadow.inherit = False
    # A preset shape carries <p:style> with a theme effect reference; some renderers draw that
    # drop shadow even after effectLst is emptied. Drop the style element entirely.
    style = box._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if style is not None:
        box._element.remove(style)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        box.adjustments[0] = 0.06
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP
    frame.margin_left = frame.margin_right = Inches(0.18)
    frame.margin_top = frame.margin_bottom = Inches(0.10)
    return box


def chrome(slide, kicker, title, number):
    """Every content slide shares this header and footer."""
    write(textbox(slide, MARGIN_L, 0.46, BODY_W, 0.3).text_frame, kicker,
          size=10.5, color=ACCENT, bold=True)
    write(textbox(slide, MARGIN_L, 0.78, BODY_W, 1.0).text_frame, title,
          size=29, bold=True, line_spacing=1.05)
    rule = slide.shapes.add_connector(1, Inches(MARGIN_L), Inches(1.78),
                                      Inches(MARGIN_L + 1.5), Inches(1.78))
    rule.line.color.rgb = ACCENT
    rule.line.width = Pt(2.5)
    write(textbox(slide, MARGIN_L, FOOTER_TOP, 8.0, 0.28).text_frame,
          "Driftwatch  \u00b7  Open Agent Hackathon 2026  \u00b7  Wildcard [Tinkerer]",
          size=9, color=MUTED)
    write(textbox(slide, W - MARGIN_R - 0.6, FOOTER_TOP, 0.6, 0.28).text_frame,
          str(number), size=9, color=MUTED, align=PP_ALIGN.RIGHT)


def bullets(slide, items, *, top=BODY_TOP, width=BODY_W, size=17, gap=13):
    # Centred in the band between the header rule and the footer, so short decks of bullets do not
    # leave a dead third at the bottom of the slide.
    frame = textbox(slide, MARGIN_L, top, width, (H - 0.95) - top,
                    anchor=MSO_ANCHOR.MIDDLE).text_frame
    for index, item in enumerate(items):
        paragraph = write(frame, item, size=size, color=TEXT, first=(index == 0),
                          space_after=gap, line_spacing=1.22)
        bullet(paragraph)
    return frame


def stat(slide, left, top, width, height, value, label, *, color=ACCENT):
    panel = rect(slide, left, top, width, height, fill=PANEL)
    frame = panel.text_frame
    frame.vertical_anchor = MSO_ANCHOR.TOP
    write(frame, value, size=34, bold=True, color=color, line_spacing=1.0)
    write(frame, label, size=11.5, color=MUTED, first=False, space_after=0, line_spacing=1.2)


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def build() -> Presentation:
    root = Path(__file__).resolve().parents[1]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)

    # 1 — title -------------------------------------------------------------------------------
    s = add_slide(prs)
    write(textbox(s, MARGIN_L, 1.55, 9.6, 0.35).text_frame,
          "OPEN AGENT HACKATHON 2026  \u00b7  WILDCARD [TINKERER]", size=11, color=ACCENT, bold=True)
    write(textbox(s, MARGIN_L, 2.02, 11.0, 1.2).text_frame, "Driftwatch",
          size=64, bold=True, line_spacing=0.95)
    write(textbox(s, MARGIN_L, 3.32, 9.8, 0.9).text_frame,
          "An OCI tenancy auditor that argues with itself",
          size=25, color=TEXT, line_spacing=1.15)
    write(textbox(s, MARGIN_L, 4.28, 9.8, 0.6).text_frame,
          "Evidence lineage  \u00b7  adversarial critique  \u00b7  a live sponsor data plane",
          size=14, color=MUTED)
    line = s.shapes.add_connector(1, Inches(MARGIN_L), Inches(5.35), Inches(W - MARGIN_R), Inches(5.35))
    line.line.color.rgb = RULE
    line.line.width = Pt(1)
    write(textbox(s, MARGIN_L, 5.58, 6.4, 1.2).text_frame,
          "Four agents, one bounded loop. Every finding carries the evidence\nthat produced it \u2014 and can be retracted when the evidence disagrees.",
          size=13, color=MUTED, line_spacing=1.35)
    meta = textbox(s, W - MARGIN_R - 3.1, 5.58, 3.1, 1.2)
    write(meta.text_frame, "solo build", size=13, color=MUTED, align=PP_ALIGN.RIGHT, line_spacing=1.35)
    write(meta.text_frame, "Zetaris + Meterless", size=13, color=MUTED, align=PP_ALIGN.RIGHT,
          first=False, line_spacing=1.35)
    notes(s, "Driftwatch audits an OCI tenancy for cost waste and shadow infrastructure. "
             "Four agents, one bounded loop, and every artefact comes out of the run itself.")

    # 2 — problem -----------------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "THE PROBLEM", "Confident verdicts, no receipts", 2)
    bullets(s, [
        "Cloud tenancies accumulate waste and unattributed \u201cshadow\u201d resources that nobody "
        "declared and nobody owns.",
        "LLM audit demos produce confident findings with no way to check how they were derived \u2014 "
        "and no way to disagree with them.",
        "Trust needs three things: evidence for every claim, a critic that can reject a finding, "
        "and a reproducible record of the reasoning.",
        "And the auditor should consume governed data where governance already lives \u2014 not a "
        "scraped summary of it.",
    ])
    notes(s, "The pitch is not 'an LLM reads your cloud bill'. It is auditability: every claim "
             "traceable to a source, and a critique step that can throw a finding away.")

    # 3 — architecture ------------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "HOW IT WORKS", "Four named agents, one bounded loop", 3)
    stages = [("Planner", "asks the\nquestion"), ("Scout", "gathers\nevidence"),
              ("Skeptic", "attacks\nthe claim"), ("Writer", "synthesises\nwhat survives")]
    box_w, gap = 2.62, 0.36
    for index, (name, role) in enumerate(stages):
        left = MARGIN_L + index * (box_w + gap)
        shape = rect(s, left, BODY_TOP, box_w, 1.28, fill=PANEL)
        frame = shape.text_frame
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        write(frame, name, size=16, bold=True, color=ACCENT if index in (1, 2) else TEXT,
              line_spacing=1.0, align=PP_ALIGN.CENTER)
        write(frame, role, size=11, color=MUTED, first=False, align=PP_ALIGN.CENTER, line_spacing=1.15)
    bullets(s, [
        "Handoffs, critique and retries are written to JSONL: which agent acted, on what input, "
        "with what status.",
        "The Skeptic can reject a finding and force re-investigation \u2014 rejection is as visible "
        "as acceptance.",
        "A figures guard refuses any number in the report that no evidence item supports.",
        "Hand-rolled, no orchestration framework: rounds, per-source deadlines and a total budget "
        "are all capped.",
    ], top=3.72, size=15.5, gap=9)
    notes(s, "The loop is deliberately boring: four names, explicit handoffs, hard caps. "
             "Everything it does is in the trace.")

    # 4 — Zetaris -----------------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "SPONSOR \u00b7 ZETARIS", "The data plane, live and least-privileged", 4)
    bullets(s, [
        "Policy snapshots are published as immutable tables on the live Zetaris AI Data Gateway "
        "(synthetic data, real engine).",
        "The agent fetches them through two pinned SELECTs, then re-verifies row count, content "
        "digest and scope hash after transport \u2014 before any agent sees a rule.",
        "The runtime identity is SELECT-only; the refusal of CREATE and GRANT is recorded evidence, "
        "not a promise.",
        "A failed digest degrades explicitly to the file source. It never silently serves a rule it "
        "could not verify.",
    ], width=7.9)
    stat(s, 9.35, 2.15, 2.98, 1.8, "1 \u2192 0", "Republish without rule R-1: exactly one finding "
         "disappears, everything else is unchanged")
    stat(s, 9.35, 4.2, 2.98, 1.8, "2 SELECTs", "Pinned queries, digest and scope re-validated "
         "after the wire", color=WARM)
    notes(s, "Zetaris is the governed-data seam. The causal proof: removing one rule removes exactly "
             "the one finding that rule produced.")

    # 5 — Meterless engine --------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "SPONSOR \u00b7 METERLESS ENGINE", "The World Model is load-bearing", 5)
    bullets(s, [
        "An engine in app/world_model/: an immutable observation store, validated ingestion, and a "
        "context builder whose selections pin one exact run and source revision.",
        "Scout and Skeptic both read their context through it. Every finding carries the provenance "
        "of the observation behind it.",
        "Observations cannot be rewritten in place; a later snapshot cannot retro-fit an earlier "
        "candidate.",
        "Acceptance is generated, not written: scripts/verify_world_model.py regenerates the proof "
        "offline, with no credentials and no network.",
    ], width=7.9)
    stat(s, 9.35, 2.15, 2.98, 1.8, "2 agents", "Scout and Skeptic both read their context "
         "through it \u2014 not renamed state, not an unused store")
    stat(s, 9.35, 4.2, 2.98, 1.8, "offline", "Proof regenerated locally; no sponsor runtime "
         "required to check it", color=WARM)
    notes(s, "This is the part a judge can verify without any sponsor credentials: run the script, "
             "read the acceptance JSON.")

    # 6 — Meterless status --------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "SPONSOR \u00b7 METERLESS PROVIDER", "Nightshift: wired, not yet live", 6)
    bullets(s, [
        "The provider implements the documented contract: bearer auth, meterless-app header, "
        "/v1/models discovery before selection, three JSON schemas, a 60-second budget.",
        "Redirects are refused, automatic POST retries are disabled, and a slow body cannot outrun "
        "the remaining audit deadline.",
        "Accounting is truthful: real attempts, real fallbacks, and zero attempts reported as "
        "not_used rather than dressed up as a success.",
        "No request has been served. The vendor\u2019s Mac builds are ad-hoc signed and Gatekeeper "
        "rejects them; we did not bypass macOS security.",
    ], width=7.9)
    chip = rect(s, 9.35, 2.15, 2.98, 1.05, fill=PANEL)
    write(chip.text_frame, "nightshift", size=11, color=MUTED, line_spacing=1.0)
    write(chip.text_frame, "not_used", size=20, bold=True, color=WARM, first=False, line_spacing=1.1)
    note = rect(s, 9.35, 3.35, 2.98, 1.62, fill=PANEL)
    for index, line in enumerate(("attempts   0", "successes  0", "fallbacks  0")):
        paragraph = write(note.text_frame, line, size=12, color=MUTED, font=MONO,
                          line_spacing=1.35, first=(index == 0))
        paragraph.space_after = Pt(3)
    notes(s, "This slide is deliberately unflattering. A configured provider with zero attempts is "
             "not an integration success, and the report says so.")

    # 7 — causal experiment -------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "EVIDENCE", "The causal experiment \u2014 not a demo branch", 7)
    write(textbox(s, MARGIN_L, 2.0, BODY_W, 0.4).text_frame,
          "Same scenario, same code, one rule unpublished.", size=15, color=MUTED)
    rows = [["live run", "policy snapshot", "rules", "finding from R-1"],
            ["base", "example1_base_v2", "5", "accepted \u00b7 cost_waste"],
            ["variant", "example1_no_volume_v2", "4", "gone \u2014 and nothing else moved"]]
    table_shape = s.shapes.add_table(len(rows), 4, Inches(MARGIN_L), Inches(2.62),
                                     Inches(BODY_W), Inches(1.55))
    table = table_shape.table
    tbl = table._tbl
    style_id = tbl.tblPr.find(
        "{http://schemas.openxmlformats.org/drawingml/2006/main}tableStyleId")
    if style_id is not None:
        tbl.tblPr.remove(style_id)
    edge = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for width, column in zip((2.0, 3.1, 1.3, 4.93), range(4)):
        table.columns[column].width = Inches(width)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = PANEL_ALT if r == 0 else PANEL
            cell.margin_left = cell.margin_right = Inches(0.14)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            frame = cell.text_frame
            frame.word_wrap = True
            paragraph = frame.paragraphs[0]
            run = paragraph.add_run()
            run.text = value
            run.font.size = Pt(12.5 if r else 11)
            run.font.bold = r == 0 or c == 0
            run.font.name = SANS
            run.font.color.rgb = MUTED if r == 0 else (ACCENT if c == 3 and r == 2 else TEXT)
            tcPr = cell._tc.get_or_add_tcPr()
            for side in ("lnL", "lnR", "lnT", "lnB"):
                line = tcPr.makeelement(edge + side, {"w": "9525", "cap": "flat", "cmpd": "sng",
                                                      "algn": "ctr"})
                fill = line.makeelement(edge + "solidFill", {})
                colour = fill.makeelement(edge + "srgbClr", {"val": "2A3040"})
                fill.append(colour)
                line.append(fill)
                tcPr.append(line)
    guards = [("dead endpoint", "degrades honestly \u2014 sponsor_acceptance: FALSE"),
              ("tampered digest pin", "rejected before use \u2014 zero fabricated output")]
    for index, (name, effect) in enumerate(guards):
        top = 4.62 + index * 0.78
        panel = rect(s, MARGIN_L, top, BODY_W, 0.62, fill=PANEL)
        frame = panel.text_frame
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        frame.margin_left = Inches(0.3)
        paragraph = frame.paragraphs[0]
        paragraph.alignment = PP_ALIGN.LEFT
        run = paragraph.add_run()
        run.text = name
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.name = SANS
        run.font.color.rgb = WARM
        run2 = paragraph.add_run()
        run2.text = "     " + effect
        run2.font.size = Pt(12)
        run2.font.name = SANS
        run2.font.color.rgb = MUTED
    notes(s, "Two runs, one rule removed. The delta is one finding, and the guards are shown failing "
             "closed rather than silently succeeding.")

    # 8 — the acceptance run, as it printed ----------------------------------------------------
    s = add_slide(prs)
    chrome(s, "EVIDENCE \u00b7 ZETARIS ACCEPTANCE", "The acceptance run, as it printed", 8)
    bullets(s, [
        "One command re-publishes the policy without rule R-1 and diffs the resulting findings "
        "against the base snapshot.",
        "only_in_base carries exactly one entry \u2014 the detached-volume finding R-1 produced; "
        "only_in_variant is empty.",
        "The tool reports its own verdict: effect_observed true, sponsor_acceptance true.",
        "This is the program's output, not a rendering of it."
    ], width=4.55, size=14.5, gap=12)
    picture = root / "docs/demo/hero-frame.png"
    assert picture.is_file(), picture
    shot = s.shapes.add_picture(str(picture), Inches(5.85), Inches(2.05), width=Inches(6.45))
    # The capture carries a 3 px light fringe from its rounded window corners; crop it so the
    # panel edge reads as a clean rectangle on the slide.
    shot.crop_left = shot.crop_right = 3 / 786
    shot.crop_top = shot.crop_bottom = 3 / 560
    notes(s, "The screenshot is the actual terminal output of the Zetaris acceptance run that the "
             "evidence directory records. It is here so a judge can read the diff without leaving "
             "the deck.")

    # 8 — supplier bug ------------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "WHAT WENT WRONG", "Our guard caught a supplier bug in production", 9)
    bullets(s, [
        "The live engine\u2019s CSV parser silently truncated cells at embedded quotes \u2014 row counts "
        "and headers still looked perfect.",
        "Our content-digest check rejected every affected fetch, so the run degraded to fixture data "
        "honestly instead of feeding corrupted rules to an agent.",
        "Response: a quote-safe re-export with unchanged digests, new immutable snapshots, and v1 "
        "revoked and dropped.",
        "\u201cA connector\u2019s happy path is not its contract \u2014 validate the payload after the wire, "
        "not just the status code.\u201d",
    ])
    notes(s, "This is the credibility slide: the guard that was built to catch our own bad data "
             "caught the vendor's.")

    # 9 — measured ----------------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "MEASUREMENT", "Measured, not promised", 10)
    card_w, card_gap = 3.55, 0.34
    for index, (value, label, colour) in enumerate([
            ("3 / 3", "Curated scenarios \u2014 precision, recall and verdict accuracy all 1.0, "
                      "deterministic", ACCENT),
            ("10", "Held-out generated tenancies, same scores; the generator exposed two defects the "
                   "curated set missed", ACCENT),
            ("465", "Tests, including sample-mode isolation enforced by blocking sockets and "
                    "subprocess creation", WARM)]):
        stat(s, MARGIN_L + index * (card_w + card_gap), 2.1, card_w, 2.05, value, label, color=colour)
    bullets(s, [
        "Undefined metrics stay n/a rather than being scored as perfect; a clean tenancy must produce "
        "no findings at all.",
        "Every external call has a timeout, every loop has a cap, and a run finishes in minutes.",
        "Packaging verified from a fresh public clone, and the offline path re-run with network and "
        "DNS denied.",
    ], top=4.45, size=14.5, gap=8)
    notes(s, "Numbers on a slide are cheap. These are the ones the repo can reproduce, including the "
             "two defects the held-out generator found.")

    # 10 — attribution ------------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "DISCLOSURE", "How it was built \u2014 attributed honestly", 11)
    bullets(s, [
        "Cursor drove the first two tasks before its free-tier quota ran out; the blocker was posted "
        "and the sessions are retained.",
        "Hermes drove the remaining tasks with tests first; per-task attribution lives in the "
        "committed build log.",
        "Every mutating step on the live Zetaris instance went through a dry-run approval package "
        "first \u2014 recorded in decisions.md.",
        "Pre-existing components are declared in the submission form; the build window work is "
        "scored separately.",
    ])
    notes(s, "Attribution is a rule, not a courtesy. This slide lists what each tool actually did.")

    # 11 — run it -----------------------------------------------------------------------------
    s = add_slide(prs)
    chrome(s, "REPRODUCE", "Run it yourself \u2014 no keys required", 12)
    code = [("git clone https://github.com/antnoumous/antynomoushackathon26", ACCENT),
            ("cd antynomoushackathon26", ACCENT),
            ("python3.11 -m venv .venv && . .venv/bin/activate", ACCENT),
            ("pip install -r requirements.txt", ACCENT),
            ("", ACCENT),
            ("python run.py             # full agent, cached data, no credentials", TEXT),
            ("python -m evals.run_eval  # precision / recall / determinism", TEXT)]
    panel = rect(s, MARGIN_L, 2.05, BODY_W, 2.72, fill=PANEL)
    frame = panel.text_frame
    frame.margin_left = Inches(0.3)
    frame.margin_top = Inches(0.26)
    for index, (line, colour) in enumerate(code):
        paragraph = write(frame, line or " ", size=13, color=colour, font=MONO,
                          line_spacing=1.45, first=(index == 0))
        paragraph.space_after = Pt(0)
    write(textbox(s, MARGIN_L, 5.0, BODY_W, 0.9).text_frame,
          "Sample mode needs no credentials, no network and no model. "
          "Sponsor settings are read only after sample mode is selected.",
          size=14, color=MUTED, line_spacing=1.3)
    write(textbox(s, MARGIN_L, 6.0, BODY_W, 0.6).text_frame,
          "Every claim traces to evidence \u2014 every failure degrades honestly.",
          size=17, bold=True, color=TEXT)
    notes(s, "A judge can clone and run this in two commands. Nothing installs at run time.")

    return prs


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/demo/driftwatch-deck.pptx")
    prs = build()
    assert len(prs.slides) == 12, len(prs.slides)
    for index, slide in enumerate(prs.slides, start=1):
        boxes = [shape for shape in slide.shapes if shape.has_text_frame]
        assert boxes, f"slide {index} has no text"
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    print(f"wrote {out} with {len(prs.slides)} slides")


if __name__ == "__main__":
    main()
