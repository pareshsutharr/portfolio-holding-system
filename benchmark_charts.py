
import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


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


# =====================================
# DONUT LABELS
# =====================================

def add_donut_labels(
    ax,
    wedges,
    values,
    regular_size=10,
    small_size=8
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
                0.67
                if small_slice_index % 2 == 0
                else 0.86
            )

            rotation = angle

            if 90 < rotation < 270:

                rotation += 180

            font_size = small_size

            small_slice_index += 1


        else:

            radius = 0.76

            rotation = 0

            font_size = regular_size


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
# BENCHMARK DONUT CHART
# =====================================

def create_benchmark_donut(
    benchmark,
    benchmark_name,
    filename
):

    fig, ax = plt.subplots(figsize=(11,8))

    labels = benchmark["sector"].tolist()

    values = benchmark["benchmark_weight"].tolist()

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

    ax.legend(

        wedges,

        labels,

        title="Sector",

        loc="center left",

        bbox_to_anchor=(1.02,0.5),

        fontsize=LEGEND_SIZE

    )

    ax.set_title(

        f"{benchmark_name} Sector Allocation",

        fontsize=TITLE_SIZE,

        fontweight="bold"

    )

    ax.text(
        0,
        0,
        f"{benchmark_name}\nSectors",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color="#0F172A"
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
# SIDE BY SIDE DONUT COMPARISON
# =====================================

def create_donut_comparison(
    comparison,
    benchmark_name,
    filename
):

    comparison = comparison.copy()

    comparison["maximum_weight"] = comparison[
        [
            "client_weight",
            "benchmark_weight"
        ]
    ].max(axis=1)

    comparison = comparison.sort_values(
        by="maximum_weight",
        ascending=False
    )


    labels = comparison["sector"].astype(str).tolist()

    client_values = comparison["client_weight"].tolist()

    benchmark_values = comparison["benchmark_weight"].tolist()

    chart_colors = plt.cm.tab20(
        np.linspace(
            0,
            1,
            len(labels)
        )
    )


    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14, 8.5)
    )


    chart_data = [
        (
            client_values,
            "Client Portfolio",
            "Client Portfolio\nSectors"
        ),
        (
            benchmark_values,
            benchmark_name,
            f"{benchmark_name}\nSectors"
        )
    ]


    for ax, data in zip(axes, chart_data):

        values, title, center_text = data

        wedges, texts = ax.pie(
            values,
            labels=None,
            colors=chart_colors,
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
            values,
            regular_size=11,
            small_size=8.5
        )

        ax.text(
            0,
            0,
            center_text,
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="#0F172A"
        )

        ax.set_title(
            title,
            fontsize=TITLE_SIZE,
            fontweight="bold",
            pad=15
        )

        ax.set_aspect("equal")


    legend_handles = [
        Patch(
            facecolor=color,
            edgecolor="white",
            label=label
        )
        for label, color in zip(
            labels,
            chart_colors
        )
    ]


    fig.legend(
        handles=legend_handles,
        title="Sector",
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=3,
        fontsize=9.5,
        title_fontsize=11,
        frameon=False
    )


    fig.suptitle(
        "Sector Allocation Comparison",
        fontsize=20,
        fontweight="bold"
    )


    plt.subplots_adjust(
        left=0.03,
        right=0.97,
        top=0.84,
        bottom=0.27,
        wspace=0.08
    )


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
# BENCHMARK VS CLIENT
# =====================================

def create_comparison_chart(
    comparison,
    benchmark_name,
    filename
):

    comparison = comparison.sort_values(

        by="benchmark_weight",

        ascending=True

    )

    fig, ax = plt.subplots(figsize=(13,8))

    y = np.arange(len(comparison))

    width = 0.38

    benchmark_bars = ax.barh(

        y - width/2,

        comparison["benchmark_weight"],

        height=width,

        label=benchmark_name

    )

    client_bars = ax.barh(

        y + width/2,

        comparison["client_weight"],

        height=width,

        label="Client Portfolio"

    )

    ax.bar_label(
        benchmark_bars,
        labels=[f"{value:.1f}%" if value > 0 else "" for value in comparison["benchmark_weight"]],
        padding=3,
        fontsize=8,
        fontweight="bold",
    )

    ax.bar_label(
        client_bars,
        labels=[f"{value:.1f}%" if value > 0 else "" for value in comparison["client_weight"]],
        padding=3,
        fontsize=8,
        fontweight="bold",
    )

    maximum = max(float(comparison["benchmark_weight"].max()), float(comparison["client_weight"].max()), 1.0)
    ax.set_xlim(0, maximum * 1.18)

    ax.set_yticks(y)

    ax.set_yticklabels(

        comparison["sector"],

        fontsize=TICK_SIZE

    )

    ax.set_xlabel(

        "Allocation (%)",

        fontsize=LABEL_SIZE,

        fontweight="bold"

    )

    ax.set_title(

        "Benchmark vs Client Sector Allocation",

        fontsize=TITLE_SIZE,

        fontweight="bold"

    )

    ax.legend()

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
# GENERATE BENCHMARK CHARTS
# =====================================

def generate_benchmark_charts(
    analysis
):

    chart_paths = {}


    for benchmark_key, benchmark_data in analysis["benchmarks"].items():

        benchmark = benchmark_data["sector"]

        benchmark_name = benchmark_data["name"]

        comparison = benchmark_data["comparison"]


        donut_comparison_file = (
            f"{benchmark_key}_sector_donut_comparison.png"
        )

        benchmark_donut_file = (
            f"{benchmark_key}_sector_donut.png"
        )

        comparison_file = (
            f"{benchmark_key}_vs_client.png"
        )


        create_donut_comparison(

            comparison,

            benchmark_name,

            donut_comparison_file

        )


        create_benchmark_donut(

            benchmark,

            benchmark_name,

            benchmark_donut_file

        )


        create_comparison_chart(

            comparison,

            benchmark_name,

            comparison_file

        )


        chart_paths[
            f"{benchmark_key}_sector_donut_comparison"
        ] = os.path.join(
            OUTPUT_DIR,
            donut_comparison_file
        )

        chart_paths[
            f"{benchmark_key}_donut"
        ] = os.path.join(
            OUTPUT_DIR,
            benchmark_donut_file
        )

        chart_paths[
            f"{benchmark_key}_vs_client"
        ] = os.path.join(
            OUTPUT_DIR,
            comparison_file
        )

    print("\n========== BENCHMARK CHARTS GENERATED ==========\n")

    return chart_paths
