from __future__ import annotations
import numpy as np
import pandas as pd
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.observables.diagnostics import hole_scrambling_number

def threshold_scan(config: dict, out_csv: str | None = None) -> pd.DataFrame:
    ph_values = config.get("threshold", {}).get("hole_fractions", [0.0, 0.1, 0.2, 0.3])
    eta_values = config.get("threshold", {}).get("mobile_etas", [0.0, 0.4])
    lsd_values = config.get("threshold", {}).get("lambda_sds", [0.0, 0.25])
    dims = config.get("threshold", {}).get("dimensions", [1, 3])
    seeds = config.get("threshold", {}).get("seeds", [101, 102])
    criterion_db = float(config.get("threshold", {}).get("target_xi2_db", -3.0))
    rows = []
    for d in dims:
        shape = (int(config.get("threshold", {}).get("L1", 14)),) if d == 1 else (3, 3, 3) if d == 3 else (4, 4)
        graph = hypercubic_lattice(shape, False)
        times = np.linspace(0.0, float(config.get("dtwa", {}).get("t_max", 1.3)), int(config.get("dtwa", {}).get("n_steps", 27)))
        for eta in eta_values:
            for lsd in lsd_values:
                for ph in ph_values:
                    vals = []
                    spins = []
                    for s in seeds:
                        ctrl = ControlProtocol(enabled=False, jz_initial=float(config.get("model", {}).get("jz", 0.35)), final_time=float(times[-1]))
                        res = run_dtwa(graph, times, jz=float(config.get("model", {}).get("jz", 0.35)), hole_fraction=float(ph), mobile_eta=float(eta), lambda_sd=float(lsd), n_traj=int(config.get("dtwa", {}).get("n_traj", 64)), seed=int(s), control=ctrl)
                        data = res["data"]
                        idx = int(np.nanargmin(data[:,4]))
                        vals.append(float(data[idx,5])); spins.append(float(data[idx,7]))
                    mean_db = float(np.mean(vals)); std_db = float(np.std(vals, ddof=1)) if len(vals)>1 else 0.0
                    success = bool(mean_db < criterion_db and np.mean(spins) > 0.25)
                    rows.append({"dimension": int(d), "N": int(graph.n_sites), "p_h": float(ph), "mobile_eta": float(eta), "lambda_sd": float(lsd), "xi2_db_min_mean": mean_db, "xi2_db_min_std": std_db, "spin_length_mean": float(np.mean(spins)), "success_target": success, "target_xi2_db": criterion_db, "K_hsd": hole_scrambling_number(float(ph), float(eta), float(lsd), graph.coordination_average, float(times[-1]))})
    df = pd.DataFrame(rows)
    if out_csv:
        df.to_csv(out_csv, index=False)
    return df

def ph_star_table(scan: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in scan.groupby(["dimension", "mobile_eta", "lambda_sd"]):
        ok = group[group["success_target"]]
        ph_star = float(ok["p_h"].max()) if len(ok) else float("nan")
        rows.append({"dimension": keys[0], "mobile_eta": keys[1], "lambda_sd": keys[2], "p_h_star": ph_star, "n_points": int(len(group))})
    return pd.DataFrame(rows)
