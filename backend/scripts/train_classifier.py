"""
Train the MentalHealthClassifier on the corpus.

Steps:
1. Load corpus, embed every "context" string with the frozen MiniLM model
   (same model already used by the embedder at runtime).
2. Run stratified 5-fold cross-validation to get an honest accuracy/F1
   estimate on data the model never trained on within each fold.
3. Train a final model on the FULL dataset (this is the one that ships).
4. Save weights + label map + a written evaluation report.

Run from backend/:
    venv\\Scripts\\activate
    python scripts\\train_classifier.py
"""

import json
import sys
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
from sentence_transformers import SentenceTransformer

# Make `app` importable when run as a script from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.classifier import MentalHealthClassifier, CATEGORIES

CORPUS_PATH = Path(__file__).resolve().parent.parent / "corpus" / "mental_health_corpus.json"
MODELS_DIR = Path(__file__).resolve().parent.parent / "app" / "models"
WEIGHTS_PATH = MODELS_DIR / "classifier_weights.pt"
LABEL_MAP_PATH = MODELS_DIR / "label_map.json"
REPORT_PATH = MODELS_DIR / "training_report.txt"

EPOCHS = 300
LR = 1e-3
BATCH_SIZE = 16
SEED = 42

torch.manual_seed(SEED)
np.random.seed(SEED)


def load_data():
    with open(CORPUS_PATH, encoding="utf-8") as f:
        corpus = json.load(f)

    contexts = [e["context"] for e in corpus]
    labels_str = [e["category"] for e in corpus]

    cat_to_idx = {cat: i for i, cat in enumerate(CATEGORIES)}
    labels = np.array([cat_to_idx[c] for c in labels_str])

    print(f"Loaded {len(contexts)} examples across {len(set(labels_str))} categories.")
    print("Category distribution:", Counter(labels_str))

    print("Embedding all contexts with all-MiniLM-L6-v2 (frozen, no training here)...")
    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = encoder.encode(contexts, normalize_embeddings=True, show_progress_bar=True)

    return embeddings, labels, labels_str


def train_one_model(X_train, y_train, epochs=EPOCHS, lr=LR, batch_size=BATCH_SIZE):
    model = MentalHealthClassifier()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    X_t = torch.tensor(X_train, dtype=torch.float32)
    y_t = torch.tensor(y_train, dtype=torch.long)

    n = X_t.shape[0]
    model.train()
    for epoch in range(epochs):
        perm = torch.randperm(n)
        total_loss = 0.0
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            xb, yb = X_t[idx], y_t[idx]

            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(idx)

    return model


def evaluate_model(model, X_val, y_val):
    model.eval()
    with torch.no_grad():
        X_t = torch.tensor(X_val, dtype=torch.float32)
        logits = model(X_t)
        preds = torch.argmax(logits, dim=-1).numpy()
    return preds


def cross_validate(X, y, labels_str, k=5):
    print(f"\n{'='*60}\nRunning stratified {k}-fold cross-validation...\n{'='*60}")
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEED)

    all_true = []
    all_pred = []
    fold_accuracies = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), start=1):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = train_one_model(X_train, y_train)
        preds = evaluate_model(model, X_val, y_val)

        acc = float(np.mean(preds == y_val))
        fold_accuracies.append(acc)
        all_true.extend(y_val.tolist())
        all_pred.extend(preds.tolist())

        print(f"Fold {fold}/{k}: accuracy = {acc:.3f}")

    mean_acc = float(np.mean(fold_accuracies))
    std_acc = float(np.std(fold_accuracies))
    print(f"\nMean CV accuracy: {mean_acc:.3f} (+/- {std_acc:.3f})")

    report = classification_report(
        all_true, all_pred, target_names=CATEGORIES, digits=3, zero_division=0
    )
    cm = confusion_matrix(all_true, all_pred, labels=list(range(len(CATEGORIES))))

    print("\nAggregated classification report (across all folds):")
    print(report)

    return mean_acc, std_acc, report, cm


def format_confusion_matrix(cm) -> str:
    lines = ["Confusion matrix (rows = true category, columns = predicted category)", ""]
    header = "".join(f"{c[:4]:>7}" for c in CATEGORIES)
    lines.append(" " * 14 + header)
    for i, row in enumerate(cm):
        row_str = "".join(f"{v:>7}" for v in row)
        lines.append(f"{CATEGORIES[i]:<14}{row_str}")
    return "\n".join(lines)


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X, y, labels_str = load_data()

    mean_acc, std_acc, report, cm = cross_validate(X, y, labels_str, k=5)

    print(f"\n{'='*60}\nTraining FINAL model on the full dataset (this is what ships)...\n{'='*60}")
    final_model = train_one_model(X, y, epochs=EPOCHS)

    torch.save(final_model.state_dict(), WEIGHTS_PATH)
    with open(LABEL_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump({"categories": CATEGORIES}, f, indent=2)

    cm_str = format_confusion_matrix(cm)

    report_text = f"""MindBridge AI — Classifier Training Report
{'='*60}

Dataset: {CORPUS_PATH.name}
Total examples: {len(y)}
Categories ({len(CATEGORIES)}): {', '.join(CATEGORIES)}

Cross-validation: stratified 5-fold
Mean accuracy: {mean_acc:.3f} (+/- {std_acc:.3f})

Per-class precision / recall / F1 (aggregated across folds):
{report}

{cm_str}

Final model trained on full dataset ({len(y)} examples, {EPOCHS} epochs)
and saved to: {WEIGHTS_PATH.name}
Label map saved to: {LABEL_MAP_PATH.name}
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\nSaved model weights to: {WEIGHTS_PATH}")
    print(f"Saved label map to: {LABEL_MAP_PATH}")
    print(f"Saved full report to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
