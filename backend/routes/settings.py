from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from backend.prompt_engine import _normalize_directions
from backend.game_logic import compute_tier_boundaries
from backend.settings_manager import GameSettings, get_settings, reset_settings, update_settings, build_scoring_params
from backend.logger import logger

router = APIRouter()


class SettingsResponse(BaseModel):
    scoring_mode: str
    min_stddev_cpm: float
    tier_0_max_sigma: float
    tier_1_max_sigma: float
    tier_2_max_sigma: float
    tier_3_max_sigma: float
    fixed_thresholds: list[float]
    paragraph_word_count: int
    target_split_size: int
    min_split_size: int
    outcome_directions: dict[int, list[str]]
    temperature: float
    top_k: int
    top_p: float
    provider: str
    custom_endpoint: str
    custom_api_key: str
    custom_model: str
    ollama_model: str
    ignore_case: bool


class SettingsPatch(BaseModel):
    scoring_mode: str | None = None
    min_stddev_cpm: float | None = None
    tier_0_max_sigma: float | None = None
    tier_1_max_sigma: float | None = None
    tier_2_max_sigma: float | None = None
    tier_3_max_sigma: float | None = None
    fixed_thresholds: list[float] | None = None
    paragraph_word_count: int | None = None
    target_split_size: int | None = None
    min_split_size: int | None = None
    outcome_directions: dict[int, list[str]] | None = None
    temperature: float | None = None
    top_k: int | None = None
    top_p: float | None = None
    provider: str | None = None
    custom_endpoint: str | None = None
    custom_api_key: str | None = None
    custom_model: str | None = None
    ollama_model: str | None = None
    ignore_case: bool | None = None


def _clamp_thresholds(
    thresholds: list[float],
    min_val: float = 0,
    max_val: float = 9999,
) -> list[float]:
    return [max(min_val, min(v, max_val)) for v in thresholds]


def _settings_to_response(gs: GameSettings) -> SettingsResponse:
    return SettingsResponse(
        scoring_mode=gs.scoring_mode,
        min_stddev_cpm=gs.min_stddev_cpm,
        tier_0_max_sigma=gs.tier_0_max_sigma,
        tier_1_max_sigma=gs.tier_1_max_sigma,
        tier_2_max_sigma=gs.tier_2_max_sigma,
        tier_3_max_sigma=gs.tier_3_max_sigma,
        fixed_thresholds=_clamp_thresholds(gs.fixed_thresholds),
        paragraph_word_count=gs.paragraph_word_count,
        target_split_size=gs.target_split_size,
        min_split_size=gs.min_split_size,
        outcome_directions=gs.outcome_directions,
        temperature=gs.temperature,
        top_k=gs.top_k,
        top_p=gs.top_p,
        provider=gs.provider,
        custom_endpoint=gs.custom_endpoint,
        custom_api_key=gs.custom_api_key,
        custom_model=gs.custom_model,
        ollama_model=gs.ollama_model,
        ignore_case=gs.ignore_case,
    )


@router.get("/api/settings/boundaries")
async def get_settings_boundaries():
    gs = get_settings()
    params = build_scoring_params(gs)
    boundaries = compute_tier_boundaries(params=params)
    return {"boundaries": boundaries}


@router.get("/api/settings", response_model=SettingsResponse)
async def get_settings_endpoint():
    return _settings_to_response(get_settings())


@router.post("/api/settings", response_model=SettingsResponse)
async def update_settings_endpoint(body: SettingsPatch):
    dumped = body.model_dump(exclude_none=True)
    logger.info("POST /api/settings body=%s", dumped)
    if "outcome_directions" in dumped:
        dumped["outcome_directions"] = _normalize_directions(dumped["outcome_directions"])
    updated = update_settings(**dumped)
    return _settings_to_response(updated)


@router.post("/api/settings/reset", response_model=SettingsResponse)
async def reset_settings_endpoint():
    gs = reset_settings()
    return _settings_to_response(gs)
