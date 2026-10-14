"""Evaluation metrics and statistics for binary classification."""

from typing import Any, Dict, List, Union
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
import torch


def compute_metrics(
    y_true: Union[np.ndarray, torch.Tensor],
    y_pred_probs: Union[np.ndarray, torch.Tensor],
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Compute comprehensive binary classification metrics.
    
    Metrics:
      - Accuracy
      - Balanced Accuracy
      - Precision
      - Recall
      - F1 Score
      - ROC-AUC
      - Confusion Matrix [[TN, FP], [FN, TP]]
      
    Args:
        y_true: Ground truth binary labels (0 or 1).
        y_pred_probs: Predicted probabilities in [0.0, 1.0].
        threshold: Decision boundary threshold (default 0.5).
        
    Returns:
        Dict mapping metric names to computed values.
    """
    if isinstance(y_true, torch.Tensor):
        y_true = y_true.detach().cpu().numpy()
    if isinstance(y_pred_probs, torch.Tensor):
        y_pred_probs = y_pred_probs.detach().cpu().numpy()

    y_true = y_true.astype(int).flatten()
    y_pred_probs = y_pred_probs.astype(float).flatten()
    y_pred = (y_pred_probs >= threshold).astype(int)

    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    if len(np.unique(y_true)) < 2:
        auc = 0.5
    else:
        try:
            auc = float(roc_auc_score(y_true, y_pred_probs))
        except (ValueError, IndexError):
            auc = 0.5

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()

    return {
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "roc_auc": auc,
        "confusion_matrix": cm,
    }
