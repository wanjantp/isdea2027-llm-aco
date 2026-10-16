#!/bin/bash
cd ~/ISDEA
H="--heuristic B2_k2=experiments/controls/b2_pow2.py:T1 --heuristic B2_k3=experiments/controls/b2_pow3.py:T1 --heuristic B2_k4=experiments/controls/b2_pow4.py:T1"
B="--baselines none --budgets 1x1,3x3,5x10,15x40,30x150 --seeds 10 --workers $(nproc)"
F=data/fields2benchmark; R=experiments/results/eval
python experiments/run_eval.py --fields $F/fields2benchmark_local.geojson --split $F/split.json --subset test_B $H $B --out $R/testB_beta > $R/testB_beta.log 2>&1
python experiments/run_eval.py --fields data/thai_fields/thai_fields_utm48n_local.geojson $H $B --out $R/testC_beta > $R/testC_beta.log 2>&1
python experiments/run_eval.py --fields $F/fields2benchmark_local.geojson --split $F/split.json --subset test_A $H $B --out $R/testA_beta > $R/testA_beta.log 2>&1
echo DONE > $R/beta_tests.done
