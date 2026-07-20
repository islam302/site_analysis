"""Render a combined analysis result into a styled PDF (English or Arabic).

Arabic support requires three things reportlab does not do on its own:
1. an Arabic-capable TTF font (``settings.PDF_ARABIC_FONT``),
2. glyph *reshaping* (contextual letter joining) via ``arabic_reshaper``,
3. *bidi* reordering (RTL) via ``python-bidi``.
All display text passes through :meth:`_Builder.t` which applies these for ``ar``.
"""
from __future__ import annotations

import logging
import unicodedata
from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.full_report.explanations import get_explanations
from apps.full_report.labels import LABELS
from apps.full_report.recommendations import build_recommendations, recommendations_intro

logger = logging.getLogger("apps.full_report")

# Palette
NAVY = colors.HexColor("#0f172a")
ACCENT = colors.HexColor("#2563eb")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#cbd5e1")
STRIPE = colors.HexColor("#f1f5f9")
GOOD, WARN, POOR, NA = (
    colors.HexColor("#16a34a"),
    colors.HexColor("#d97706"),
    colors.HexColor("#dc2626"),
    colors.HexColor("#64748b"),
)
GOOD_BG, WARN_BG, POOR_BG, NA_BG = (
    colors.HexColor("#dcfce7"),
    colors.HexColor("#ffedd5"),
    colors.HexColor("#fee2e2"),
    colors.HexColor("#f1f5f9"),
)

_ARABIC_FONT = None  # resolved font family name once registered ("AR" or fallback)
_ARABIC_CMAP: frozenset[int] = frozenset()  # codepoints the registered Arabic font has


def _ensure_arabic_font() -> str:
    """Register the Arabic TTF once; return its family name (fallback: Helvetica)."""
    global _ARABIC_FONT, _ARABIC_CMAP
    if _ARABIC_FONT is not None:
        return _ARABIC_FONT
    try:
        pdfmetrics.registerFont(TTFont("AR", settings.PDF_ARABIC_FONT))
        bold = settings.PDF_ARABIC_FONT_BOLD or settings.PDF_ARABIC_FONT
        pdfmetrics.registerFont(TTFont("AR-Bold", bold))
        pdfmetrics.registerFontFamily("AR", normal="AR", bold="AR-Bold")
        _ARABIC_CMAP = frozenset(pdfmetrics.getFont("AR").face.charToGlyph)
        _ARABIC_FONT = "AR"
    except Exception as exc:  # noqa: BLE001 - degrade gracefully if font missing
        logger.warning("Arabic font unavailable (%s); Arabic text may not render.", exc)
        _ARABIC_FONT = "Helvetica"
    return _ARABIC_FONT


def _font_fallback(text: str) -> str:
    """Swap any presentation-form glyph the font lacks for its base letter.

    Sans fonts like Tajawal shape Arabic via OpenType and omit the *isolated*
    presentation forms (U+FE8D …) that ``arabic_reshaper`` emits, which would
    render as tofu boxes. The base letter decomposes to the same isolated shape,
    so we substitute it whenever the exact form is missing. Font-agnostic no-op
    when the font already covers everything (e.g. Arial).
    """
    if not _ARABIC_CMAP:
        return text
    out = []
    for ch in text:
        if ord(ch) in _ARABIC_CMAP:
            out.append(ch)
            continue
        decomposed = unicodedata.normalize("NFKD", ch)
        repl = "".join(c for c in decomposed if ord(c) in _ARABIC_CMAP)
        out.append(repl or ch)
    return "".join(out)


def _rating(score, tr) -> tuple[str, colors.Color, colors.Color]:
    if score is None:
        return tr["na"], NA, NA_BG
    if score >= 90:
        return tr["good"], GOOD, GOOD_BG
    if score >= 50:
        return tr["warn"], WARN, WARN_BG
    return tr["poor"], POOR, POOR_BG


