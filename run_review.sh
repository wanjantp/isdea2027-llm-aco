#!/bin/bash
cd ~/ISDEA
E=experiments/results/evolve; F=data/fields2benchmark; R=experiments/results/eval; W="--workers $(nproc) --baselines none --seeds 10"
H=""; for d in $E/*_v3_s*/; do n=$(basename $d); t=T3; [[ $n == *_T1_* ]] && t=T1; [[ $n == *_T2_* ]] && t=T2; H="$H --heuristic $n=${d}best_heuristic.py:$t"; done
K="--heuristic coder7b_noturn=experiments/controls/knockout/coder7b_noturn.py --heuristic q9b_T2_noturn=experiments/controls/knockout/q9b_T2_noturn.py:T2 --heuristic q9b_T3_noturn=experiments/controls/knockout/q9b_T3_noturn.py"
for t in A B; do
  python experiments/run_eval.py --fields $F/fields2benchmark_local.geojson --split $F/split.json --subset test_$t $H $K $W --budgets 3x3,5x10 --out $R/test${t}_allruns > $R/test${t}_allruns.log 2>&1
done
python experiments/run_eval.py --fields data/thai_fields/thai_fields_utm48n_local.geojson $H $K $W --budgets 3x3,5x10 --out $R/testC_allruns > $R/testC_allruns.log 2>&1
S="--heuristic B2_k5=experiments/controls/b2_pow5.py:T1 --heuristic B2_k2=experiments/controls/b2_pow2.py:T1 --heuristic coder7b=$E/local_qwen25coder7b_T3_v3_s0/best_heuristic.py --heuristic q9b_T2=$E/local_qwen35_9b_T2_v3_s0/best_heuristic.py:T2 --heuristic q9b_T3=$E/local_qwen35_9b_T3_v3_s1/best_heuristic.py"
for c in 05 2; do
  python experiments/run_eval.py --fields $F/fields2benchmark_local.geojson --split $F/split.json --subset test_A $S --workers $(nproc) --baselines B2_distance --seeds 10 --budgets 3x3,5x10 --uav data/energy/sens/uav_cturn_x$c.json --out $R/testA_cturn_x$c > $R/testA_cturn_x$c.log 2>&1
done
echo DONE > $R/review.done
