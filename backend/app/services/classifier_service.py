"""
ClassifierService — loads the trained MentalHealthClassifier at startup and
provides category prediction + confidence for a given message embedding.

IMPORTANT DESIGN NOTE:
This model runs ALONGSIDE the existing keyword-based crisis detection in
crisis_service.py — it never replaces it. The keyword list remains the hard
safety net (its recall doesn't depend on how well this model was trained);
this classifier adds a second, learned signal on top of it.

If no trained weights are found on disk (e.g. train_classifier.py hasn't
been run yet), this service degrades gracefully: predict() returns
available=False, and ai_service.py falls back to the original pure
cosine-similarity behavior. The app never crashes for lack of a trained model.
"""

import json
import logging
from pathlib import Path

import numpy as np
import torch

from .classifier import MentalHealthClassifier, CATEGORIES

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
WEIGHTS_PATH = MODELS_DIR / "classifier_weights.pt"
LABEL_MAP_PATH = MODELS_DIR / "label_map.json"

# Below this confidence, treat the category prediction as too uncertain to
# act on — ai_service falls back to plain cosine-similarity retrieval instead
# of trusting the guess.
CONFIDENCE_FALLBACK_THRESHOLD = 0.35

# Confidence needed for the classifier's own "crisis" prediction to count as
# an ADDITIONAL crisis signal, on top of (never instead of) the keyword check.
#
# ⚠ SAFETY NOTE: Raised from 0.78 → 0.82 to eliminate false positives on
# short/vague messages ("yes", "okay", "I don't know") that scored ~0.6 and
# were incorrectly triggering crisis protocol. The keyword-based check in
# crisis_service.py remains the hard safety net (100% recall on known phrases)
# and is completely unaffected by this threshold.
CRISIS_CONFIDENCE_THRESHOLD = 0.82

# Number of MC Dropout forward passes used to estimate confidence/uncertainty.
# The model is tiny (~28K params), so 20 passes adds negligible latency.
MC_DROPOUT_PASSES = 20


class ClassifierService:
    def __init__(self):
        self.model: MentalHealthClassifier | None = None
        self.categories: list[str] = CATEGORIES
        self._loaded = False

    def initialize(self):
        """Load trained weights. Called once at FastAPI startup."""
        if not WEIGHTS_PATH.exists():
            logger.warning(
                f"[Classifier] No trained weights found at {WEIGHTS_PATH}. "
                "Run scripts/train_classifier.py first. Until then, the system "
                "falls back to pure cosine-similarity retrieval and "
                "keyword-only crisis detection."
            )
            return

        self.model = MentalHealthClassifier()
        self.model.load_state_dict(torch.load(WEIGHTS_PATH, map_location="cpu"))
        self.model.eval()

        if LABEL_MAP_PATH.exists():
            with open(LABEL_MAP_PATH, encoding="utf-8") as f:
                self.categories = json.load(f)["categories"]

        self._loaded = True
        logger.info(f"[Classifier] Loaded trained model ({len(self.categories)} categories).")

    def predict(self, query_vec: np.ndarray, mc_passes: int = MC_DROPOUT_PASSES) -> dict:
        """
        Returns:
        {
            "category": str | None,
            "confidence": float,
            "uncertainty": float,   # variance across MC Dropout passes
            "available": bool       # False if no trained model is loaded
        }
        """
        if not self._loaded or self.model is None:
            return {"category": None, "confidence": 0.0, "uncertainty": 0.0, "available": False}

        x = torch.tensor(np.asarray(query_vec), dtype=torch.float32).unsqueeze(0)
        pred_idx, confidence, uncertainty = self.model.predict_with_confidence(x, mc_passes=mc_passes)
        category = self.categories[pred_idx]

        return {
            "category": category,
            "confidence": float(confidence),
            "uncertainty": float(uncertainty),
            "available": True,
        }


# Singleton — initialized once at FastAPI startup, same pattern as `embedder`
classifier_service = ClassifierService()
