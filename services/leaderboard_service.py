from __future__ import annotations

from database.repositories import UserRepository

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


async def format_leaderboard(user_repo: UserRepository, limit: int) -> str:
    rows = await user_repo.get_leaderboard(limit)
    if not rows:
        return "Hozircha ishtirokchilar yo'q."

    lines: list[str] = []
    for i, row in enumerate(rows, start=1):
        prefix = MEDALS.get(i, f"{i}.")
        lines.append(f"{prefix} {row['full_name']} — {row['points']} ball")
    return "\n".join(lines)


async def format_user_stats(user_repo: UserRepository, user_id: int) -> str:
    stats = await user_repo.get_user_stats(user_id)
    if not stats or not stats.get("registered"):
        return "Siz hali ro'yxatdan o'tmagansiz. /start bosing."

    points = stats.get("points", 0)
    refs = stats.get("referral_count", 0)
    rank = stats.get("rank")
    rank_text = f"{rank}-o'rin" if rank else "reytingda yo'q"

    return (
        f"⭐️ Ballaringiz: {points}\n"
        f"👥 Takliflaringiz: {refs}\n"
        f"🏆 Reytingdagi o'rningiz: {rank_text}"
    )
