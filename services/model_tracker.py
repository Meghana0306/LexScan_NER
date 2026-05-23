"""
Optional model performance tracker.

Writes JSONL records for predictions and user corrections so teams can
measure drift and accuracy trends later without changing current outputs.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TrackerSummary:
    predictions_logged: int
    feedback_logged: int
    compared_predictions: int
    exact_match_accuracy: float | None


class ModelTracker:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        if base_dir is None:
            try:
                from config.settings import get_settings

                base_dir = get_settings().model_tracker_dir
            except Exception:
                base_dir = Path("logs") / "model_tracker"
        self.base_dir = Path(base_dir)

    def is_enabled(self) -> bool:
        try:
            from config.settings import get_settings

            return bool(get_settings().enable_model_tracker)
        except Exception:
            return False

    @property
    def predictions_path(self) -> Path:
        return self.base_dir / "predictions.jsonl"

    @property
    def feedback_path(self) -> Path:
        return self.base_dir / "feedback.jsonl"

    def _ensure_dir(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def record_prediction(
        self,
        *,
        route: str,
        text: str,
        domain: str,
        entities: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if not self.is_enabled():
            return None
        prediction_id = uuid.uuid4().hex
        payload = {
            "prediction_id": prediction_id,
            "timestamp": time.time(),
            "route": route,
            "domain": domain,
            "text_length": len(text or ""),
            "entity_count": len(entities or []),
            "entities": entities or [],
            "metadata": metadata or {},
        }
        self._append_jsonl(self.predictions_path, payload)
        return prediction_id

    def record_feedback(
        self,
        *,
        prediction_id: str,
        corrected_entities: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        if not self.is_enabled():
            return False
        payload = {
            "prediction_id": prediction_id,
            "timestamp": time.time(),
            "corrected_entities": corrected_entities or [],
            "metadata": metadata or {},
        }
        self._append_jsonl(self.feedback_path, payload)
        return True

    def summarize(self) -> TrackerSummary:
        predictions = self._read_jsonl(self.predictions_path)
        feedback = self._read_jsonl(self.feedback_path)
        feedback_by_id = {item.get("prediction_id"): item for item in feedback if item.get("prediction_id")}
        compared = 0
        exact_matches = 0

        for pred in predictions:
            pred_id = pred.get("prediction_id")
            if pred_id not in feedback_by_id:
                continue
            compared += 1
            predicted_entities = self._normalized_entities(pred.get("entities") or [])
            corrected_entities = self._normalized_entities(feedback_by_id[pred_id].get("corrected_entities") or [])
            if predicted_entities == corrected_entities:
                exact_matches += 1

        accuracy = None if compared == 0 else round(exact_matches / compared, 6)
        return TrackerSummary(
            predictions_logged=len(predictions),
            feedback_logged=len(feedback),
            compared_predictions=compared,
            exact_match_accuracy=accuracy,
        )

    def log_degradation_if_needed(self) -> TrackerSummary:
        summary = self.summarize()
        if summary.exact_match_accuracy is None:
            return summary
        try:
            from config.settings import get_settings
            from utils.logger import get_logger

            threshold = float(get_settings().model_tracker_alert_threshold)
            if summary.exact_match_accuracy < threshold:
                get_logger("model_tracker").warning(
                    "model_accuracy_degraded",
                    extra={
                        "extra": {
                            "exact_match_accuracy": summary.exact_match_accuracy,
                            "threshold": threshold,
                            "compared_predictions": summary.compared_predictions,
                        }
                    },
                )
        except Exception:
            pass
        return summary

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        self._ensure_dir()
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def _normalized_entities(self, entities: list[dict[str, Any]]) -> list[tuple[str, str, int | None, int | None]]:
        normalized: list[tuple[str, str, int | None, int | None]] = []
        for entity in entities:
            normalized.append(
                (
                    str(entity.get("text") or "").strip().lower(),
                    str(entity.get("label") or "").strip().upper(),
                    entity.get("start"),
                    entity.get("end"),
                )
            )
        return sorted(normalized)


model_tracker = ModelTracker()

