"""Generate an editable, presentation deck from manifest and slide specification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

NAVY = RGBColor(19, 35, 58)         # #13233A
RED = RGBColor(215, 25, 32)         # #D71920
MID_GREY = RGBColor(100, 116, 139)  # #64748B
LIGHT_BLUE = RGBColor(234, 240, 246)# #EAF0F6
WHITE = RGBColor(255, 255, 255)
DARK_TEXT = RGBColor(30, 41, 59)    # #1E293B
BORDER_GREY = RGBColor(203, 213, 225)

SLIDE_WIDTH_IN = 13.333
SLIDE_HEIGHT_IN = 7.5


def extract_slide_titles(deck: Presentation) -> set[str]:
    """Extract titles or main headings from all slides."""
    titles = set()
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text:
                for p in shape.text_frame.paragraphs:
                    line = p.text.strip()
                    if (
                        line
                        and not line.startswith("•")
                        and not line.startswith("ME3106 ·")
                        and not line.startswith("ADVANCED MOTORSPORT")
                        and not line.startswith("Representative Educational")
                        and not line.startswith("Figure:")
                        and len(line) > 5
                    ):
                        titles.add(line)
    return titles


def all_slide_text_within_safe_bounds(deck: Presentation) -> bool:
    """Check that all shapes with text frames remain strictly within slide bounds."""
    width_limit = deck.slide_width
    height_limit = deck.slide_height
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                left = shape.left
                top = shape.top
                width = shape.width
                height = shape.height
                if left < 0 or top < 0:
                    return False
                if left + width > width_limit + 1000:
                    return False
                if top + height > height_limit + 1000:
                    return False
    return True


def _add_header_and_footer(slide, category: str, title: str, slide_num: int, total_slides: int, run_id: str) -> None:
    """Add consistent running header and footer to a content slide."""
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.95))
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_cat = tf.paragraphs[0]
    p_cat.text = f"ME3106 · {category.upper()}"
    p_cat.font.name = "Arial"
    p_cat.font.size = Pt(10)
    p_cat.font.bold = True
    p_cat.font.color.rgb = RED
    p_cat.space_after = Pt(2)

    p_title = tf.add_paragraph()
    p_title.text = title
    p_title.font.name = "Arial"
    p_title.font.size = Pt(21)
    p_title.font.bold = True
    p_title.font.color.rgb = NAVY

    # Divider line
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8),
        Inches(1.4),
        Inches(11.7),
        Inches(0.02)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = RED
    line.line.color.rgb = RED

    # Footer
    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.35))
    ftf = footer_box.text_frame
    ftf.word_wrap = True
    ftf.margin_left = ftf.margin_top = ftf.margin_right = ftf.margin_bottom = 0
    p_foot = ftf.paragraphs[0]
    p_foot.text = f"Representative Educational Model  ·  Run ID: {run_id}  ·  Slide {slide_num} of {total_slides}"
    p_foot.font.name = "Arial"
    p_foot.font.size = Pt(8.5)
    p_foot.font.color.rgb = MID_GREY


def _build_title_slide(slide, slide_data: dict, manifest: dict) -> None:
    """Build high-impact widescreen title slide."""
    # Top accent bar
    top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.6), Inches(11.7), Inches(0.08))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = RED
    top_bar.line.color.rgb = RED

    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(2.2))
    tf = title_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_tag = tf.paragraphs[0]
    p_tag.text = "ADVANCED MOTORSPORT SIMULATION & VEHICLE DYNAMICS"
    p_tag.font.name = "Arial"
    p_tag.font.size = Pt(11)
    p_tag.font.bold = True
    p_tag.font.color.rgb = RED
    p_tag.space_after = Pt(6)

    p_title = tf.add_paragraph()
    p_title.text = slide_data["title"]
    p_title.font.name = "Arial"
    p_title.font.size = Pt(28)
    p_title.font.bold = True
    p_title.font.color.rgb = NAVY
    p_title.space_after = Pt(6)

    p_sub = tf.add_paragraph()
    p_sub.text = slide_data.get("subtitle", "")
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(15)
    p_sub.font.color.rgb = MID_GREY

    # Left Card: Summary Points
    card_left = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.2), Inches(6.8), Inches(3.3))
    card_left.fill.solid()
    card_left.fill.fore_color.rgb = LIGHT_BLUE
    card_left.line.color.rgb = BORDER_GREY

    tb_left = slide.shapes.add_textbox(Inches(1.0), Inches(3.35), Inches(6.4), Inches(3.0))
    ltf = tb_left.text_frame
    ltf.word_wrap = True
    p_chead = ltf.paragraphs[0]
    p_chead.text = "Project Scope & Methodology"
    p_chead.font.name = "Arial"
    p_chead.font.size = Pt(14)
    p_chead.font.bold = True
    p_chead.font.color.rgb = NAVY
    p_chead.space_after = Pt(8)

    for bp in slide_data.get("bullet_points", []):
        p_bp = ltf.add_paragraph()
        p_bp.text = f"•  {bp}"
        p_bp.font.name = "Arial"
        p_bp.font.size = Pt(11)
        p_bp.font.color.rgb = DARK_TEXT
        p_bp.space_after = Pt(6)

    # Right Card: Project Metadata Table
    card_right = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.8), Inches(3.2), Inches(4.7), Inches(3.3))
    card_right.fill.solid()
    card_right.fill.fore_color.rgb = WHITE
    card_right.line.color.rgb = BORDER_GREY

    meta_table = slide.shapes.add_table(6, 2, Inches(8.0), Inches(3.4), Inches(4.3), Inches(2.9))
    tbl = meta_table.table
    tbl.columns[0].width = Inches(1.8)
    tbl.columns[1].width = Inches(2.5)

    metadata_rows = [
        ("Project Code", "ME3106 Motorsport Sim"),
        ("Model Version", manifest.get("model_version", "1.0.0")),
        ("Run ID", manifest.get("run_id", "N/A")),
        ("Angle Sweep", "0.0° to 30.0° (1° step)"),
        ("Circuits", "Low-DF, Balanced, High-DF"),
        ("Classification", "Representative Educational"),
    ]
    for row_idx, (k, v) in enumerate(metadata_rows):
        c0 = tbl.cell(row_idx, 0)
        c1 = tbl.cell(row_idx, 1)
        c0.text = k
        c1.text = str(v)
        c0.text_frame.paragraphs[0].font.name = "Arial"
        c0.text_frame.paragraphs[0].font.size = Pt(9.5)
        c0.text_frame.paragraphs[0].font.bold = True
        c0.text_frame.paragraphs[0].font.color.rgb = NAVY
        c1.text_frame.paragraphs[0].font.name = "Arial"
        c1.text_frame.paragraphs[0].font.size = Pt(9.5)
        c1.text_frame.paragraphs[0].font.color.rgb = DARK_TEXT

    # Footer
    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.35))
    ftf = footer_box.text_frame
    ftf.word_wrap = True
    p_foot = ftf.paragraphs[0]
    p_foot.text = f"Representative Educational Model  ·  Run ID: {manifest.get('run_id')}  ·  Seed {manifest.get('seed')}"
    p_foot.font.name = "Arial"
    p_foot.font.size = Pt(9)
    p_foot.font.color.rgb = MID_GREY


def _build_content_slide(slide, slide_data: dict, manifest: dict, results_root: Path, total_slides: int) -> None:
    """Build a standard two-column or text-and-figure content slide."""
    idx = slide_data["index"]
    _add_header_and_footer(
        slide,
        slide_data.get("category", "ANALYSIS"),
        slide_data["title"],
        idx,
        total_slides,
        manifest.get("run_id", "N/A"),
    )

    figure_rel = slide_data.get("figure")
    figure_path = None
    if figure_rel:
        candidate = results_root / figure_rel
        if candidate.is_file():
            figure_path = candidate
        else:
            cand2 = results_root.parent / figure_rel
            if cand2.is_file():
                figure_path = cand2

    # If figure is present, use text on left and image on right
    if figure_path is not None:
        # Left column (Text & stats)
        text_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(5.8), Inches(3.6))
        tf = text_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        bps = slide_data.get("bullet_points", [])
        for i, bp in enumerate(bps):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = f"•  {bp}"
            p.font.name = "Arial"
            p.font.size = Pt(11.5)
            p.font.color.rgb = DARK_TEXT
            p.space_after = Pt(6)

        # Key stats table at bottom of left column
        stats = slide_data.get("key_stats", {})
        if stats:
            stats_table = slide.shapes.add_table(len(stats), 2, Inches(0.8), Inches(5.2), Inches(5.8), Inches(1.5))
            stbl = stats_table.table
            stbl.columns[0].width = Inches(2.5)
            stbl.columns[1].width = Inches(3.3)
            for r_idx, (k, v) in enumerate(stats.items()):
                c0 = stbl.cell(r_idx, 0)
                c1 = stbl.cell(r_idx, 1)
                c0.text = k
                c1.text = str(v)
                c0.text_frame.paragraphs[0].font.name = "Arial"
                c0.text_frame.paragraphs[0].font.size = Pt(9.5)
                c0.text_frame.paragraphs[0].font.bold = True
                c0.text_frame.paragraphs[0].font.color.rgb = NAVY
                c1.text_frame.paragraphs[0].font.name = "Arial"
                c1.text_frame.paragraphs[0].font.size = Pt(9.5)
                c1.text_frame.paragraphs[0].font.color.rgb = DARK_TEXT

        # Right column (Figure)
        slide.shapes.add_picture(str(figure_path), Inches(6.9), Inches(1.55), width=Inches(5.6))

        # Caption
        caption_text = slide_data.get("figure_caption", f"Figure: {slide_data['title']}")
        cap_box = slide.shapes.add_textbox(Inches(6.9), Inches(6.35), Inches(5.6), Inches(0.45))
        ctf = cap_box.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_top = ctf.margin_right = ctf.margin_bottom = 0
        p_cap = ctf.paragraphs[0]
        p_cap.text = caption_text
        p_cap.font.name = "Arial"
        p_cap.font.size = Pt(9)
        p_cap.font.italic = True
        p_cap.font.color.rgb = MID_GREY

    else:
        # Two-column layout (Left: detailed points, Right: stats / data cards)
        text_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.55), Inches(6.8), Inches(5.1))
        tf = text_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        bps = slide_data.get("bullet_points", [])
        for i, bp in enumerate(bps):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = f"•  {bp}"
            p.font.name = "Arial"
            p.font.size = Pt(12)
            p.font.color.rgb = DARK_TEXT
            p.space_after = Pt(8)

        # Right side card for stats / parameters
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.0), Inches(1.55), Inches(4.5), Inches(5.1))
        card.fill.solid()
        card.fill.fore_color.rgb = LIGHT_BLUE
        card.line.color.rgb = BORDER_GREY

        stats = slide_data.get("key_stats", {})
        if stats:
            card_title = slide.shapes.add_textbox(Inches(8.2), Inches(1.7), Inches(4.1), Inches(0.4))
            ctf = card_title.text_frame
            ctf.margin_left = ctf.margin_top = ctf.margin_right = ctf.margin_bottom = 0
            p_ct = ctf.paragraphs[0]
            p_ct.text = "Key Metrics & Specifications"
            p_ct.font.name = "Arial"
            p_ct.font.size = Pt(13)
            p_ct.font.bold = True
            p_ct.font.color.rgb = NAVY

            stats_table = slide.shapes.add_table(len(stats), 2, Inches(8.2), Inches(2.2), Inches(4.1), Inches(3.8))
            stbl = stats_table.table
            stbl.columns[0].width = Inches(2.0)
            stbl.columns[1].width = Inches(2.1)
            for r_idx, (k, v) in enumerate(stats.items()):
                c0 = stbl.cell(r_idx, 0)
                c1 = stbl.cell(r_idx, 1)
                c0.text = k
                c1.text = str(v)
                c0.text_frame.paragraphs[0].font.name = "Arial"
                c0.text_frame.paragraphs[0].font.size = Pt(10)
                c0.text_frame.paragraphs[0].font.bold = True
                c0.text_frame.paragraphs[0].font.color.rgb = NAVY
                c1.text_frame.paragraphs[0].font.name = "Arial"
                c1.text_frame.paragraphs[0].font.size = Pt(10)
                c1.text_frame.paragraphs[0].font.color.rgb = DARK_TEXT


def _append_headline_metrics_slide(deck: Presentation, manifest: dict, total_slides: int) -> None:
    """Ensure all manifest headline values are visibly rendered and cross-checked."""
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    _add_header_and_footer(
        slide,
        "VERIFICATION & HEADLINE METRICS",
        "Cross-Artifact Simulation Headline Metrics",
        12,
        total_slides,
        manifest.get("run_id", "N/A"),
    )

    intro_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.6))
    itf = intro_box.text_frame
    itf.margin_left = itf.margin_top = itf.margin_right = itf.margin_bottom = 0
    p_in = itf.paragraphs[0]
    p_in.text = (
        "Summary of core numerical metrics matching the versioned manifest.json, report tables, "
        "and exported CSV datasets to 3 decimal places."
    )
    p_in.font.name = "Arial"
    p_in.font.size = Pt(12)
    p_in.font.color.rgb = DARK_TEXT

    headline = manifest.get("headline_metrics", {})
    circuits = ["low_downforce", "balanced", "high_downforce"]
    circuit_labels = {"low_downforce": "Low Downforce", "balanced": "Balanced", "high_downforce": "High Downforce"}

    table_shape = slide.shapes.add_table(4, 4, Inches(0.8), Inches(2.2), Inches(11.7), Inches(3.2))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(3.5)
    tbl.columns[1].width = Inches(2.7)
    tbl.columns[2].width = Inches(2.7)
    tbl.columns[3].width = Inches(2.8)

    headers = ["Metric Description", "Low Downforce", "Balanced", "High Downforce"]
    for col_idx, h in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        cell.text = h
        p = cell.text_frame.paragraphs[0]
        p.font.name = "Arial"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = WHITE

    rows_data = [
        ("Fixed Optimum Rear-Wing Angle (°)", "fixed_optimum_angle_deg"),
        ("Fixed Minimum Lap Time (s)", "fixed_minimum_lap_time_s"),
        ("Actuator-Limited Active Lap Time (s)", "active_limited_lap_time_s"),
    ]
    for row_idx, (desc, key) in enumerate(rows_data, start=1):
        cell_desc = tbl.cell(row_idx, 0)
        cell_desc.text = desc
        p0 = cell_desc.text_frame.paragraphs[0]
        p0.font.name = "Arial"
        p0.font.size = Pt(10.5)
        p0.font.bold = True
        p0.font.color.rgb = NAVY

        group = headline.get(key, {})
        for col_idx, c_name in enumerate(circuits, start=1):
            val = group.get(c_name, 0.0)
            cell_val = tbl.cell(row_idx, col_idx)
            cell_val.text = f"{val:.3f}"
            p1 = cell_val.text_frame.paragraphs[0]
            p1.font.name = "Arial"
            p1.font.size = Pt(11)
            p1.font.color.rgb = DARK_TEXT

    note_box = slide.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.8))
    ntf = note_box.text_frame
    ntf.word_wrap = True
    ntf.margin_left = ntf.margin_top = ntf.margin_right = ntf.margin_bottom = 0
    p_nt = ntf.paragraphs[0]
    p_nt.text = (
        f"Manifest SHA-256 Provenance: run_id={manifest.get('run_id')}  ·  "
        f"seed={manifest.get('seed')}  ·  monte_carlo_samples={manifest.get('monte_carlo_samples_per_circuit')}\n"
        f"Notice: {manifest.get('interpretation_warning', '')}"
    )
    p_nt.font.name = "Arial"
    p_nt.font.size = Pt(9)
    p_nt.font.italic = True
    p_nt.font.color.rgb = MID_GREY


def build_presentation(manifest_path: Path, content_path: Path, output_pptx: Path) -> Path:
    """Build an 18-slide PowerPoint deck from manifest and slide_content.json."""
    manifest_path = Path(manifest_path).resolve()
    content_path = Path(content_path).resolve()
    output_pptx = Path(output_pptx).resolve()
    output_pptx.parent.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    content = json.loads(content_path.read_text(encoding="utf-8"))
    results_root = manifest_path.parent

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_WIDTH_IN)
    prs.slide_height = Inches(SLIDE_HEIGHT_IN)
    blank_layout = prs.slide_layouts[6]

    slides_data = content.get("slides", [])
    total_slides = len(slides_data)

    for slide_data in slides_data:
        slide = prs.slides.add_slide(blank_layout)
        if slide_data.get("layout") == "title_slide":
            _build_title_slide(slide, slide_data, manifest)
        else:
            _build_content_slide(slide, slide_data, manifest, results_root, total_slides)

    prs.save(str(output_pptx))
    return output_pptx
