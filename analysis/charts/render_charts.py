"""Render the 7 report figures from chart_data.json (which only exists if
every reconciliation check passed). PNG at 300 DPI + true-vector SVG (text
kept as text via svg.fonttype='none').

Style: white background, engine colors extracted from the website's
comparison page (ENGINE_META), Helvetica Neue (site's 'General Sans' is not
installed locally; the site's own fallback chain is system sans), text/axes
in the brand ink #141414, no heavy gridlines, value labels everywhere,
titles baked in, figure numbers/captions NOT baked in.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import Patch

OUT = Path(__file__).resolve().parent
PNG = OUT / "png"
SVG = OUT / "svg"
PNG.mkdir(exist_ok=True)
SVG.mkdir(exist_ok=True)

D = json.loads((OUT / "chart_data.json").read_text())
PAL = D["palette"]
NAME = D["display"]
ENGINES = ["quissly", "doofinder", "clerk", "luigisbox", "algolia"]
TIERS = ["simple", "medium", "complex"]
INK = "#141414"
WARN = "#7c2d12"      # all-junk tone (distinct from every engine color)
NONE_GRAY = "#d4d4d8"  # no-results
FONT = "Helvetica Neue"

plt.rcParams.update({
    "font.family": FONT, "text.color": INK, "axes.edgecolor": INK,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "svg.fonttype": "none", "figure.facecolor": "white",
    "axes.facecolor": "white", "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
})


def save(fig, stem):
    fig.savefig(PNG / f"{stem}.png", dpi=300, facecolor="white")
    fig.savefig(SVG / f"{stem}.svg", facecolor="white")
    plt.close(fig)
    print(f"rendered {stem}")


def tint(hex_color, amount):
    """Mix toward white (amount 0..1)."""
    r, g, b = to_rgb(hex_color)
    return (r + (1 - r) * amount, g + (1 - g) * amount,
            b + (1 - b) * amount)


# ── C1: EZR grouped bars ─────────────────────────────────────────────────────
def c1():
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    order = sorted(ENGINES, key=lambda e: D["ezr_pooled"][e])
    series = ["Pooled", "Simple", "Medium", "Complex"]
    tints = [0.0, 0.45, 0.62, 0.78]
    w = 0.2
    for j, s in enumerate(series):
        for i, e in enumerate(order):
            v = (D["ezr_pooled"][e] if s == "Pooled"
                 else D["ezr_tier"][e][TIERS.index(s.lower())])
            x = i + (j - 1.5) * w
            ax.bar(x, v, w * 0.92, color=tint(PAL[e], tints[j]),
                   edgecolor="white", linewidth=0.4)
            bold = (s == "Complex" and e == "algolia") or \
                   (s == "Pooled" and e == "quissly")
            ax.text(x, v + 1.2, f"{v:.1f}", ha="center", va="bottom",
                    fontsize=8, fontweight="bold" if bold else "normal")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([NAME[e] for e in order], fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of queries returning nothing useful", fontsize=9.5)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="y", color="#eeeeee", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    # annotations
    ax.annotate("96.5% of complex queries\nreturn nothing useful",
                xy=(4 + 1.5 * w, 96.5), xytext=(3.1, 84),
                fontsize=8.5, fontweight="bold", ha="right",
                arrowprops=dict(arrowstyle="-", color=INK, linewidth=0.7))
    ax.annotate("lowest pooled rate: 7.4%",
                xy=(0 - 1.5 * w, 7.4), xytext=(-0.28, 26),
                fontsize=8.5, fontweight="bold", ha="left",
                arrowprops=dict(arrowstyle="-", color=INK, linewidth=0.7))
    ax.legend(handles=[Patch(facecolor=tint("#6b7280", t), label=s)
                       for s, t in zip(series, tints)],
              loc="upper left", bbox_to_anchor=(0.11, 1.0), frameon=False,
              fontsize=8.5, ncol=4, handlelength=1.1, columnspacing=1.0)
    ax.set_title("Effective zero-result rate: how often the shopper gets "
                 "nothing useful", fontsize=12, fontweight="bold",
                 loc="left", pad=26)
    ax.text(0, 1.055, "1,259 queries per engine, July 2026",
            transform=ax.transAxes, fontsize=9, color="#555555")
    fig.tight_layout()
    save(fig, "C1_ezr")


# ── C2: outcome composition, 3 stacked panels ───────────────────────────────
def c2():
    fig, axes = plt.subplots(3, 1, figsize=(6.5, 7.5), sharex=True,
                             gridspec_kw={"hspace": 0.42})
    ns = D["tier_n"]
    for pi, (t, ax) in enumerate(zip(TIERS, axes)):
        ypos = range(len(ENGINES) - 1, -1, -1)
        for y, e in zip(ypos, ENGINES):
            zero = D["zero_tier"][e][pi]
            junk = D["alljunk_tier"][e][pi]
            useful = 100 - zero - junk
            ax.barh(y, useful, 0.62, color=PAL[e], edgecolor="white",
                    linewidth=0.4)
            ax.barh(y, junk, 0.62, left=useful, color=WARN,
                    edgecolor="white", linewidth=0.4)
            ax.barh(y, zero, 0.62, left=useful + junk, color=NONE_GRAY,
                    edgecolor="white", linewidth=0.4)
            for val, start, seg_color in ((useful, 0, PAL[e]),
                                          (junk, useful, WARN),
                                          (zero, useful + junk, NONE_GRAY)):
                if val >= 4.0:   # smaller segments unlabeled (8pt rule)
                    lum = sum(c * f for c, f in zip(to_rgb(seg_color),
                                                    (.299, .587, .114)))
                    ax.text(start + val / 2, y, f"{val:.1f}", ha="center",
                            va="center", fontsize=8,
                            color="white" if lum < 0.55 else INK)
        ax.set_yticks(list(ypos))
        ax.set_yticklabels([NAME[e] for e in ENGINES], fontsize=9.5)
        ax.set_xlim(0, 100)
        ax.set_title(f"{t.capitalize()} (n={ns[t]})", loc="left",
                     fontsize=10.5, fontweight="bold", pad=6)
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        if pi < 2:
            ax.tick_params(axis="x", length=0)
            ax.spines["bottom"].set_visible(False)
    axes[2].xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    axes[2].text(0, -1.5, "Algolia answered 13 of 315 complex queries.",
                 fontsize=7.5, color="#555555")
    fig.legend(handles=[Patch(facecolor="#6b7280", label="Useful results"),
                        Patch(facecolor=WARN, label="All results junk"),
                        Patch(facecolor=NONE_GRAY, label="No results")],
               loc="upper center", bbox_to_anchor=(0.55, 0.965),
               frameon=False, fontsize=9, ncol=3)
    fig.suptitle("Outcome of every query: useful, all-junk, or nothing",
                 x=0.02, y=0.985, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.015, 1, 0.93))
    save(fig, "C2_outcomes")


# ── C3 / C4: grouped bars by tier ───────────────────────────────────────────
def tier_grouped(stem, values, ns, ylim, ylabel, title, pct, annos):
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    w = 0.16
    for j, e in enumerate(ENGINES):
        for i in range(3):
            v = values[e][i]
            x = i + (j - 2) * w
            ax.bar(x, v, w * 0.9, color=PAL[e], edgecolor="white",
                   linewidth=0.4,
                   label=NAME[e] if i == 0 else None)
            ax.text(x, v + ylim * 0.012, f"{v:.1f}", ha="center",
                    va="bottom", fontsize=8,
                    fontweight="bold" if (e, i) in annos else "normal")
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"{t.capitalize()} (n={n})"
                        for t, n in zip(TIERS, ns)], fontsize=10)
    ax.set_ylim(0, ylim)
    ax.set_ylabel(ylabel, fontsize=9.5)
    if pct:
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="y", color="#eeeeee", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for (e, i), txt in annos.items():
        x = i + (ENGINES.index(e) - 2) * w
        v = values[e][i]
        # keep the callout text inside the axes so it can't hit the legend
        ty = min(v + ylim * 0.16, ylim * 0.90)
        tx = x + (0.30 if ty <= v + ylim * 0.02 else 0.18)
        ax.annotate(txt, xy=(x, v), xytext=(tx, ty),
                    fontsize=8.5, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=INK,
                                    linewidth=0.7))
    ax.legend(loc="upper right", frameon=False, fontsize=8.5, ncol=5,
              handlelength=1.0, columnspacing=0.9,
              bbox_to_anchor=(1.0, 1.09))
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=22)
    fig.tight_layout()
    save(fig, stem)


# ── C5: forest plot ─────────────────────────────────────────────────────────
def c5():
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    groups = [("Effective zero-result rate", "ezr"),
              ("nDCG@10", "ndcg"), ("Recall@20", "recall")]
    rivals = ["doofinder", "clerk", "luigisbox", "algolia"]
    rows = []          # (y, label, adv, lo, hi, color) top-down
    y = 0
    header_ys = []
    for gname, gkey in groups:
        header_ys.append((y, gname))
        y -= 1
        for v in rivals:
            d = D["forest"][gkey][v]
            rows.append((y, NAME[v], d["adv"], d["lo"], d["hi"], PAL[v]))
            y -= 1
        y -= 0.6
    for ry, label, adv, lo, hi, color in rows:
        ax.plot([lo, hi], [ry, ry], color=color, linewidth=1.6,
                solid_capstyle="butt")
        ax.plot([lo, lo], [ry - 0.14, ry + 0.14], color=color, linewidth=1.4)
        ax.plot([hi, hi], [ry - 0.14, ry + 0.14], color=color, linewidth=1.4)
        ax.plot(adv, ry, "o", color=color, markersize=6)
        ax.text(hi + 0.9, ry, f"+{adv:.1f}", va="center", fontsize=8.5,
                fontweight="bold")
        ax.text(-2.2, ry, label, va="center", ha="right", fontsize=9)
    for hy, gname in header_ys:
        ax.text(-2.2, hy, gname, va="center", ha="right", fontsize=10,
                fontweight="bold")
    ax.axvline(0, color=INK, linewidth=0.9)
    ax.set_xlim(-14, 40)
    ax.set_ylim(y + 0.4, 1.0)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Quissly advantage (pp); right of zero favors Quissly",
                  fontsize=9.5)
    ax.grid(axis="x", color="#eeeeee", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.text(0.0, 1.035, "For EZR (lower is better) the difference is "
            "plotted as rival minus Quissly, so right of zero still favors "
            "Quissly.", transform=ax.transAxes, fontsize=8, color="#555555")
    ax.text(0.0, -0.115,
            "7 sector/tier EZR cells vs Doofinder are within noise (see "
            "report Section 5.1); all pooled comparisons\nshown here are "
            "significant after Holm correction.",
            transform=ax.transAxes, fontsize=8, color="#555555", va="top")
    ax.set_title("How large are the gaps, and how certain",
                 fontsize=12, fontweight="bold", loc="left", pad=30)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "C5_forest")


# ── C6: sector heatmap, two panels ──────────────────────────────────────────
def c6():
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 4.8),
                             gridspec_kw={"wspace": 0.06})
    order = D["heat_sector_order"]
    slab = {"auto": "Auto parts", "cosmetics": "Cosmetics",
            "electronics": "Electronics", "fast_fashion": "Fast fashion",
            "furniture": "Furniture", "marketplace": "Marketplace",
            "pharmacy": "Pharmacy"}
    cmap_ezr = LinearSegmentedColormap.from_list(
        "ezr", ["#d3f0c5", "#f8e0a0", "#e2543e"])   # low good -> high bad
    cmap_ndcg = LinearSegmentedColormap.from_list(
        "ndcg", ["#f5f5ff", "#a5a8f0", "#3b3fa0"])  # low pale -> high deep
    panels = [("Effective zero-result rate", "ezr", cmap_ezr,
               "lower is better", 0, 100),
              ("Pooled-ideal nDCG@10", "ndcg", cmap_ndcg,
               "higher is better", 0, 100)]
    for pi, (ptitle, key, cmap, direction, vmin, vmax) in enumerate(panels):
        ax = axes[pi]
        mat = [[D["heat"][key][s][e] for e in ENGINES] for s in order]
        ax.imshow(mat, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        for r in range(len(order)):
            for c in range(len(ENGINES)):
                v = mat[r][c]
                rgba = cmap((v - vmin) / (vmax - vmin))
                lum = .299 * rgba[0] + .587 * rgba[1] + .114 * rgba[2]
                ax.text(c, r, f"{v:.1f}", ha="center", va="center",
                        fontsize=8, color="white" if lum < 0.55 else INK)
        ax.set_xticks(range(len(ENGINES)))
        ax.set_xticklabels([NAME[e] for e in ENGINES], fontsize=8,
                           rotation=32, ha="right")
        if pi == 0:
            ax.set_yticks(range(len(order)))
            ax.set_yticklabels([slab[s] for s in order], fontsize=9)
        else:
            ax.set_yticks([])
        ax.set_title(f"{ptitle}\n", fontsize=10.5, fontweight="bold",
                     loc="left", pad=2)
        ax.text(0, 1.02, direction, transform=ax.transAxes, fontsize=8.5,
                color="#555555")
        ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
    fig.suptitle("Sector by sector: failure rate and ranking quality",
                 x=0.02, y=0.99, ha="left", fontsize=12, fontweight="bold")
    # tight_layout can't manage these imshow axes (it warns and under-applies
    # the rect), so set the top margin explicitly: axes stop at 0.82, panel
    # titles sit just above that, and the suptitle at 0.99 keeps clear air
    fig.tight_layout()
    fig.subplots_adjust(top=0.82)
    save(fig, "C6_sectors")


# ── C7: audit classes ───────────────────────────────────────────────────────
def c7():
    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    items = [("Partial match exists", D["audit_classes"]["partial"]),
             ("Inconclusive", D["audit_classes"]["inconclusive"]),
             ("Catalog gap", D["audit_classes"]["catalog-gap"]),
             ("Engines missed", D["audit_classes"]["engines-missed"])]
    ys = range(len(items) - 1, -1, -1)
    for y, (label, v) in zip(ys, items):
        ax.barh(y, v, 0.58, color="#64748b")
        ax.text(v + 0.4, y, str(v), va="center", fontsize=9,
                fontweight="bold")
    ax.set_yticks(list(ys))
    ax.set_yticklabels([l for l, _ in items], fontsize=9.5)
    ax.set_xlim(0, 40)
    ax.set_xlabel("queries (of 50 audited)", fontsize=9)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color="#eeeeee", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Why 200 queries had no Exact match anywhere "
                 "(50-query audit)", fontsize=11.5, fontweight="bold",
                 loc="left", pad=10)
    fig.tight_layout()
    save(fig, "C7_audit")


def contact_sheet():
    from PIL import Image
    stems = ["C1_ezr", "C2_outcomes", "C3_ndcg", "C4_recall",
             "C5_forest", "C6_sectors", "C7_audit"]
    thumbs = []
    for s in stems:
        im = Image.open(PNG / f"{s}.png")
        im.thumbnail((900, 900))
        thumbs.append((s, im))
    cols, pad = 3, 30
    cw = max(im.width for _, im in thumbs) + pad
    rh = max(im.height for _, im in thumbs) + pad + 30
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw + pad, rows * rh + pad), "white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)
    for i, (s, im) in enumerate(thumbs):
        x = pad + (i % cols) * cw
        y = pad + (i // cols) * rh
        sheet.paste(im, (x, y + 24))
        draw.text((x, y), s, fill="#141414")
    sheet.save(OUT / "contact_sheet.png")
    print("rendered contact_sheet")


if __name__ == "__main__":
    c1()
    c2()
    tier_grouped("C3_ndcg", D["ndcg_tier"], D["ndcg_tier_n"], 100,
                 "nDCG@10 (points)",
                 "Ranking quality collapses with complexity for "
                 "keyword-tier engines", pct=False,
                 annos={("algolia", 2): "1.16 points"})
    tier_grouped("C4_recall", D["recall_tier"], D["recall_tier_n"], 80,
                 "Recall@20", "Share of all known-relevant products found "
                 "(recall@20)", pct=True,
                 annos={("quissly", 2): "72.4%", ("algolia", 2): "0.5%"})
    c5()
    c6()
    c7()
    contact_sheet()
