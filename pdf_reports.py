from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
    KeepTogether
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from xml.sax.saxutils import escape
import os
from datetime import date as date_cls
from pathlib import Path

from riskometer_report import build_riskometer_story
from stock_style_report import build_style_story
from portfolio_disparity_report import build_disparity_story


class NumberedCanvas(canvas.Canvas):
    logo_path = Path(__file__).resolve().parent / "public" / "logo.png"

    HEADER_HEIGHT_RATIO = 0.10
    FOOTER_HEIGHT_RATIO = 0.10

    def __init__(self, *args, report_number=None, **kwargs):
        self.report_number = report_number
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for page_number, state in enumerate(self._saved_page_states, start=1):
            self.__dict__.update(state)
            self._pageNumber = page_number
            self.draw_page_chrome(total_pages, page_number)
            super().showPage()
        super().save()

    def draw_page_chrome(self, page_count, page_number):
        width, height = self._pagesize
        header_height = height * self.HEADER_HEIGHT_RATIO
        footer_height = height * self.FOOTER_HEIGHT_RATIO
        self.saveState()
        self.resetTransforms()

        # Header band (10% of page height): logo left, report number right.
        self.setFillColor(colors.white)
        self.rect(0, height - header_height, width, header_height, fill=1, stroke=0)
        if self.logo_path.exists():
            logo_height = header_height * 0.5
            self.drawImage(
                str(self.logo_path),
                30,
                height - header_height + (header_height - logo_height) / 2,
                width=logo_height * 3.9,
                height=logo_height,
                preserveAspectRatio=True,
                anchor="w",
                mask="auto",
            )
        report_number = self.report_number or "—"
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(width - 30, height - header_height / 2 + 6, "REPORT NUMBER")
        self.setFont("Helvetica-Bold", 11)
        self.setFillColor(colors.HexColor("#123A63"))
        self.drawRightString(width - 30, height - header_height / 2 - 8, report_number)
        self.setStrokeColor(colors.HexColor("#DCE6EB"))
        self.line(30, height - header_height, width - 30, height - header_height)

        # Footer band (10% of page height): brand line left, page count right.
        self.setFillColor(colors.white)
        self.rect(0, 0, width, footer_height, fill=1, stroke=0)
        self.setStrokeColor(colors.HexColor("#DCE6EB"))
        self.line(30, footer_height, width - 30, footer_height)
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#123A63"))
        self.drawString(30, footer_height / 2 - 2, "Growth Avenues | Portfolio Analysis Report")
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawCentredString(width / 2, footer_height / 2 - 2, report_number)
        self.drawRightString(width - 30, footer_height / 2 - 2, f"Page {page_number:02d} / {page_count:02d}")
        self.restoreState()


