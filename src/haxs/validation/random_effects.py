
from __future__ import annotations
import numpy as np
import pandas as pd


def balanced_random_effects_anova(df: pd.DataFrame, value_col: str = "effect_db", occ_col: str = "occupancy_idx", path_col: str = "path_idx", phase_col: str = "phase_idx") -> dict[str, float]:
    """Balanced nested ANOVA for y_{ijk}=mu+occ_i+path_{j(i)}+phase_{k(ij)}.

    Returns non-negative method-of-moments variance components and the standard
    error of the overall mean. Input must contain a complete balanced grid.
    """
    d = df[[occ_col, path_col, phase_col, value_col]].copy()
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    d = d.dropna()
    I = int(d[occ_col].nunique()); J = int(d[path_col].nunique()); K = int(d[phase_col].nunique())
    if I < 2 or J < 2 or K < 2:
        raise ValueError("random-effects ANOVA requires at least 2 occupancy, path, and phase levels")
    counts = d.groupby([occ_col, path_col, phase_col]).size()
    if not (len(counts) == I * J * K and counts.eq(1).all()):
        raise ValueError("input is not a complete balanced occupancy/path/phase grid")
    y = d.pivot_table(index=[occ_col, path_col], columns=phase_col, values=value_col)
    # convert to I x J x K ordered array
    arr = np.empty((I, J, K), dtype=float)
    occs = sorted(d[occ_col].unique()); paths = sorted(d[path_col].unique()); phases = sorted(d[phase_col].unique())
    for ii,o in enumerate(occs):
        for jj,p in enumerate(paths):
            vals = d[(d[occ_col]==o)&(d[path_col]==p)].sort_values(phase_col)[value_col].to_numpy(float)
            arr[ii,jj,:] = vals
    grand = float(arr.mean())
    occ_mean = arr.mean(axis=(1,2))
    path_mean = arr.mean(axis=2)
    ss_occ = J*K * float(np.sum((occ_mean - grand)**2))
    ss_path = K * float(np.sum((path_mean - occ_mean[:,None])**2))
    ss_phase = float(np.sum((arr - path_mean[:,:,None])**2))
    df_occ = I-1; df_path = I*(J-1); df_phase = I*J*(K-1)
    ms_occ = ss_occ / df_occ if df_occ else np.nan
    ms_path = ss_path / df_path if df_path else np.nan
    ms_phase = ss_phase / df_phase if df_phase else np.nan
    sigma_phase = max(float(ms_phase), 0.0)
    sigma_path = max(float((ms_path - ms_phase)/K), 0.0)
    sigma_occ = max(float((ms_occ - ms_path)/(J*K)), 0.0)
    var_mean_occ = sigma_occ / I
    var_mean_path = sigma_path / (I*J)
    var_mean_phase = sigma_phase / (I*J*K)
    var_mean_total = var_mean_occ + var_mean_path + var_mean_phase
    se = float(np.sqrt(max(var_mean_total, 0.0)))
    return {
        "n_occupancy": I, "n_paths_per_occupancy": J, "n_phase_batches_per_path": K,
        "mean_effect_db": grand,
        "sigma2_occupancy": sigma_occ,
        "sigma2_path": sigma_path,
        "sigma2_phase_batch": sigma_phase,
        "var_mean_occupancy": var_mean_occ,
        "var_mean_path": var_mean_path,
        "var_mean_phase_batch": var_mean_phase,
        "var_mean_total": var_mean_total,
        "hierarchical_standard_error": se,
        "phase_fraction_of_mean_variance": float(var_mean_phase / var_mean_total) if var_mean_total > 0 else np.nan,
        "path_fraction_of_mean_variance": float(var_mean_path / var_mean_total) if var_mean_total > 0 else np.nan,
        "occupancy_fraction_of_mean_variance": float(var_mean_occ / var_mean_total) if var_mean_total > 0 else np.nan,
        "ms_occupancy": float(ms_occ), "ms_path_within_occupancy": float(ms_path), "ms_phase_within_path": float(ms_phase),
    }


def bootstrap_hierarchical_ci(df: pd.DataFrame, value_col: str = "effect_db", occ_col: str = "occupancy_idx", path_col: str = "path_idx", phase_col: str = "phase_idx", n_boot: int = 2000, seed: int = 1729, ci: float = 0.95) -> tuple[float, float]:
    rng = np.random.default_rng(int(seed))
    occs = sorted(df[occ_col].unique())
    reps = []
    for _ in range(int(n_boot)):
        vals = []
        occ_samp = rng.choice(occs, size=len(occs), replace=True)
        for o in occ_samp:
            sub_o = df[df[occ_col] == o]
            paths = sorted(sub_o[path_col].unique())
            path_samp = rng.choice(paths, size=len(paths), replace=True)
            for p in path_samp:
                sub_p = sub_o[sub_o[path_col] == p]
                phases = sorted(sub_p[phase_col].unique())
                phase_samp = rng.choice(phases, size=len(phases), replace=True)
                for k in phase_samp:
                    vals.extend(sub_p[sub_p[phase_col] == k][value_col].to_numpy(float).tolist())
        reps.append(float(np.mean(vals)))
    alpha = (1.0-float(ci))/2.0
    return float(np.quantile(reps, alpha)), float(np.quantile(reps, 1-alpha))
