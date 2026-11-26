"""Render vector paper figures at the svjour3 smallextended text width (12.2 cm)."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

from paper_numbers import ROOT, load_results, outcome

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/paper-matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

WIDTH = 12.2 / 2.54
COLORS = {"preserved": "#56B4E9", "loud": "#E69F00", "loud-partial": "#CC79A7",
          "silent-loss": "#D55E00", "unsupported": "#EEEEEE"}
MARKS = {"preserved": "", "loud": "/", "loud-partial": "x", "silent-loss": "", "unsupported": ""}
ALIASES = {"remove_column": "drop_column", "remove_foreign_key": "drop_foreign_key",
           "remove_index": "drop_index", "remove_check_constraint": "drop_check_constraint"}
GROUPS = (
    ("Columns", (("add_column", "Add column"), ("drop_column", "Drop column"),
                 ("rename_column", "Rename column"), ("change_type", "Change type"),
                 ("add_reference", "Add reference"), ("add_timestamps", "Add timestamps"))),
    ("Properties", (("set_not_null", "Set NOT NULL"), ("drop_not_null", "Drop NOT NULL"),
                    ("set_default", "Set default"), ("change_default", "Change default"),
                    ("drop_default", "Drop default"))),
    ("Constraints", (("add_foreign_key", "Add foreign key"), ("drop_foreign_key", "Drop foreign key"),
                     ("add_unique", "Add unique"), ("drop_unique", "Drop unique"),
                     ("add_check_constraint", "Add check"), ("drop_check_constraint", "Drop check"))),
    ("Indexes / tables", (("add_index", "Add index"), ("drop_index", "Drop index"),
                         ("rename_table", "Rename table"))),
)
PANELS = (
    ("Rails", "rails", "current", "rails", "default"),
    ("Drizzle", "drizzle", "current", "drizzle", "default"),
    ("Django", "django", "django-current", "django", "default"),
    ("Alembic (auto)", "alembic", "alembic", "auto", "auto"),
    ("Prisma 7.10.0", "prisma", "prisma-stable", "prisma", "default"),
)


def panel_cells(data, panel):
    _, fw, pin, path, mode = panel
    rows = data["operation_matrix"]["rows"] + data["orm_matrix"]["rows"]
    selected = [r for r in rows if (r["framework"], r["version_label"], r["path"],
                r.get("mode", "default")) == (fw, pin, path, mode)]
    cells = {}
    for row in selected:
        key = ALIASES.get(row["operation"], row["operation"]), row["context"]
        if key in cells:
            raise ValueError(f"Duplicate figure cell: {panel}, {key}")
        cells[key] = outcome(row)
    union = {op for _, ops in GROUPS for op, _ in ops}
    if {op for op, _ in cells} - union:
        raise ValueError("Operation missing from figure union")
    return cells


def save(fig, path):
    # Fixed dimensions preserve the stated font size at \includegraphics[width=\linewidth].
    fig.savefig(path, format="pdf", metadata={"Creator": None, "Producer": None,
                "CreationDate": None, "ModDate": None})
    plt.close(fig)


def heatmap(data, output):
    fig = plt.figure(figsize=(WIDTH, 7.00))
    positions, group_positions = {}, []
    row = 0
    for group, operations in GROUPS:
        group_positions.append((row, group))
        row += 1
        for op, label in operations:
            positions[op] = (row, label)
            row += 1
    manifest = []
    for index, panel in enumerate(PANELS):
        tier, col = divmod(index, 3)
        ax = fig.add_axes([0.243 + col * 0.252, 0.540 - tier * 0.455, 0.240, 0.411])
        ax.set_xlim(-0.5, 8.5)
        ax.set_ylim(row - 0.5, -0.5)
        cells = panel_cells(data, panel)
        count = Counter()
        for op, (y, label) in positions.items():
            for x in range(9):
                status = cells.get((op, f"C{x}"), "unsupported")
                count[status] += 1
                ax.add_patch(Rectangle((x - 0.48, y - 0.48), 0.96, 0.96,
                             facecolor=COLORS[status], edgecolor="white", linewidth=0.3,
                             hatch=MARKS[status]))
                if status == "unsupported":
                    ax.text(x, y, "-", ha="center", va="center", fontsize=8, color="#666666")
        ax.set_xticks(range(9), [f"C{x}" for x in range(9)], fontsize=8, rotation=90)
        ax.xaxis.tick_top()
        ax.tick_params(axis="both", length=0, pad=2)
        ax.set_yticks([])
        if col == 0:
            for y, label in positions.values():
                ax.text(-0.085, y, label, transform=ax.get_yaxis_transform(),
                        ha="right", va="center", fontsize=8)
            for y, label in group_positions:
                ax.text(-0.085, y, label, transform=ax.get_yaxis_transform(),
                        ha="right", va="center", fontsize=8, fontweight="bold")
        for y, _ in group_positions:
            ax.axhline(y + 0.5, color="#777777", linewidth=0.35)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.text(0.5, 1.075, panel[0], transform=ax.transAxes, ha="center", fontsize=8, fontweight="bold")
        manifest.append(dict(label=panel[0], framework=panel[1], pin=panel[2], path=panel[3],
                             mode=panel[4], outcomes=dict(sorted(count.items()))))
    handles = [Patch(facecolor=COLORS[s], hatch=MARKS[s], label=s.capitalize(), edgecolor="#666666", linewidth=0.3)
               for s in COLORS]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=3,
               frameon=False, fontsize=8, handlelength=1.3, columnspacing=1.1)
    save(fig, output / "Fig1.pdf")
    return manifest


def fix_bars(data, output):
    rows = data["operation_matrix"]["rows"] + data["rails_fixes"]["rows"]
    pins = {
        "rails": ("before", "current", "rails-pr57128", "rails-pr56811", "rails-pr58709",
                  "rails-pr57128+56811", "rails-pr58709+56811"),
        "drizzle": ("before", "current", "drizzle-pr5784", "drizzle-pr5074", "drizzle-pr5784+5074"),
    }
    fig = plt.figure(figsize=(WIDTH, 3.90))
    manifest = []
    for fw, bounds in (("rails", [0.25, 0.56, 0.71, 0.37]), ("drizzle", [0.25, 0.165, 0.71, 0.27])):
        ax = fig.add_axes(bounds)
        counts, failures = [], []
        for pin in pins[fw]:
            selected = [r for r in rows if (r["framework"], r["version_label"], r["path"]) == (fw, pin, fw)]
            if not selected:
                raise ValueError(f"Missing fix pin: {fw}/{pin}")
            counts.append(sum(outcome(r) == "silent-loss" for r in selected))
            atomic = [r for r in data["rails_atomicity"]["rows"] if fw == "rails" and
                      r["version_label"] == pin and r["scenario"]["transactional"]]
            failures.append(sum(r["assessment"]["classification"] != "fully rolled back" for r in atomic))
            manifest.append(dict(framework=fw, pin=pin, cells=len(selected), silent_loss=counts[-1],
                                 atomicity_tested=len(atomic), atomicity_failures=failures[-1] if atomic else None))
        ax.barh(range(len(counts)), counts, height=0.65, color=COLORS["silent-loss"])
        for y, (value, failure) in enumerate(zip(counts, failures)):
            ax.text(value + 0.7, y, str(value), va="center", fontsize=8)
            if failure:
                ax.plot(value + 8, y, marker="x", color="#222222", markersize=5, markeredgewidth=1.2)
                ax.text(value + 10, y, f"{failure}/4", va="center", fontsize=8)
        labels = [pin.removeprefix(fw + "-pr").replace("+", " + ") for pin in pins[fw]]
        ax.set_yticks(range(len(counts)), labels, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, 61)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
        ax.tick_params(labelsize=8, length=2)
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#DDDDDD", linewidth=0.4)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#AAAAAA")
        ax.text(0, 1.06, fw.capitalize(), transform=ax.transAxes, fontsize=8, fontweight="bold")
        if fw == "drizzle":
            ax.set_xlabel("Silent-loss cells (framework path)", fontsize=8, labelpad=3)
    fig.legend(handles=[Line2D([], [], color="#222222", marker="x", linestyle="none",
                    label="Atomicity failures / transactional probes")],
               loc="lower center", bbox_to_anchor=(0.5, 0.005), frameon=False, fontsize=8)
    save(fig, output / "Fig2.pdf")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "paper/figures")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "pdf.fonttype": 42,
                         "hatch.linewidth": 0.35, "axes.unicode_minus": False})
    data = load_results()
    manifest = {"width_inches": WIDTH, "minimum_font_pt": 8,
                "sources": ["results/operation_matrix.json", "results/rails_fixes.json",
                            "results/orm_matrix.json", "results/rails_atomicity.json"],
                "operation_aliases": ALIASES,
                "grid": heatmap(data, args.output), "fixes": fix_bars(data, args.output),
                "notes": ["Grid uses populated outcomes and native framework paths; Alembic uses auto mode.",
                          "Absent operations in the union are unsupported by the retained matrix, not assertions about all framework capabilities.",
                          "Five panels in a 3+2 layout; Prisma 7.10.0 is the executable stable pin. The unsupported latest tag is omitted.",
                          "Bar annotations mark partial commits only in transactional probes; unmarked pins may be untested (see atomicity_tested).",
                          "Numeric fix labels are PR numbers; combined labels denote retained local merge pins."]}
    manifest["source_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                 for name in manifest["sources"]}
    manifest["matplotlib_version"] = matplotlib.__version__
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote vector figures to {args.output}")


if __name__ == "__main__":
    main()
