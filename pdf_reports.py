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
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from xml.sax.saxutils import escape
import os
from pathlib import Path

from riskometer_report import build_riskometer_story
from stock_style_report import build_style_story
from portfolio_returns_report import build_returns_story


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_footer(total_pages)
            super().showPage()
        super().save()

    def draw_page_footer(self, page_count):
        self.setStrokeColor(colors.HexColor("#D9E2EC"))
        self.line(30, 25, 565, 25)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6B7280"))
        self.drawString(30, 12, "Portfolio Analysis Report")
        self.drawRightString(565, 12, f"Page {self._pageNumber} of {page_count}")


class PortfolioPDF:
    def __init__(
        self,
        analysis,
        chart_paths,
        risk_analysis=None,
        style_analysis=None,
        returns_analysis=None,
        output_path="output/portfolio_report.pdf",
        report_options=None,
    ):
        self.analysis = analysis
        self.chart_paths = chart_paths
        self.risk_analysis = risk_analysis
        self.style_analysis = style_analysis
        self.returns_analysis = returns_analysis
        self.report_options = report_options or {}
        self.enabled_sections = self.report_options.get("sections", {})

        self.portfolio = analysis["portfolio"]
        self.summary = analysis["summary"]
        self.sector = analysis["sector"]
        self.industry = analysis["industry"]
        self.market_cap = analysis["market_cap"]
        self.benchmarks = analysis["benchmarks"]

        self.elements = []

        self.doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=28,
            leftMargin=28,
            topMargin=30,
            bottomMargin=35
        )

        self.styles = getSampleStyleSheet()
        self._build_styles()

        self.primary = colors.HexColor("#0F172A")
        self.secondary = colors.HexColor("#1D4ED8")
        self.accent = colors.HexColor("#E8F0FE")
        self.light_bg = colors.HexColor("#F8FAFC")
        self.border = colors.HexColor("#D9E2EC")
        self.text_muted = colors.HexColor("#475569")
        self.success = colors.HexColor("#16A34A")
        self.danger = colors.HexColor("#DC2626")

    def _build_styles(self):
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.white,
            spaceAfter=10
        )

        self.cover_subtitle = ParagraphStyle(
            "CoverSubtitle",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.white
        )

        self.heading_style = ParagraphStyle(
            "CustomHeading",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=22,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=8
        )

        self.sub_heading = ParagraphStyle(
            "CustomSubHeading",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1E3A8A")
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

    def _table_cell(self, value, style=None):

        if style is None:

            style = self.table_text_style


        return Paragraph(
            escape(str(value)),
            style
        )

    def _section_title(self, title, subtitle=None):
        items = [Paragraph(title, self.heading_style), Spacer(1, 4)]
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
                Paragraph("<b>Total Value</b><br/>Rs. {:,.2f}".format(self.summary["total_portfolio_value"]), self.normal_style),
                Paragraph("<b>Total Holdings</b><br/>{}".format(self.summary["total_holdings"]), self.normal_style),
                Paragraph("<b>Total Sectors</b><br/>{}".format(self.summary["total_sectors"]), self.normal_style),
            ],
            [
                Paragraph("<b>Total Industries</b><br/>{}".format(self.summary["total_industries"]), self.normal_style),
                Paragraph("<b>Diversification</b><br/>{}".format(self.summary["diversification"]), self.normal_style),
                Paragraph(
                    "<b>Concentration Risk</b><br/><font color='{}'>{}</font>".format(
                        risk_color.hexval().replace("0x", "#"),
                        self.summary["concentration_risk"]
                    ),
                    self.normal_style
                ),
            ]
        ]

        table = Table(data, colWidths=[170, 170, 170], rowHeights=[60, 60])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, self.border),
            ("INNERGRID", (0, 0), (-1, -1), 0.8, self.border),
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
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ]

        if alignments:
            for col_idx, alignment in alignments.items():
                style_cmds.append(("ALIGN", (col_idx, 0), (col_idx, -1), alignment))
        else:
            style_cmds.append(("ALIGN", (0, 0), (-1, -1), "CENTER"))

        table.setStyle(TableStyle(style_cmds))
        return table

    def add_cover_page(self):
        cover_data = [[
            Paragraph(escape(self.report_options.get("title", "Portfolio Analysis Report")), self.title_style)
        ]]

        cover = Table(cover_data, colWidths=[530], rowHeights=[120])
        cover.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))

        self.elements.append(cover)
        self.elements.append(Spacer(1, 30))

        intro = "<para align='center'>{}</para>".format(escape(self.report_options.get("subtitle", "A visually summarized review of portfolio holdings, diversification, allocation mix, and concentration indicators.")))
        self.elements.append(Paragraph(intro, self.normal_style))
        self.elements.append(Spacer(1, 30))
        self.elements.append(self._build_kpi_table())
        self.elements.append(Spacer(1, 30))

        summary_block = f"""
        <b>Largest Sector:</b> {self.summary['largest_sector']} ({self.summary['largest_sector_weight']}%)<br/>
        <b>Largest Industry:</b> {self.summary['largest_industry']} ({self.summary['largest_industry_weight']}%)<br/>
        <b>Top 2 Holdings Weight:</b> {self.summary['top2_weight']:.2f}%<br/>
        <b>Top 5 Holdings Weight:</b> {self.summary['top5_weight']:.2f}%
        """
        self.elements.append(Paragraph(summary_block, self.normal_style))
        self.elements.append(PageBreak())

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

        col_widths = [
            70,
            90,
            50,
            75,
            80,
            34,
            42,
            58,
            40
        ]

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
        self.elements.append(PageBreak())

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

        table = self._styled_table(
            table_data,
            col_widths=[220, 150, 120],
            font_size=8,
            alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
        )

        self.elements.append(KeepTogether([
            table,
            Spacer(1, 18),
            self._centered_image(
                self.chart_paths.get("sector_donut"),
                5.8 * inch,
                4.22 * inch
            )
        ]))
        self.elements.append(PageBreak())

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

        table = self._styled_table(
            table_data,
            col_widths=[220, 150, 120],
            font_size=8,
            alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
        )

        self.elements.append(KeepTogether([
            table,
            Spacer(1, 18),
            self._centered_image(
                self.chart_paths.get("industry_donut"),
                5.8 * inch,
                4.22 * inch
            )
        ]))
        self.elements.append(PageBreak())

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

        table = self._styled_table(
            table_data,
            col_widths=[220, 150, 120],
            font_size=8,
            alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
        )

        self.elements.append(KeepTogether([
            table,
            Spacer(1, 18),
            self._centered_image(
                self.chart_paths.get("market_cap_donut"),
                5.8 * inch,
                4.22 * inch
            )
        ]))
        self.elements.append(PageBreak())

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

        table = self._styled_table(
            table_data,
            col_widths=[290, 100, 100],
            font_size=8,
            alignments={0: "LEFT", 1: "RIGHT", 2: "RIGHT"}
        )

        self.elements.append(KeepTogether([
            table,
            Spacer(1, 18),
            self._centered_image(
                self.chart_paths.get("top_holdings"),
                6.5 * inch,
                4 * inch
            )
        ]))
        self.elements.append(PageBreak())


    def add_benchmark_page(
        self,
        benchmark_key,
        benchmark_data
    ):

        benchmark_name = benchmark_data["name"]

        comparison = benchmark_data["comparison"].copy()

        self.elements.extend(
            self._section_title(
                f"Benchmark Comparison ({benchmark_name})",
                f"Comparison of sector allocation against the {benchmark_name} benchmark."
            )
        )

        table_data = [[
            "Sector",
            f"{benchmark_name} %",
            "Portfolio %",
            "Difference"
        ]]

        for _, row in comparison.iterrows():

            diff = row["difference"]

            if diff > 0:
                diff_text = f"+{diff:.2f}%"
            else:
                diff_text = f"{diff:.2f}%"

            table_data.append([
                str(row["sector"]),
                f"{row['benchmark_weight']:.2f}%",
                f"{row['client_weight']:.2f}%",
                diff_text
            ])

        table = self._styled_table(
            table_data,
            col_widths=[220, 90, 90, 90],
            font_size=8,
            alignments={
                0: "LEFT",
                1: "RIGHT",
                2: "RIGHT",
                3: "RIGHT"
            }
        )

        self.elements.append(table)

        self.elements.append(PageBreak())

        self.elements.extend(
            self._section_title(
                "Sector Allocation Charts",
                f"Client portfolio and {benchmark_name} sector allocations shown side by side."
            )
        )

        self.elements.append(
            self._centered_image(
                self.chart_paths.get(
                    f"{benchmark_key}_sector_donut_comparison"
                ),
                7.2 * inch,
                4.37 * inch
            )
        )

        self.elements.append(Spacer(1, 12))

        self.elements.append(
            self._centered_image(
                self.chart_paths.get(
                    f"{benchmark_key}_vs_client"
                ),
                7 * inch,
                4.31 * inch
            )
        )

        self.elements.append(PageBreak())

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

        self.elements.append(PageBreak())

    def add_insights_page(self):
        self.elements.extend(self._section_title(
            "Portfolio Insights",
            "A quick narrative summary of concentration and diversification indicators."
        ))

        summary = self.summary

        insights_data = [
            ["Metric", "Observation"],
            ["Total Portfolio Value", f"Rs. {summary['total_portfolio_value']:,.2f}"],
            ["Total Holdings", str(summary["total_holdings"])],
            ["Total Sectors", str(summary["total_sectors"])],
            ["Total Industries", str(summary["total_industries"])],
            ["Largest Sector", f"{summary['largest_sector']} ({summary['largest_sector_weight']}%)"],
            ["Largest Industry", f"{summary['largest_industry']} ({summary['largest_industry_weight']}%)"],
            ["Top 2 Holdings Weight", f"{summary['top2_weight']:.2f}%"],
            ["Top 5 Holdings Weight", f"{summary['top5_weight']:.2f}%"],
            ["Diversification Score", str(summary["diversification"])],
            ["Concentration Risk", str(summary["concentration_risk"])],
        ]

        table = self._styled_table(
            insights_data,
            col_widths=[180, 290],
            font_size=8,
            alignments={0: "LEFT", 1: "LEFT"}
        )

        self.elements.append(table)

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

            self.add_benchmark_holdings_page(
                benchmark_data
            )

        if enabled("insights"): self.add_insights_page()

        if self.returns_analysis and enabled("performance"):
            self.elements.append(PageBreak())
            self.elements.extend(
                build_returns_story(
                    self.returns_analysis,
                    self.doc.width,
                    Path("output"),
                )
            )

        if self.risk_analysis and enabled("risk"):
            self.elements.append(PageBreak())
            self.elements.extend(
                build_riskometer_story(
                    self.risk_analysis,
                    self.doc.width,
                    Path("output"),
                )
            )

        if self.style_analysis and enabled("style"):
            self.elements.append(PageBreak())
            self.elements.extend(
                build_style_story(
                    self.style_analysis,
                    self.doc.width,
                    Path("output"),
                )
            )

        self.doc.build(self.elements, canvasmaker=NumberedCanvas)

        print("\n========== PDF GENERATED ==========\n")
        print("Saved : output/portfolio_report.pdf")
