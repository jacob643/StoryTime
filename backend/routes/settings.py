from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from backend.settings_manager import GameSettings, get_settings, update_settings

router = APIRouter()


class SettingsResponse(BaseModel):
    scoring_mode: str
    min_data: int
    min_stddev_cpm: float
    tier_0_max_sigma: float
    tier_1_max_sigma: float
    tier_2_max_sigma: float
    tier_3_max_sigma: float
    fixed_thresholds: list[list[float]]
    target_split_size: int
    min_split_size: int
    default_avg_cpm: float
    outcome_directions: dict[int, str]
    provider: str
    custom_endpoint: str
    custom_api_key: str
    custom_model: str


class SettingsPatch(BaseModel):
    scoring_mode: str | None = None
    min_data: int | None = None
    min_stddev_cpm: float | None = None
    tier_0_max_sigma: float | None = None
    tier_1_max_sigma: float | None = None
    tier_2_max_sigma: float | None = None
    tier_3_max_sigma: float | None = None
    fixed_thresholds: list[list[float]] | None = None
    target_split_size: int | None = None
    min_split_size: int | None = None
    default_avg_cpm: float | None = None
    outcome_directions: dict[int, str] | None = None
    provider: str | None = None
    custom_endpoint: str | None = None
    custom_api_key: str | None = None
    custom_model: str | None = None


def _settings_to_response(gs: GameSettings) -> SettingsResponse:
    return SettingsResponse(
        scoring_mode=gs.scoring_mode,
        min_data=gs.min_data,
        min_stddev_cpm=gs.min_stddev_cpm,
        tier_0_max_sigma=gs.tier_0_max_sigma,
        tier_1_max_sigma=gs.tier_1_max_sigma,
        tier_2_max_sigma=gs.tier_2_max_sigma,
        tier_3_max_sigma=gs.tier_3_max_sigma,
        fixed_thresholds=gs.fixed_thresholds,
        target_split_size=gs.target_split_size,
        min_split_size=gs.min_split_size,
        default_avg_cpm=gs.default_avg_cpm,
        outcome_directions=gs.outcome_directions,
        provider=gs.provider,
        custom_endpoint=gs.custom_endpoint,
        custom_api_key=gs.custom_api_key,
        custom_model=gs.custom_model,
    )


@router.get("/api/settings", response_model=SettingsResponse)
async def get_settings_endpoint():
    return _settings_to_response(get_settings())


@router.post("/api/settings", response_model=SettingsResponse)
async def update_settings_endpoint(body: SettingsPatch):
    updated = update_settings(**body.model_dump(exclude_none=True))
    return _settings_to_response(updated)