class _Builder:
    def __init__(self, lang: str):
        self.lang = "ar" if lang == "ar" else "en"
        self.tr = LABELS[self.lang]
        self.rtl = self.lang == "ar"
        self.align = TA_RIGHT if self.rtl else TA_LEFT
        if self.rtl:
            self.font = _ensure_arabic_font()
            self.font_bold = f"{self.font}-Bold" if self.font == "AR" else "Helvetica-Bold"
        else:
            self.font, self.font_bold = "Helvetica", "Helvetica-Bold"
        self._reshape = None
        self._bidi = None
        if self.rtl:
            import arabic_reshaper
            from bidi.algorithm import get_display

            self._reshape = arabic_reshaper.reshape
            self._bidi = get_display

    def t(self, text) -> str:
        """Shape + bidi-reorder text for Arabic; identity for English."""
        text = "" if text is None else str(text)
        if self.rtl and text:
            return _font_fallback(self._bidi(self._reshape(text)))
        return text

    def style(self, name, **kw) -> ParagraphStyle:
        kw.setdefault("fontName", self.font)
        kw.setdefault("alignment", self.align)
        return ParagraphStyle(name, **kw)

    def p(self, text, style) -> Paragraph:
        return Paragraph(self.t(text), style)


def _kv_table(builder: _Builder, rows: list[list[str]], widths) -> Table:
    header = builder.font_bold
    body = builder.font
    data = [[builder.t(c) for c in row] for row in rows]
    if builder.rtl:  # mirror columns so the label sits on the right
        data = [list(reversed(r)) for r in data]
        widths = list(reversed(widths))
    table = Table(data, colWidths=widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), header),
                ("FONTNAME", (0, 1), (-1, -1), body),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, STRIPE]),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT" if builder.rtl else "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _metric_table(builder: _Builder, entries: list[tuple], widths=(95 * mm, 79 * mm)) -> Table:
    """A Metric/Result table where each row carries a small grey explanation line
    underneath it (spanning the full width). ``entries`` is a list of
    ``(label, result, explanation)`` — pass ``""`` as explanation to omit the note.
    """
    tr = builder.tr
    hstyle = builder.style("mh", fontName=builder.font_bold, fontSize=9.5, textColor=colors.white)
    mstyle = builder.style("ml", fontName=builder.font_bold, fontSize=9.5, textColor=NAVY)
    rstyle = builder.style("mr", fontSize=9.5, textColor=NAVY)
    nstyle = builder.style("mn", fontSize=8, textColor=MUTED, leading=10.5)

    w = list(widths)
    header = [builder.p(tr["metric"], hstyle), builder.p(tr["result"], hstyle)]
    if builder.rtl:
        header = list(reversed(header))
        w = list(reversed(w))

    data = [header]
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT" if builder.rtl else "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    row = 1
    for block, (label, result, note) in enumerate(entries):
        mv = [builder.p(label, mstyle), builder.p(str(result), rstyle)]
        if builder.rtl:
            mv = list(reversed(mv))
        bg = colors.white if block % 2 == 0 else STRIPE
        data.append(mv)
        if note:
            data.append([builder.p(note, nstyle), ""])
            cmds += [
                ("SPAN", (0, row + 1), (-1, row + 1)),
                ("BACKGROUND", (0, row), (-1, row + 1), bg),
                ("LINEBELOW", (0, row + 1), (-1, row + 1), 0.4, LINE),
                ("BOTTOMPADDING", (0, row), (-1, row), 1),
                ("TOPPADDING", (0, row + 1), (-1, row + 1), 0),
            ]
            row += 2
        else:
            cmds += [
                ("BACKGROUND", (0, row), (-1, row), bg),
                ("LINEBELOW", (0, row), (-1, row), 0.4, LINE),
            ]
            row += 1

    table = Table(data, colWidths=w)
    table.setStyle(TableStyle(cmds))
    return table


