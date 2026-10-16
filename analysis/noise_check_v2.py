# Run from anywhere: python analysis/noise_check_v2.py  (about 2 min on 2 cores)
"""Training-fitness noise on train_v2 with T25 params: per-seed ACO 3x3 energies for seeds 0..14 on all 30 training fields,
for the seed heuristic (B2), the k=5 control and the selected coder7b and qwen T3 heuristics. Fitness for seed triple j = seeds 3j..3j+2."""
import os, sys, json, pickle, multiprocessing as mp
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, R + "/src"); os.chdir(R)
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[k] = "1"
import numpy as np; np.seterr(all="ignore")
from llm_evolve import reference_energies, swath_cache
from fields import load_fields
from energy import Costs, UAVModel
from aco import ACO, ACOParams
from heuristics import load_heuristic_from_code, mask_for_template
E = "experiments/results/evolve"
H = {"B2": ("experiments/controls/b2_pow1.5.py", "T3"), "k5": ("experiments/controls/b2_pow5.py", "T3"),
     "coder7b": (E + "/local_qwen25coder7b_T3_v3_s0/best_heuristic.py", "T3"), "q9b_T3": (E + "/local_qwen35_9b_T3_v3_s1/best_heuristic.py", "T3")}
B2CODE = "import numpy as np\ndef heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):\n    return 1.0/(dist_m+1.0)\n"
FP = "data/train/train_v2.geojson"; UAV = "data/energy/uav_params.json"
ids = [f.id for f in load_fields(FP, None)]
OUT = os.path.join(R, "supplement"); os.makedirs(OUT, exist_ok=True)
def job(args):
    name, seed = args
    code = B2CODE if name == "B2" else open(H[name][0]).read()
    fn = load_heuristic_from_code(code); uav = UAVModel.load(UAV)
    sw = swath_cache(FP, ids, 5.0, os.path.join(__import__("tempfile").gettempdir(), "train_v2_swaths.pkl"))
    return name, seed, {fid: ACO(ACOParams(n_ants=3, n_iters=3), fn, seed=seed, feature_mask=mask_for_template(H[name][1])).run(Costs(sw[fid], (0.0, 0.0), uav))[1].energy_J for fid in ids}
if __name__ == "__main__":
    ref = reference_energies(FP, ids, 5.0, UAV); swath_cache(FP, ids, 5.0, os.path.join(__import__("tempfile").gettempdir(), "train_v2_swaths.pkl"))
    res = {}
    with mp.Pool(2) as p:
        for name, seed, e in p.imap_unordered(job, [(n, s) for s in range(15) for n in H]):
            res.setdefault(name, {})[seed] = e; print(name, seed, flush=True)
    json.dump({"ref": ref, "res": res}, open(os.path.join(OUT, "noise_v2.json"), "w"))
