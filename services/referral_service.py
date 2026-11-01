from __future__ import annotations

from dataclasses import dataclass
from database.repositories import UserRepository


@dataclass(slots=True)
class RegistrationResult:
    is_new: bool
    points: int
    referrer_id: int | None = None


async def complete_registration(
    user_repo: UserRepository,
    user_id: int,
    full_name: str,
    username: str | None,
    phone: str,
    referrer_id: int | None,
    start_points: int,
    referral_points: int,
) -> RegistrationResult:
    is_new, valid_referrer = await user_repo.register_and_credit_referrer(
        user_id=user_id,
        full_name=full_name,
        username=username,
        phone=phone,
        referrer_id=referrer_id,
        start_points=start_points,
        referral_points=referral_points,
    )
    if not is_new:
        user = await user_repo.get_by_id(user_id)
        pts = user["points"] if user else 0
        return RegistrationResult(is_new=False, points=pts, referrer_id=None)

    return RegistrationResult(is_new=True, points=start_points, referrer_id=valid_referrer)
