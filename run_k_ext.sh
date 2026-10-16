#!/bin/bash
cd ~/ISDEA
H="--heuristic B2_k5=experiments/controls/b2_pow5.py:T1 --heuristic B2_k6=experiments/controls/b2_pow6.py:T1 --heuristic B2_k8=experiments/controls/b2_pow8.py:T1"
F=data/fields2benchmark; R=experiments/results/eval; W="--workers $(nproc) --baselines none"
python experiments/run_eval.py --fields $F/fields2benchmark_local.geojson --split $F/split.json --subset validation $H $W --budgets greedy,1x1,3x3,5x10 --seeds 5 --out $R/validation_k_ext > $R/validation_k_ext.log 2>&1
for t in test_A test_B; do python experiments/run_eval.py --fields $F/fields2benchmark_local.geojson --split $F/split.json --subset $t $H $W --budgets 1x1,3x3,5x10 --seeds 10 --out $R/${t/_/}_k_ext > $R/${t/_/}_k_ext.log 2>&1; done
python experiments/run_eval.py --fields data/thai_fields/thai_fields_utm48n_local.geojson $H $W --budgets 1x1,3x3,5x10 --seeds 10 --out $R/testC_k_ext > $R/testC_k_ext.log 2>&1
lscpu | grep -E "Model name|^CPU\(s\)" > $R/cpu_info.txt
echo DONE > $R/k_ext.done
