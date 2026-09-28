"""Plain-language explanation of a site's risk estimate.

Turns standardized elastic-net contributions (coef x standardized feature value)
into ranked, human-readable drivers with direction. Used by the site health card
and the citizen copilot. The copilot LLM only ever *rephrases* this output — it
never invents numbers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import RISK_COMPONENTS
from .features import plain


def site_contributions(model, x_row: np.ndarray, target: str = "composite") -> pd.DataFrame:
    """Per-feature contribution = standardized_value * coefficient.

    Returns a frame with feature, plain label, contribution, and direction.
    For 'composite' we average contributions across the three components.
    """
    feats = model.feature_names
    targets = RISK_COMPONENTS if target == "composite" else [target]
    contribs = np.zeros(len(feats))
    for t in targets:
        pipe = model.estimators[t]
        imp = pipe.named_steps["impute"]
        scl = pipe.named_steps["scale"]
        enet = pipe.named_steps["enet"]
        x_imp = imp.transform(x_row.reshape(1, -1))
        x_std = scl.transform(x_imp).ravel()
        contribs += x_std * enet.coef_
    contribs /= len(targets)

    df = pd.DataFrame({
        "feature": feats,
        "label": [plain(f) for f in feats],
        "contribution": contribs,
    })
    df["abs"] = df["contribution"].abs()
    df["direction"] = np.where(df["contribution"] >= 0, "raises risk", "lowers risk")
    return df.sort_values("abs", ascending=False).reset_index(drop=True)


def top_drivers_text(model, x_row: np.ndarray, target: str = "composite", k: int = 3) -> list[str]:
    """Top-k drivers as plain sentences. Empty list if the model is ~flat here."""
    df = site_contributions(model, x_row, target)
    df = df[df["abs"] > 1e-4].head(k)
    out = []
    for _, r in df.iterrows():
        verb = "raises" if r["contribution"] >= 0 else "lowers"
        out.append(f"{r['label'].capitalize()} {verb} the estimate")
    return out