class PortfolioPDF:
    def __init__(
        self,
        analysis,
        chart_paths,
        risk_analysis=None,
        style_analysis=None,
        disparity_analysis=None,
        output_path="output/portfolio_report.pdf",
        report_options=None,
    ):
        self.analysis = analysis
        self.chart_paths = chart_paths
        self.risk_analysis = risk_analysis
        self.style_analysis = style_analysis
        self.disparity_analysis = disparity_analysis
        self.report_options = report_options or {}
        self.enabled_sections = self.report_options.get("sections", {})
        self.report_number = self.report_options.get("report_number")
        self.enabled_benchmarks = self.report_options.get("benchmarks", {})

        self.portfolio = analysis["portfolio"]
        self.summary = analysis["summary"]
        self.sector = analysis["sector"]
        self.industry = analysis["industry"]
        self.market_cap = analysis["market_cap"]
        self.benchmarks = {
            key: data for key, data in analysis["benchmarks"].items()
            if self.enabled_benchmarks.get(data["name"], True)
        }

        self.elements = []

        page_width, page_height = landscape(A4)
        header_height = page_height * NumberedCanvas.HEADER_HEIGHT_RATIO
        footer_height = page_height * NumberedCanvas.FOOTER_HEIGHT_RATIO

        self.doc = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            rightMargin=34,
            leftMargin=34,
            topMargin=header_height + 14,
            bottomMargin=footer_height + 14
        )

        self.styles = getSampleStyleSheet()
        self._build_styles()

        self.primary = colors.HexColor("#123A63")
        self.secondary = colors.HexColor("#0E8290")
        self.accent = colors.HexColor("#E6F4F2")
        self.light_bg = colors.HexColor("#F5F9F8")
        self.border = colors.HexColor("#DCE6EB")
        self.text_muted = colors.HexColor("#475569")
        self.success = colors.HexColor("#16A34A")
        self.danger = colors.HexColor("#DC2626")

    def _build_styles(self):
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=29,
            leading=35,
            alignment=TA_LEFT,
            textColor=colors.white,
            spaceAfter=10
        )

        self.cover_subtitle = ParagraphStyle(
            "CoverSubtitle",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#D6E8EE")
        )

        self.heading_style = ParagraphStyle(
            "CustomHeading",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#123A63"),
            spaceAfter=8
        )

        self.sub_heading = ParagraphStyle(
            "CustomSubHeading",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#0E8290")
        )

        self.normal_style = ParagraphStyle(
            "CustomBody",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#334155")
        )

        self.small_style = ParagraphStyle(
            "SmallText",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#64748B")
        )

        self.table_text_style = ParagraphStyle(
            "TableText",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1F2937"),
            wordWrap="CJK"
        )

        self.table_center_style = ParagraphStyle(
            "TableCenterText",
            parent=self.table_text_style,
            alignment=TA_CENTER
        )

        self.table_right_style = ParagraphStyle(
            "TableRightText",
            parent=self.table_text_style,
            alignment=TA_RIGHT
        )

        self.kpi_label = ParagraphStyle(
            "KPILabel",
            parent=self.styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#475569")
        )

        self.kpi_value = ParagraphStyle(
            "KPIValue",
            parent=self.styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#0F172A")
        )

    def _safe_image(self, path, width, height):
        if path and os.path.exists(path):
            return Image(path, width=width, height=height)
        return Paragraph("Chart not available", self.small_style)

    def _centered_image(self, path, width, height):

        image = self._safe_image(
            path,
            width,
            height
        )


        container = Table(
            [[image]],
            colWidths=[self.doc.width]
        )


        container.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )


        return container

    def _two_column_slide(self, left, image_path, *, image_width=370, image_height=270):
        chart = self._safe_image(image_path, image_width, image_height)
        layout = Table([[left, chart]], colWidths=[self.doc.width * 0.50, self.doc.width * 0.47], hAlign="LEFT")
        layout.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 14),
            ("LEFTPADDING", (1, 0), (1, 0), 10),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return layout

    def _two_column_table_width(self):
        # Matches the left cell of _two_column_slide (50% of doc.width, minus its 14pt right padding).
        return self.doc.width * 0.50 - 14

    def _ensure_page_break(self):
        # Avoids stacking two consecutive PageBreaks (which renders as a blank page) when a
        # section that always ends with its own break is immediately followed by one that
        # starts with its own leading break.
        if self.elements and not isinstance(self.elements[-1], PageBreak):
            self.elements.append(PageBreak())

    def _report_dates_caption(self):
        report_generated_text = date_cls.today().strftime("%d %b %Y")
        caption = f"Report generated: {report_generated_text}"

        market_data_date = self.summary.get("market_data_date")
        if market_data_date:
            try:
                market_data_text = date_cls.fromisoformat(str(market_data_date)).strftime("%d %b %Y")
            except ValueError:
                market_data_text = str(market_data_date)
            caption += f"  &middot;  Market data as of: {market_data_text}"

        return caption

    def _table_cell(self, value, style=None):

        if style is None:

            style = self.table_text_style


        return Paragraph(
            escape(str(value)),
            style
        )

    def _section_title(self, title, subtitle=None):
        kicker = Paragraph("PORTFOLIO ANALYSIS", ParagraphStyle("Kicker", parent=self.small_style, fontName="Helvetica-Bold", fontSize=7, textColor=colors.HexColor("#0E8290"), spaceAfter=2))
        items = [kicker, Paragraph(title, self.heading_style), Spacer(1, 2)]
        if subtitle:
            items.append(Paragraph(subtitle, self.small_style))
            items.append(Spacer(1, 10))
        else:
            items.append(Spacer(1, 8))
        return items

    def _build_kpi_table(self):
        risk_color = self.danger if str(self.summary["concentration_risk"]).upper() == "HIGH" else self.success

        data = [
            [
                Paragraph("<b>Total Value</b><br/><font size='14'>Rs. {:,.0f}</font>".format(self.summary["total_portfolio_value"]), self.normal_style),
                Paragraph("<b>Holdings</b><br/><font size='14'>{}</font>".format(self.summary["total_holdings"]), self.normal_style),
                Paragraph("<b>Sectors</b><br/><font size='14'>{}</font>".format(self.summary["total_sectors"]), self.normal_style),
                Paragraph("<b>Industries</b><br/><font size='14'>{}</font>".format(self.summary["total_industries"]), self.normal_style),
                Paragraph("<b>Diversification</b><br/><font size='14'>{}</font>".format(self.summary["diversification"]), self.normal_style),
                Paragraph(
                    "<b>Concentration Risk</b><br/><font color='{}'>{}</font>".format(
                        risk_color.hexval().replace("0x", "#"),
                        self.summary["concentration_risk"]
                    ),
                    self.normal_style
                ),
            ],
            [
                Paragraph("<b>Largest Sector</b><br/><font size='14'>{} ({}%)</font>".format(escape(str(self.summary["largest_sector"])), self.summary["largest_sector_weight"]), self.normal_style),
                "",
                Paragraph("<b>Largest Industry</b><br/><font size='14'>{} ({}%)</font>".format(escape(str(self.summary["largest_industry"])), self.summary["largest_industry_weight"]), self.normal_style),
                "",
                Paragraph("<b>Top 2 Holdings</b><br/><font size='14'>{:.2f}%</font>".format(self.summary["top2_weight"]), self.normal_style),
                Paragraph("<b>Top 5 Holdings</b><br/><font size='14'>{:.2f}%</font>".format(self.summary["top5_weight"]), self.normal_style),
            ],
        ]

        table = Table(data, colWidths=[self.doc.width / 6] * 6, rowHeights=[68, 68])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, self.border),
            ("INNERGRID", (0, 0), (-1, -1), 0.6, self.border),
            ("SPAN", (0, 1), (1, 1)),
            ("SPAN", (2, 1), (3, 1)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        return table

    def _styled_table(self, data, col_widths=None, font_size=8, alignments=None, repeat_rows=1):
        table = Table(data, colWidths=col_widths, repeatRows=repeat_rows)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), font_size),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, self.border),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 1), (-1, -1), font_size),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1F2937")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ]

        if alignments:
            for col_idx, alignment in alignments.items():
                style_cmds.append(("ALIGN", (col_idx, 0), (col_idx, -1), alignment))
        else:
            style_cmds.append(("ALIGN", (0, 0), (-1, -1), "CENTER"))

        table.setStyle(TableStyle(style_cmds))
        return table

    def add_cover_page(self):
        title = Paragraph(escape(self.report_options.get("title", "Portfolio Analysis Report")), self.title_style)
        subtitle = Paragraph(escape(self.report_options.get("subtitle", "A complete view of portfolio structure, risk, style, and performance.")), self.cover_subtitle)
        cover_data = [[title], [subtitle]]
        cover = Table(cover_data, colWidths=[self.doc.width], rowHeights=[58, 48])
        cover.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#123A63")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))

        self.elements.append(cover)
        self.elements.append(Spacer(1, 8))
        self.elements.append(Paragraph(self._report_dates_caption(), self.small_style))
        self.elements.append(Spacer(1, 10))
        self.elements.append(self._build_kpi_table())
        self._ensure_page_break()

    def add_holdings_table(self):
        self.elements.extend(self._section_title(
            "Portfolio Holdings",
            "Detailed holding-wise view with exposure, value, and weight contribution."
        ))

        data = [[
            "ISIN", "Company", "Cap", "Sector", "Industry", "Qty", "CMP", "Value", "Weight %"
        ]]

        for _, row in self.portfolio.iterrows():
            data.append([
                self._table_cell(
                    row["isin"],
                    self.table_center_style
                ),
                self._table_cell(
                    row["security_name"]
                ),
                self._table_cell(
                    row["cap_category"],
                    self.table_center_style
                ),
                self._table_cell(
                    row["sector"]
                ),
                self._table_cell(
                    row["industry"]
                ),
                self._table_cell(
                    int(row["quantity"]),
                    self.table_right_style
                ),
                self._table_cell(
                    f"{row['current_market_price']:.2f}",
                    self.table_right_style
                ),
                self._table_cell(
                    f"{row['value']:,.2f}",
                    self.table_right_style
                ),
                self._table_cell(
                    f"{row['weight_percent']:.2f}%",
                    self.table_right_style
                )
            ])

        col_widths = [82, 120, 52, 100, 105, 45, 52, 75, 50]

        table = self._styled_table(
            data,
            col_widths=col_widths,
            font_size=6.5,
            alignments={
                0: "CENTER",
                1: "LEFT",
                2: "CENTER",
                3: "LEFT",
                4: "LEFT",
                5: "RIGHT",
                6: "RIGHT",
                7: "RIGHT",
                8: "RIGHT"
            },
            repeat_rows=1
        )

        self.elements.append(table)
        self._ensure_page_break()

    def add_sector_page(self):
        self.elements.extend(self._section_title(
            "Sector Allocation",
            "Portfolio exposure grouped by sector."
        ))

        table_data = [["Sector", "Value (Rs.)", "Allocation %"]]
        for _, row in self.sector.iterrows():
            table_data.append([
                row["sector"],
                f"{row['value']:,.2f}",
                f"{row['allocation_percent']:.2f}%"
            ])

        available = self._two_column_table_width()
        table = self._styled_table(
            table_data,
            col_widths=[available * 0.45, available * 0.30, available * 0.25],
            font_size=8,
            alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
        )

        self.elements.append(self._two_column_slide(table, self.chart_paths.get("sector_donut")))
        self._ensure_page_break()

    def add_industry_page(self):
        self.elements.extend(self._section_title(
            "Industry Allocation",
            "Portfolio exposure grouped by industry classification."
        ))

        table_data = [["Industry", "Value (Rs.)", "Allocation %"]]
        for _, row in self.industry.iterrows():
            table_data.append([
                row["industry"],
                f"{row['value']:,.2f}",
                f"{row['allocation_percent']:.2f}%"
            ])

        if len(table_data) <= 18:
            available = self._two_column_table_width()
            table = self._styled_table(
                table_data,
                col_widths=[available * 0.45, available * 0.30, available * 0.25],
                font_size=8,
                alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
            )
            self.elements.append(self._two_column_slide(table, self.chart_paths.get("industry_donut")))
        else:
            table = self._styled_table(
                table_data,
                col_widths=[self.doc.width * 0.45, self.doc.width * 0.30, self.doc.width * 0.25],
                font_size=8,
                alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
            )
            self.elements.append(table)
            self._ensure_page_break()
            self.elements.extend(self._section_title("Industry Allocation - Visual", "Portfolio exposure across industries."))
            self.elements.append(self._centered_image(self.chart_paths.get("industry_donut"), 7.1 * inch, 4.65 * inch))
        self._ensure_page_break()

    def add_market_cap_page(self):
        self.elements.extend(self._section_title(
            "Market Cap Allocation",
            "Exposure split across large cap, mid cap, small cap, and others."
        ))

        table_data = [["Cap Category", "Value (Rs.)", "Allocation %"]]
        for _, row in self.market_cap.iterrows():
            table_data.append([
                row["cap_category"],
                f"{row['value']:,.2f}",
                f"{row['allocation_percent']:.2f}%"
            ])

        available = self._two_column_table_width()
        table = self._styled_table(
            table_data,
            col_widths=[available * 0.45, available * 0.30, available * 0.25],
            font_size=8,
            alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
        )

        self.elements.append(self._two_column_slide(table, self.chart_paths.get("market_cap_donut")))
        self._ensure_page_break()

    def add_top_holdings_page(self):
        self.elements.extend(self._section_title(
            "Top Holdings",
            "Largest positions that drive portfolio concentration."
        ))

        table_data = [["Company", "Weight (%)", "Value (Rs.)"]]
        top10 = self.portfolio.head(10)

        for _, row in top10.iterrows():
            table_data.append([
                row["security_name"][:35],
                f"{row['weight_percent']:.2f}%",
                f"{row['value']:,.2f}"
            ])

        available = self._two_column_table_width()
        table = self._styled_table(
            table_data,
            col_widths=[available * 0.58, available * 0.21, available * 0.21],
            font_size=8,
            alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
        )

        self.elements.append(self._two_column_slide(table, self.chart_paths.get("top_holdings"), image_width=365, image_height=245))
        self._ensure_page_break()


    def add_benchmark_page(
        self,
        benchmark_key,
        benchmark_data
    ):

        benchmark_name = benchmark_data["name"]

        self.elements.extend(
            self._section_title(
                f"{benchmark_name} vs Client Sector Allocation",
                "Visual comparison with percentage labels for every non-zero sector allocation."
            )
        )

        left_chart = self._safe_image(self.chart_paths.get(f"{benchmark_key}_sector_donut_comparison"), 370, 270)
        right_chart = self._safe_image(self.chart_paths.get(f"{benchmark_key}_vs_client"), 370, 270)
        charts = Table([[left_chart, right_chart]], colWidths=[self.doc.width / 2] * 2)
        charts.setStyle(TableStyle([("VALIGN", (0,0),(-1,-1), "MIDDLE"), ("ALIGN",(0,0),(-1,-1),"CENTER"), ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),0)]))
        self.elements.append(charts)

        self._ensure_page_break()

    def add_benchmark_holdings_page(
        self,
        benchmark_data
    ):

        benchmark_name = benchmark_data["name"]

        benchmark_holdings = benchmark_data["holdings"]

        if benchmark_holdings.empty:

            return


        self.elements.extend(
            self._section_title(
                f"{benchmark_name} Top Holdings",
                f"Largest published holdings in the {benchmark_name} benchmark."
            )
        )


        table_data = [[
            "Company",
            "Benchmark Weight %"
        ]]


        for _, row in benchmark_holdings.iterrows():

            table_data.append([
                str(row["company"]),
                f"{row['benchmark_weight']:.2f}%"
            ])


        table = self._styled_table(
            table_data,
            col_widths=[330, 160],
            font_size=8,
            alignments={
                0: "LEFT",
                1: "RIGHT"
            }
        )


        self.elements.append(table)

        self._ensure_page_break()

    def generate(self):
        self.add_cover_page()
        enabled = lambda key: self.enabled_sections.get(key, True)
        if enabled("holdings"): self.add_holdings_table()
        if enabled("sector"): self.add_sector_page()
        if enabled("industry"): self.add_industry_page()
        if enabled("market_cap"): self.add_market_cap_page()
        if enabled("top_holdings"): self.add_top_holdings_page()

        for benchmark_key, benchmark_data in self.benchmarks.items() if enabled("benchmarks") else []:

            self.add_benchmark_page(
                benchmark_key,
                benchmark_data
            )

        if self.disparity_analysis and enabled("disparity"):
            self._ensure_page_break()
            self.elements.extend(
                build_disparity_story(
                    self.disparity_analysis,
                    self.doc.width,
                    Path("output"),
                    benchmark_names=[
                        name for name in ("Nifty 50", "Nifty Midcap 150", "Nifty 500")
                        if self.enabled_benchmarks.get(name, True)
                    ],
                )
            )

        if self.risk_analysis and enabled("risk"):
            self._ensure_page_break()
            self.elements.extend(
                build_riskometer_story(
                    self.risk_analysis,
                    self.doc.width,
                    Path("output"),
                )
            )

        if self.style_analysis and enabled("style"):
            self._ensure_page_break()
            self.elements.extend(
                build_style_story(
                    self.style_analysis,
                    self.doc.width,
                    Path("output"),
                )
            )

        while self.elements and isinstance(self.elements[-1], PageBreak):
            self.elements.pop()

        self.doc.build(
            self.elements,
            canvasmaker=lambda *args, **kwargs: NumberedCanvas(*args, report_number=self.report_number, **kwargs)
        )

        print("\n========== PDF GENERATED ==========\n")
        print("Saved : output/portfolio_report.pdf")
