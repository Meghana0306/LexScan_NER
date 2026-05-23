"""
Optional confidence calibration helpers.

The calibration strategy is intentionally lightweight and dependency-free:
it learns a per-label multiplier from validation examples and uses a
smoothed prior so sparse labels do not overfit wildly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class CalibrationSample:
    label: str
    score: float
    correct: bool


@dataclass
class LabelCalibration:
    sample_count: int
    observed_accuracy: float
    mean_raw_score: float
    multiplier: float


class ConfidenceCalibrator:
    def __init__(self, store_path: str | Path | None = None) -> None:
        if store_path is None:
            try:
                from config.settings import get_settings

                store_path = get_settings().calibration_store_path
            except Exception:
                store_path = Path("data") / "calibration.json"
        self.store_path = Path(store_path)
        self._label_state: dict[str, LabelCalibration] = {}

    def is_enabled(self) -> bool:
        try:
            from config.settings import get_settings

            return bool(get_settings().enable_calibration)
        except Exception:
            return False

    def fit(self, samples: list[CalibrationSample | dict[str, Any]]) -> dict[str, LabelCalibration]:
        grouped: dict[str, list[CalibrationSample]] = {}
        for raw in samples:
            sample = raw if isinstance(raw, CalibrationSample) else CalibrationSample(
                label=str(raw.get("label") or "UNKNOWN"),
                score=float(raw.get("score", 0.0)),
                correct=bool(raw.get("correct")),
            )
            grouped.setdefault(sample.label, []).append(sample)

        learned: dict[str, LabelCalibration] = {}
        for label, items in grouped.items():
            count = len(items)
            if count == 0:
                continue
            mean_score = sum(max(0.0, min(1.0, item.score)) for item in items) / count
            observed_accuracy = sum(1.0 for item in items if item.correct) / count

            # Beta-style smoothing toward identity for small sample counts.
            prior_weight = 5.0
            smoothed_accuracy = ((observed_accuracy * count) + (mean_score * prior_weight)) / (count + prior_weight)
            baseline = mean_score or 1e-6
            multiplier = max(0.25, min(2.0, smoothed_accuracy / baseline))

            learned[label] = LabelCalibration(
                sample_count=count,
                observed_accuracy=round(observed_accuracy, 6),
                mean_raw_score=round(mean_score, 6),
                multiplier=round(multiplier, 6),
            )

        self._label_state = learned
        return dict(self._label_state)

    def calibrate_score(self, label: str, score: float) -> float:
        raw = max(0.0, min(1.0, float(score)))
        state = self._label_state.get(label)
        if state is None:
            return raw
        return round(max(0.0, min(1.0, raw * state.multiplier)), 6)

    def calibrate_entity(
        self,
        entity: dict[str, Any],
        *,
        score_field: str = "confidence",
        output_field: str = "confidence_calibrated",
    ) -> dict[str, Any]:
        out = dict(entity)
        label = str(entity.get("label") or "UNKNOWN")
        raw = entity.get(score_field)
        if raw is None:
            raw = entity.get("score")
        if raw is None:
            return out
        try:
            out[output_field] = self.calibrate_score(label, float(raw))
        except (TypeError, ValueError):
            return out
        return out

    def calibrate_entities(
        self,
        entities: list[dict[str, Any]],
        *,
        score_field: str = "confidence",
        output_field: str = "confidence_calibrated",
    ) -> list[dict[str, Any]]:
        if not self.is_enabled():
            return [dict(entity) for entity in entities]
        return [
            self.calibrate_entity(entity, score_field=score_field, output_field=output_field)
            for entity in entities
        ]

    def save(self) -> Path:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "labels": {label: asdict(state) for label, state in self._label_state.items()},
        }
        self.store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.store_path

    def load(self) -> dict[str, LabelCalibration]:
        if not self.store_path.exists():
            self._label_state = {}
            return {}
        payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        labels = payload.get("labels", {})
        self._label_state = {
            label: LabelCalibration(
                sample_count=int(state.get("sample_count", 0)),
                observed_accuracy=float(state.get("observed_accuracy", 0.0)),
                mean_raw_score=float(state.get("mean_raw_score", 0.0)),
                multiplier=float(state.get("multiplier", 1.0)),
            )
            for label, state in labels.items()
        }
        return dict(self._label_state)

    def summary(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "store_path": str(self.store_path),
            "labels": {label: asdict(state) for label, state in self._label_state.items()},
        }


default_calibrator = ConfidenceCalibrator()

