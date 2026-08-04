import os
import matplotlib.pyplot as plt
import numpy as np


# =====================================
# OUTPUT DIRECTORY
# =====================================

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/tmp/portfolio-output" if os.getenv("VERCEL") else "output")

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# =====================================
# GLOBAL STYLE
# =====================================

plt.style.use("ggplot")

TITLE_SIZE = 18
LABEL_SIZE = 13
TICK_SIZE = 11
LEGEND_SIZE = 11
PCT_SIZE = 11
VALUE_SIZE = 11


# =====================================
# DONUT LABELS
# =====================================

def add_donut_labels(
    ax,
    wedges,
    values
):

    total = sum(values)

    small_slice_index = 0


    for wedge, value in zip(
        wedges,
        values
    ):

        if value <= 0:

            continue


        percentage = (
            value
            / total
            * 100
        )


        angle = (
            wedge.theta1
            + wedge.theta2
        ) / 2


        if percentage < 3:

            radius = (
                0.68
                if small_slice_index % 2 == 0
                else 0.86
            )

            rotation = angle

            if 90 < rotation < 270:

                rotation += 180

            font_size = 8

            small_slice_index += 1


        else:

            radius = 0.76

            rotation = 0

            font_size = 10


        x = radius * np.cos(
            np.deg2rad(angle)
        )

        y = radius * np.sin(
            np.deg2rad(angle)
        )


        red, green, blue, alpha = wedge.get_facecolor()

        brightness = (
            0.2126 * red
            + 0.7152 * green
            + 0.0722 * blue
        )

        text_color = (
            "white"
            if brightness < 0.48
            else "black"
        )


        ax.text(
            x,
            y,
            f"{percentage:.1f}%",
            ha="center",
            va="center",
            fontsize=font_size,
            fontweight="bold",
            color=text_color,
            rotation=rotation,
            rotation_mode="anchor"
        )


# =====================================
# DONUT CHART
# =====================================

def create_donut_chart(
    df,
    label_column,
    value_column,
    title,
    filename,
    center_text
):
    fig, ax = plt.subplots(figsize=(11, 8))

    labels = df[label_column].astype(str).tolist()
    values = df[value_column].tolist()

    wedges, texts = ax.pie(
        values,
        labels=None,
        startangle=90,
        wedgeprops=dict(
            width=0.48,
            edgecolor="white",
            linewidth=2
        )
    )

    add_donut_labels(
        ax,
        wedges,
        values
    )

    ax.set_title(
        title,
        fontsize=TITLE_SIZE,
        fontweight="bold",
        pad=20
    )

    ax.text(
        0,
        0,
        center_text,
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color="#0F172A"
    )

    ax.legend(
        wedges,
        labels,
        title="Category",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=LEGEND_SIZE,
        title_fontsize=12,
        frameon=True
    )

    ax.set_aspect("equal")

    plt.tight_layout()

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(f"Saved : {path}")


# =====================================
# HORIZONTAL BAR CHART
# =====================================

def create_bar_chart(
    df,
    x_column,
    y_column,
    title,
    xlabel,
    filename
):
    fig, ax = plt.subplots(figsize=(13, 8))

    labels = df[x_column].astype(str).tolist()
    values = df[y_column].tolist()

    bars = ax.barh(
        labels,
        values,
        color="#0B5CAD"
    )

    ax.set_xlabel(
        xlabel,
        fontsize=LABEL_SIZE,
        fontweight="bold"
    )

    ax.set_title(
        title,
        fontsize=TITLE_SIZE,
        fontweight="bold",
        pad=18
    )

    ax.tick_params(axis="x", labelsize=TICK_SIZE)
    ax.tick_params(axis="y", labelsize=TICK_SIZE)

    ax.invert_yaxis()

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{width:.2f}%",
            va="center",
            fontsize=VALUE_SIZE,
            fontweight="bold",
            color="black"
        )

    plt.tight_layout()

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(f"Saved : {path}")


# =====================================
# GENERATE ALL CHARTS
# =====================================

def generate_all_charts(analysis):

    sector = analysis["sector"]
    industry = analysis["industry"]
    market_cap = analysis["market_cap"]
    top10 = analysis["top10"]

    # -----------------------------
    # Sector Donut
    # -----------------------------
    create_donut_chart(
        sector,
        "sector",
        "allocation_percent",
        "Sector Allocation",
        "sector_donut.png",
        "Client Portfolio\nSectors"
    )

    # -----------------------------
    # Industry Donut
    # -----------------------------
    create_donut_chart(
        industry,
        "industry",
        "allocation_percent",
        "Industry Allocation",
        "industry_donut.png",
        "Client Portfolio\nIndustries"
    )

    # -----------------------------
    # Market Cap Donut
    # -----------------------------
    create_donut_chart(
        market_cap,
        "cap_category",
        "allocation_percent",
        "Market Cap Allocation",
        "market_cap_donut.png",
        "Client Portfolio\nMarket Cap"
    )

    # -----------------------------
    # Top Holdings
    # -----------------------------
    create_bar_chart(
        top10,
        "security_name",
        "weight_percent",
        "Top Holdings",
        "Weight (%)",
        "top_holdings.png"
    )

    # -----------------------------
    # Sector Allocation
    # -----------------------------
    create_bar_chart(
        sector,
        "sector",
        "allocation_percent",
        "Sector Allocation",
        "Allocation (%)",
        "sector_bar.png"
    )

    # -----------------------------
    # Market Cap Allocation
    # -----------------------------
    create_bar_chart(
        market_cap,
        "cap_category",
        "allocation_percent",
        "Market Cap Allocation",
        "Allocation (%)",
        "market_cap_bar.png"
    )

    print("\n========== CHARTS GENERATED ==========\n")

    return {
        "sector_donut": os.path.join(OUTPUT_DIR, "sector_donut.png"),
        "industry_donut": os.path.join(OUTPUT_DIR, "industry_donut.png"),
        "market_cap_donut": os.path.join(OUTPUT_DIR, "market_cap_donut.png"),
        "top_holdings": os.path.join(OUTPUT_DIR, "top_holdings.png"),
        "sector_bar": os.path.join(OUTPUT_DIR, "sector_bar.png"),
        "market_cap_bar": os.path.join(OUTPUT_DIR, "market_cap_bar.png")
    }
