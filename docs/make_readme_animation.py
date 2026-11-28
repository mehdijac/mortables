"""
Generate docs/images/generations.gif, the animated chart shown in the README.

    uv run --extra viz python docs/make_readme_animation.py

For each TGH05 generation from 1931 to 2005, it draws the probability of
being alive at each age for a man still alive at 65, with life expectancy
and the annuity value at 65.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

from mortables import get_table, life

OUT = Path(__file__).parent / "images" / "generations.gif"

# Banner colors
BG, GRID, TEXT, MUTED = "#101d35", "#2a3f5a", "#f3faf8", "#b4d6d2"
MINT, CYAN = "#86efce", "#53b9d7"

GENERATIONS = list(range(1931, 2006))
AGES = np.linspace(65, 110, 451)
RATE = 0.02

curves, e65, a65 = {}, {}, {}
for g in GENERATIONS:
    t = get_table("TGH05", generation=g)
    curves[g] = t.tpx(65, AGES - 65)
    e65[g] = t.life_expectancy(65)
    a65[g] = life.annuity(t, 65, RATE)

fig, ax = plt.subplots(figsize=(10, 4.6), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
fig.subplots_adjust(left=0.08, right=0.97, top=0.80, bottom=0.13)

ax.set_xlim(65, 110)
ax.set_ylim(0, 1.02)
ax.set_xticks(range(65, 111, 5))
ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
ax.set_yticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
ax.grid(color=GRID, linewidth=0.8)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color(GRID)
ax.tick_params(colors=MUTED, labelsize=10)
ax.set_xlabel("Âge", color=MUTED, fontsize=11)

fig.text(0.08, 0.92, "Probabilité d'être en vie, pour un homme de 65 ans (TGH05)",
         color=TEXT, fontsize=14, fontweight="bold")
gen_txt = fig.text(0.08, 0.85, "", color=MINT, fontsize=12, fontweight="bold")
stats_txt = fig.text(0.97, 0.85, "", color=MUTED, fontsize=11, ha="right")

trail = [ax.plot([], [], color=CYAN, linewidth=1, alpha=0.18)[0] for _ in GENERATIONS]
(current,) = ax.plot([], [], color=MINT, linewidth=3)
fill = [None]

HOLD = 25  # frames held on the last generation
frames = list(range(len(GENERATIONS))) + [len(GENERATIONS) - 1] * HOLD


def draw(i):
    g = GENERATIONS[i]
    for j, line in enumerate(trail):
        if j < i and (GENERATIONS[j] - 1931) % 5 == 0:
            line.set_data(AGES, curves[GENERATIONS[j]])
    current.set_data(AGES, curves[g])
    if fill[0] is not None:
        fill[0].remove()
    fill[0] = ax.fill_between(AGES, curves[g], color=MINT, alpha=0.08, linewidth=0)
    gen_txt.set_text(f"Génération {g}")
    stats_txt.set_text(
        f"Espérance de vie à 65 ans : {e65[g]:.1f} ans    "
        f"Rente viagère ä65 à 2 % : {a65[g]:.2f}".replace(".", ",")
    )
    return trail + [current, gen_txt, stats_txt]


anim = FuncAnimation(fig, draw, frames=frames, blit=False)
anim.save(OUT, writer=PillowWriter(fps=12))
print(f"→ {OUT} ({OUT.stat().st_size / 1e6:.1f} Mo)")