def _banner(builder: _Builder) -> Table:
    tr = builder.tr
    title_style = builder.style("bt", fontName=builder.font_bold, fontSize=20,
                                textColor=colors.white, alignment=TA_CENTER, leading=24)
    sub_style = builder.style("bs", fontSize=10.5, textColor=colors.HexColor("#cbd5e1"),
                              alignment=TA_CENTER, leading=14)
    inner = [[builder.p(tr["title"], title_style)], [builder.p(tr["subtitle"], sub_style)]]
    t = Table(inner, colWidths=[174 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LINEBELOW", (0, -1), (-1, -1), 3, ACCENT),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return t


def _score_cards(builder: _Builder, scores: list[tuple[str, object]]) -> Table:
    """A dashboard row of coloured score cards (label, big number, rating)."""
    cells, styles_cmds = [], []
    big = builder.style("big", fontName=builder.font_bold, fontSize=22, alignment=TA_CENTER, leading=24)
    lbl = builder.style("lbl", fontSize=8.5, textColor=NAVY, alignment=TA_CENTER, leading=11)
    rate = builder.style("rate", fontSize=8, alignment=TA_CENTER, leading=10)
    for i, (label, score) in enumerate(scores):
        rating, colour, bg = _rating(score, builder.tr)
        num = "—" if score is None else str(score)
        num_p = Paragraph(f'<font color="{colour.hexval()}">{builder.t(num)}</font>', big)
        rate_p = Paragraph(f'<font color="{colour.hexval()}">{builder.t(rating)}</font>', rate)
        cells.append([num_p, builder.p(label, lbl), rate_p])
        styles_cmds += [
            ("BACKGROUND", (i, 0), (i, 0), bg),
            ("LINEBELOW", (i, 0), (i, 0), 2.5, colour),
        ]
    w = 174 * mm / len(scores)
    table = Table([cells], colWidths=[w] * len(scores))
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                *styles_cmds,
            ]
        )
    )
    return table


def _section_title(builder: _Builder, num: int, text: str) -> Table:
    st = builder.style("st", fontName=builder.font_bold, fontSize=13, textColor=NAVY, leading=16)
    para = builder.p(f"{num}.  {text}", st)
    t = Table([[para]], colWidths=[174 * mm])
    accent_side = (-1, -1) if builder.rtl else (0, 0)
    t.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", accent_side, accent_side, 4, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _fail_note(builder: _Builder, error: str) -> Paragraph:
    s = builder.style("fail", textColor=POOR, fontSize=9.5)
    return builder.p(f"{builder.tr['could_not_run']}: {error}", s)


def _skip_note(builder: _Builder) -> Paragraph:
    s = builder.style("skip", textColor=MUTED, fontSize=9.5)
    return builder.p(builder.tr["not_included"], s)


def _fmt(value, suffix=""):
    return "—" if value is None else f"{value}{suffix}"


def _ssl_grade_color(grade: str):
    g = (grade or "").upper()
    if g in ("A+", "A"):
        return GOOD, GOOD_BG
    if g in ("B", "C"):
        return WARN, WARN_BG
    return POOR, POOR_BG  # F, T (untrusted), or unknown


