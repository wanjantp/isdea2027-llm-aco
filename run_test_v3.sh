#!/bin/bash
cd ~/ISDEA
E=experiments/results/evolve
H="--heuristic coder7b=$E/local_qwen25coder7b_T3_v3_s0/best_heuristic.py
 --heuristic q9b_T3=$E/local_qwen35_9b_T3_v3_s1/best_heuristic.py
 --heuristic q9b_T3rep=$E/local_qwen35_9b_T3_repair_v3_s1/best_heuristic.py
 --heuristic q9b_T2=$E/local_qwen35_9b_T2_v3_s0/best_heuristic.py:T2
 --heuristic q9b_T1=$E/local_qwen35_9b_T1_v3_s2/best_heuristic.py:T1
 --heuristic sol=$E/or_gpt6sol_T3_v3_s0/best_heuristic.py
 --heuristic luna=$E/or_gpt6luna_T3_v3_s1/best_heuristic.py
 --heuristic haiku=$E/or_haiku55_T3_v3_s0/best_heuristic.py
 --heuristic q9b_api=$E/or_qwen35_9b_T3_v3_s0/best_heuristic.py"
B="--budgets greedy,1x1,3x3,5x10,15x40,30x150 --seeds 10 --workers $(nproc)"
F=data/fields2benchmark
R=experiments/results/eval
python experiments/run_eval.py --fields $F/fields2benchmark_local.geojson --split $F/split.json --subset test_B $H $B --out $R/testB_v3 > $R/testB_v3.log 2>&1
python experiments/run_eval.py --fields data/thai_fields/thai_fields_utm48n_local.geojson $H $B --out $R/testC_v3 > $R/testC_v3.log 2>&1
python experiments/run_eval.py --fields $F/fields2benchmark_local.geojson --split $F/split.json --subset test_A $H $B --out $R/testA_v3 > $R/testA_v3.log 2>&1
echo ALL DONE > $R/test_v3.done
