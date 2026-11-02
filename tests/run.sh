#!/bin/sh
# Deterministic entrypoint. Python 3.8+ and nothing else.
# All arithmetic is WAD-18 exact fixed point. No IEEE-754 anywhere in src/.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE"

export PYTHONHASHSEED=0
export LC_ALL=C
export TZ=UTC
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

echo "== D2-D6 contract (includes a static no-float audit of src/) =="
python3 src/determinism.py --assert-contract manifest.json

echo "== R3 = lfp(Phi) on the meta-invariant state =="
python3 src/r3_engine.py \
    --manifest   manifest.json \
    --invariants spec/meta_invariants.json \
    --state      data/reference_state.json \
    --trace      logs/trace.jsonl \
    --rejections logs/rejections.jsonl \
    --result     logs/result.json

echo "== certification =="
python3 src/certify.py --trace logs/trace.jsonl --manifest manifest.json

echo "== PO3 + PO4: 30 seeds, exact Wilcoxon, Cliff's delta =="
python3 src/experiment.py --out logs/po4_contribution.json \
                          --rejections logs/domain_rejections.jsonl

echo "== PO5: Sobol sensitivity in WAD-18 =="
python3 src/sensitivity.py --out logs/po5_robustness.json

echo "== PO6: external ratification status =="
python3 src/ratify.py --out logs/ratification_status.json

echo "== obligation score, in-scope denominator =="
python3 src/score.py --out logs/score.json

echo "== tests =="
python3 tests/run_all.py

echo "== mutation testing: does the suite catch anything? =="
if [ "${MUTATION:-sample}" = "exhaustive" ]; then
    # Every eligible token in every target file. Roughly 15 minutes: each of
    # 162 mutants runs the whole suite. Sharded so no single step runs long.
    for i in 0 1 2 3; do
        python3 src/mutation.py --out "logs/mut_s$i.json" --shards 4 --shard "$i"
    done
    python3 src/mutation_report.py --out logs/mutation.json
else
    # Sampled: fast, and NOT the headline number. It writes to its own file so
    # it cannot overwrite the recorded exhaustive result.
    python3 src/mutation.py --out logs/mutation_sample.json --limit 6
    echo "   (sampled. run MUTATION=exhaustive sh run.sh for the real score)"
fi

echo "== hashing artifacts =="
python3 src/hash_artifacts.py

echo "DONE. logs/score.json carries both numbers: the in-scope obligation"
echo "score, and the certificate status that qualifies it."
