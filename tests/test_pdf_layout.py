import pandas as pd

from market_etl.models import format_report_number
from pdf_reports import NumberedCanvas, PortfolioPDF


def _empty_analysis() -> dict:
    return {
        "portfolio": pd.DataFrame(),
        "summary": {},
        "sector": pd.DataFrame(),
        "industry": pd.DataFrame(),
        "market_cap": pd.DataFrame(),
        "benchmarks": {},
    }


def test_portfolio_report_uses_landscape_page_and_company_logo(tmp_path) -> None:
    report = PortfolioPDF(_empty_analysis(), {}, output_path=tmp_path / "report.pdf")
    width, height = report.doc.pagesize
    assert width > height
    assert NumberedCanvas.logo_path.exists()


def test_header_and_footer_each_reserve_ten_percent_of_page_height(tmp_path) -> None:
    report = PortfolioPDF(_empty_analysis(), {}, output_path=tmp_path / "report.pdf")
    _, page_height = report.doc.pagesize
    header_height = page_height * NumberedCanvas.HEADER_HEIGHT_RATIO
    footer_height = page_height * NumberedCanvas.FOOTER_HEIGHT_RATIO

    assert NumberedCanvas.HEADER_HEIGHT_RATIO == 0.10
    assert NumberedCanvas.FOOTER_HEIGHT_RATIO == 0.10
    assert report.doc.topMargin >= header_height
    assert report.doc.bottomMargin >= footer_height


def test_report_number_flows_from_options_into_the_pdf_and_canvas(tmp_path) -> None:
    report = PortfolioPDF(
        _empty_analysis(),
        {},
        output_path=tmp_path / "report.pdf",
        report_options={"report_number": "JBV-GA-001"},
    )
    assert report.report_number == "JBV-GA-001"


def test_format_report_number_produces_sequential_zero_padded_codes() -> None:
    assert format_report_number(1) == "JBV-GA-001"
    assert format_report_number(2) == "JBV-GA-002"
    assert format_report_number(42) == "JBV-GA-042"
    assert format_report_number(1234) == "JBV-GA-1234"
    assert format_report_number(None) is None


def test_generate_never_leaves_consecutive_or_trailing_page_breaks(tmp_path) -> None:
    from reportlab.platypus import PageBreak

    portfolio = pd.DataFrame([{
        "isin": "INE001A01036", "security_name": "Reliance Industries Ltd", "cap_category": "Large",
        "sector": "Energy", "industry": "Refineries", "quantity": 10, "current_market_price": 2500.5,
        "value": 25005.0, "weight_percent": 100.0,
    }])
    analysis = {
        "portfolio": portfolio,
        "summary": {
            "total_portfolio_value": 25005.0, "total_holdings": 1, "total_sectors": 1, "total_industries": 1,
            "diversification": "Low", "concentration_risk": "HIGH",
            "largest_sector": "Energy", "largest_sector_weight": 100.0,
            "largest_industry": "Refineries", "largest_industry_weight": 100.0,
            "top2_weight": 100.0, "top5_weight": 100.0,
        },
        "sector": pd.DataFrame([{"sector": "Energy", "value": 25005.0, "allocation_percent": 100.0}]),
        "industry": pd.DataFrame([{"industry": "Refineries", "value": 25005.0, "allocation_percent": 100.0}]),
        "market_cap": pd.DataFrame([{"cap_category": "Large", "value": 25005.0, "allocation_percent": 100.0}]),
        "benchmarks": {},
    }
    # This is the scenario that used to produce a blank page: an "old style" section
    # (market_cap) that always ends with its own trailing PageBreak, immediately followed by
    # a "new style" section (disparity) that used to unconditionally prepend its own leading
    # PageBreak -- with benchmarks/top_holdings switched off so nothing sits between them.
    disparity_analysis = {
        "since_date": pd.Timestamp("2020-01-01"),
        "as_of_date": pd.Timestamp("2026-08-18"),
        "invested_amount": 25005.0,
        "benchmark_names": ["Nifty 50"],
        "series": {
            "Portfolio": {"return_pct": 10.0, "stats": None},
            "Nifty 50": {"return_pct": 5.0, "stats": None},
        },
        "opportunity_loss": {"Nifty 50": {"disparity_pct": 5.0, "amount": 1250.25}},
    }

    report = PortfolioPDF(
        analysis, {}, disparity_analysis=disparity_analysis,
        output_path=tmp_path / "report.pdf",
        report_options={"sections": {"benchmarks": False, "top_holdings": False}},
    )

    # doc.build() drains/mutates the flowables list it's given, so capture a snapshot of
    # exactly what generate() hands it rather than inspecting report.elements afterwards.
    captured: list = []
    original_build = report.doc.build

    def capture_and_build(flowables, **kwargs):
        captured.extend(flowables)
        return original_build(flowables, **kwargs)

    report.doc.build = capture_and_build
    report.generate()

    assert captured
    assert not isinstance(captured[-1], PageBreak)
    for previous, current in zip(captured, captured[1:]):
        assert not (isinstance(previous, PageBreak) and isinstance(current, PageBreak))
