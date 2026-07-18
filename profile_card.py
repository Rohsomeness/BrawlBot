"""Generate player profile image cards from Brawl Stars API data."""
from __future__ import annotations

from typing import Any, Optional

from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle


def _safe(value: Any, default: Any = 0) -> Any:
    return default if value is None else value


def generate_profile_card(
    player_info: dict,
    local_stats: Optional[dict] = None,
    display_name: Optional[str] = None,
    output_path: str = "profile_card.png",
) -> str:
    """
    Render a dark-themed profile card and save it to disk.

    Returns the output path.
    """
    local_stats = local_stats or {}
    name = display_name or player_info.get("name", "Unknown")
    tag = player_info.get("tag", "")
    trophies = int(_safe(player_info.get("trophies"), 0))
    highest = int(_safe(player_info.get("highestTrophies"), trophies))
    exp_level = int(_safe(player_info.get("expLevel"), 0))
    team_wins = int(_safe(player_info.get("3vs3Victories"), 0))
    solo_wins = int(_safe(player_info.get("soloVictories"), 0))
    duo_wins = int(_safe(player_info.get("duoVictories"), 0))
    club = player_info.get("club") or {}
    club_name = club.get("name") or "No club"

    brawlers = list(player_info.get("brawlers") or [])
    brawlers_sorted = sorted(
        brawlers,
        key=lambda b: int(_safe(b.get("trophies"), 0)),
        reverse=True,
    )
    top_brawlers = brawlers_sorted[:5]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=140)
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # Outer card
    card = FancyBboxPatch(
        (0.25, 0.25),
        9.5,
        5.5,
        boxstyle="round,pad=0.05,rounding_size=0.25",
        linewidth=2,
        edgecolor="#38bdf8",
        facecolor="#1e293b",
    )
    ax.add_patch(card)

    # Accent bar
    ax.add_patch(Rectangle((0.25, 4.9), 9.5, 0.85, facecolor="#0284c7", edgecolor="none"))

    ax.text(
        0.55,
        5.35,
        name,
        color="white",
        fontsize=22,
        fontweight="bold",
        va="center",
    )
    ax.text(0.55, 5.0, tag, color="#e0f2fe", fontsize=12, va="center")
    ax.text(
        9.45,
        5.35,
        f"LVL {exp_level}",
        color="white",
        fontsize=16,
        fontweight="bold",
        ha="right",
        va="center",
    )

    # Main stats
    stats_block = [
        ("Trophies", f"{trophies:,}"),
        ("Peak", f"{highest:,}"),
        ("3v3 Wins", f"{team_wins:,}"),
        ("Solo Wins", f"{solo_wins:,}"),
        ("Duo Wins", f"{duo_wins:,}"),
        ("Brawlers", f"{len(brawlers)}"),
    ]
    for idx, (label, value) in enumerate(stats_block):
        col = idx % 3
        row = idx // 3
        x = 0.7 + col * 3.1
        y = 4.2 - row * 0.95
        ax.add_patch(
            FancyBboxPatch(
                (x - 0.2, y - 0.35),
                2.8,
                0.75,
                boxstyle="round,pad=0.02,rounding_size=0.12",
                linewidth=1,
                edgecolor="#334155",
                facecolor="#0f172a",
            )
        )
        ax.text(x, y + 0.15, label, color="#94a3b8", fontsize=10, va="center")
        ax.text(x, y - 0.15, value, color="#f8fafc", fontsize=16, fontweight="bold", va="center")

    ax.text(0.55, 2.15, f"Club: {club_name}", color="#cbd5e1", fontsize=11, va="center")

    # Local bot stats
    climbed = int(_safe(local_stats.get("total_trophies_climbed"), 0))
    stars = int(_safe(local_stats.get("total_star_players"), 0))
    wins = int(_safe(local_stats.get("total_wins"), 0))
    defeats = int(_safe(local_stats.get("total_defeats"), 0))
    ax.text(
        0.55,
        1.75,
        f"Tracked: +{climbed} trophies | {stars} stars | {wins}W-{defeats}L",
        color="#7dd3fc",
        fontsize=10,
        va="center",
    )

    # Top brawlers
    ax.text(0.55, 1.35, "Top brawlers", color="#e2e8f0", fontsize=12, fontweight="bold")
    if top_brawlers:
        max_trophies = max(int(_safe(b.get("trophies"), 0)) for b in top_brawlers) or 1
        for i, brawler in enumerate(top_brawlers):
            y = 1.05 - i * 0.18
            bname = str(brawler.get("name") or "?")
            btrophies = int(_safe(brawler.get("trophies"), 0))
            power = int(_safe(brawler.get("power"), 0))
            bar_width = 4.5 * (btrophies / max_trophies)
            ax.add_patch(Rectangle((3.6, y - 0.05), bar_width, 0.12, facecolor="#38bdf8", edgecolor="none"))
            ax.text(0.55, y, f"{bname} (P{power})", color="#cbd5e1", fontsize=9, va="center")
            ax.text(8.3, y, f"{btrophies}", color="#f8fafc", fontsize=9, va="center", ha="right")
    else:
        ax.text(0.55, 1.0, "No brawler data", color="#94a3b8", fontsize=10)

    ax.text(
        9.45,
        0.4,
        "BrawlBot",
        color="#64748b",
        fontsize=9,
        ha="right",
        va="center",
    )

    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output_path