def _grade_badge(builder: _Builder, grade: str) -> Table:
    """A single coloured card showing the SSL security grade."""
    color, bg = _ssl_grade_color(grade)
    big = builder.style("gb", fontName=builder.font_bold, fontSize=22, alignment=TA_CENTER, leading=24)
    lbl = builder.style("gbl", fontSize=8.5, alignment=TA_CENTER, textColor=NAVY, leading=11)
    num = Paragraph(f'<font color="{color.hexval()}">{grade or "—"}</font>', big)
    table = Table([[[num, builder.p(builder.tr["ssl_grade"], lbl)]]], colWidths=[55 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), bg),
                ("LINEBELOW", (0, 0), (0, 0), 2.5, color),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def build_report_pdf(report: dict, lang: str = "en") -> bytes:
    """Return PDF bytes for a combined report. ``lang`` is ``en`` or ``ar``."""
    b = _Builder(lang)
    tr = b.tr
    ex = get_explanations(b.lang)  # per-metric plain-language notes
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title="Website Analysis Report",
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
    )
    meta = b.style("meta", fontSize=10, textColor=NAVY, leading=15)
    muted = b.style("muted", fontSize=9, textColor=MUTED, leading=13)
    story: list = [_banner(b), Spacer(1, 5 * mm)]

    story.append(b.p(f"<b>{tr['url']}:</b>  {report['url']}", meta))
    story.append(b.p(f"<b>{tr['strategy']}:</b>  {report['strategy']}", meta))
    gen = report["generated_at"]
    gen_str = gen.strftime("%Y-%m-%d %H:%M UTC") if hasattr(gen, "strftime") else str(gen)
    story.append(b.p(f"<b>{tr['generated']}:</b>  {gen_str}", muted))
    story.append(Spacer(1, 4 * mm))

    # 1) PageSpeed --------------------------------------------------------
    story.append(_section_title(b, 1, tr["ps_title"]))
    ps = report["pagespeed"]
    if ps["status"] == "skipped":
        story.append(_skip_note(b))
    elif ps["status"] != "ok":
        story.append(_fail_note(b, ps["error"]))
    else:
        d = ps["data"]
        story.append(_score_cards(b, [
            (tr["performance"], d.get("performance_score")),
            (tr["accessibility"], d.get("accessibility_score")),
            (tr["best_practices"], d.get("best_practices_score")),
            (tr["seo"], d.get("seo_score")),
        ]))
        story.append(Spacer(1, 3 * mm))
        story.append(_metric_table(b, [
            (tr["performance"], _fmt(d.get("performance_score")), ex["performance"]),
            (tr["accessibility"], _fmt(d.get("accessibility_score")), ex["accessibility"]),
            (tr["best_practices"], _fmt(d.get("best_practices_score")), ex["best_practices"]),
            (tr["seo"], _fmt(d.get("seo_score")), ex["seo"]),
            (tr["fcp"], _fmt(d.get("first_contentful_paint"), " s"), ex["fcp"]),
            (tr["lcp"], _fmt(d.get("largest_contentful_paint"), " s"), ex["lcp"]),
            (tr["tbt"], _fmt(d.get("total_blocking_time"), " ms"), ex["tbt"]),
            (tr["cls"], _fmt(d.get("cumulative_layout_shift")), ex["cls"]),
            (tr["si"], _fmt(d.get("speed_index"), " s"), ex["si"]),
        ]))
    story.append(Spacer(1, 5 * mm))

    # 2) GTmetrix ---------------------------------------------------------
    story.append(_section_title(b, 2, tr["gtm_title"]))
    gtm = report["gtmetrix"]
    if gtm["status"] == "skipped":
        story.append(_skip_note(b))
    elif gtm["status"] != "ok":
        story.append(_fail_note(b, gtm["error"]))
    else:
        d = gtm["data"]
        pb = d.get("page_bytes")
        story.append(_metric_table(b, [
            (tr["grade"], d.get("gtmetrix_grade") or "—", ex["grade"]),
            (tr["performance"], _fmt(d.get("performance_score")), ex["performance"]),
            (tr["structure"], _fmt(d.get("structure_score")), ex["structure"]),
            (tr["lcp"], _fmt(d.get("largest_contentful_paint"), " ms"), ex["lcp"]),
            (tr["tbt"], _fmt(d.get("total_blocking_time"), " ms"), ex["tbt"]),
            (tr["fully_loaded"], _fmt(d.get("fully_loaded_time"), " ms"), ex["fully_loaded"]),
            (tr["page_size"], f"{round(pb / 1024)} KB" if pb else "—", ex["page_size"]),
            (tr["requests"], _fmt(d.get("page_requests")), ex["requests"]),
        ]))
    story.append(Spacer(1, 5 * mm))

    # 3) Accessibility ----------------------------------------------------
    story.append(_section_title(b, 3, tr["wave_title"]))
    wave = report["accessibility"]
    if wave["status"] == "skipped":
        story.append(_skip_note(b))
    elif wave["status"] != "ok":
        story.append(_fail_note(b, wave["error"]))
    else:
        d = wave["data"]
        story.append(_metric_table(b, [
            (tr["wcag"], d.get("wcag_level") or tr["fails"], ex["wcag"]),
            (tr["errors"], _fmt(d.get("total_errors", 0)), ex["errors"]),
            (tr["contrast"], _fmt(d.get("total_contrast_errors", 0)), ex["contrast"]),
            (tr["alerts"], _fmt(d.get("total_alerts", 0)), ex["alerts"]),
            (tr["features"], _fmt(d.get("total_features", 0)), ex["features"]),
            (tr["structural"], _fmt(d.get("total_structural", 0)), ex["structural"]),
        ]))
        top = d.get("top_issues") or []
        if top:
            story.append(Spacer(1, 3 * mm))
            story.append(b.p(tr["top_issues"], muted))
            rows = [[tr["type"], tr["issue"], tr["count"]]]
            for issue in top:
                rows.append([issue.get("issue_type", ""), issue.get("description", ""),
                             str(issue.get("count", 0))])
            story.append(_kv_table(b, rows, [26 * mm, 128 * mm, 20 * mm]))
    story.append(Spacer(1, 5 * mm))

    # 4) SSL / TLS security ----------------------------------------------
    story.append(_section_title(b, 4, tr["ssl_title"]))
    ssl = report.get("ssl", {"status": "failed", "error": "not run", "data": {}})
    if ssl["status"] == "skipped":
        story.append(_skip_note(b))
    elif ssl["status"] != "ok":
        story.append(_fail_note(b, ssl["error"]))
    else:
        d = ssl["data"]
        story.append(_grade_badge(b, d.get("grade") or "—"))
        story.append(Spacer(1, 3 * mm))
        expires = d.get("cert_expires_in_days")
        trusted = d.get("cert_is_trusted")
        vulns = [k for k, v in (d.get("vulnerabilities") or {}).items() if v]
        story.append(_metric_table(b, [
            (tr["ssl_protocols"], ", ".join(d.get("protocols") or []) or "—", ex["ssl_protocols"]),
            (tr["ssl_cert_expiry"],
             f"{expires} {tr['days']}" if expires is not None else "—", ex["ssl_cert_expiry"]),
            (tr["ssl_trusted"],
             (tr["yes"] if trusted else tr["no"]) if trusted is not None else "—",
             ex["ssl_trusted"]),
            (tr["ssl_vulns"], ", ".join(vulns) if vulns else tr["none_found"], ex["ssl_vulns"]),
        ]))
    story.append(Spacer(1, 5 * mm))

    # 5) Broken link check ------------------------------------------------
    story.append(_section_title(b, 5, tr["links_title"]))
    links = report.get("links", {"status": "failed", "error": "not run", "data": {}})
    if links["status"] == "skipped":
        story.append(_skip_note(b))
    elif links["status"] != "ok":
        story.append(_fail_note(b, links["error"]))
    else:
        d = links["data"]
        story.append(_metric_table(b, [
            (tr["links_total"], _fmt(d.get("total_links", 0)), ex["links_total"]),
            (tr["links_healthy"], _fmt(d.get("healthy", 0)), ex["links_healthy"]),
            (tr["links_broken"], _fmt(d.get("broken", 0)), ex["links_broken"]),
            (tr["links_redirects"], _fmt(d.get("redirects", 0)), ex["links_redirects"]),
            (tr["links_timeouts"], _fmt(d.get("timeouts", 0)), ex["links_timeouts"]),
        ]))
        broken = d.get("broken_links") or []
        if broken:
            story.append(Spacer(1, 3 * mm))
            story.append(b.p(tr["links_broken_list"], muted))
            rows = [[tr["status_col"], tr["link_col"]]]
            for item in broken:
                rows.append([str(item.get("http_status") or "—"), item.get("target_url", "")])
            story.append(_kv_table(b, rows, [24 * mm, 150 * mm]))

    story.append(Spacer(1, 5 * mm))

    # 6) Structured data (Schema.org) -------------------------------------
    story.append(_section_title(b, 6, tr["sd_title"]))
    sd = report.get("structured_data", {"status": "failed", "error": "not run", "data": {}})
    if sd["status"] == "skipped":
        story.append(_skip_note(b))
    elif sd["status"] != "ok":
        story.append(_fail_note(b, sd["error"]))
    elif sd["data"].get("total_schemas", 0) == 0:
        story.append(b.p(tr["sd_none"], muted))
    else:
        d = sd["data"]
        formats = []
        if d.get("has_json_ld"):
            formats.append(tr["sd_json_ld"])
        if d.get("has_microdata"):
            formats.append(tr["sd_microdata"])
        if d.get("has_rdfa"):
            formats.append(tr["sd_rdfa"])
        story.append(_metric_table(b, [
            (tr["sd_total"], _fmt(d.get("total_schemas", 0)), ex["sd_total"]),
            (tr["sd_valid"], _fmt(d.get("valid_schemas", 0)), ex["sd_valid"]),
            (tr["sd_rich"], _fmt(d.get("rich_result_eligible", 0)), ex["sd_rich"]),
            (tr["sd_errors"], _fmt(d.get("total_errors", 0)), ex["sd_errors"]),
            (tr["sd_warnings"], _fmt(d.get("total_warnings", 0)), ex["sd_warnings"]),
            (tr["sd_formats"], ", ".join(formats) or "—", ex["sd_formats"]),
        ]))
        types = d.get("schemas") or []
        if types:
            story.append(Spacer(1, 3 * mm))
            story.append(b.p(tr["sd_types_found"], muted))
            rows = [[tr["sd_type_col"], tr["sd_format_col"], tr["sd_valid_col"]]]
            for item in types:
                rows.append([
                    item.get("schema_type", ""),
                    item.get("format", ""),
                    tr["yes"] if item.get("is_valid") else tr["no"],
                ])
            story.append(_kv_table(b, rows, [80 * mm, 64 * mm, 30 * mm]))
        issues = d.get("issues") or []
        if issues:
            story.append(Spacer(1, 3 * mm))
            story.append(b.p(tr["sd_issues_list"], muted))
            rows = [[tr["sd_type_col"], tr["sd_field_col"], tr["issue"]]]
            for item in issues:
                rows.append([
                    item.get("schema_type", ""),
                    item.get("field", ""),
                    item.get("message", ""),
                ])
            story.append(_kv_table(b, rows, [30 * mm, 50 * mm, 94 * mm]))
    story.append(Spacer(1, 5 * mm))

    # 7) Recommendations --------------------------------------------------
    story.append(_section_title(b, 7, tr["rec_title"]))
    story.append(b.p(recommendations_intro(b.lang), muted))
    story.append(Spacer(1, 2 * mm))
    rec_style = b.style("rec", fontSize=10, textColor=NAVY, leading=15)
    recs = build_recommendations(report, b.lang)
    rows = [[b.p(f"{i}.  {rec}", rec_style)] for i, rec in enumerate(recs, 1)]
    rec_table = Table(rows, colWidths=[174 * mm])
    rec_table.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, STRIPE]),
                ("LINEBEFORE", ((-1, 0) if b.rtl else (0, 0)),
                 ((-1, -1) if b.rtl else (0, -1)), 3, ACCENT),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(rec_table)

    story.append(Spacer(1, 8 * mm))
    story.append(b.p(tr["ratings_note"], muted))
    story.append(b.p(tr["footer"], muted))

    doc.build(story)
    return buffer.getvalue()
