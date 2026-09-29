#!/usr/bin/env bash
# chunk_sweep_runner.sh — W6 Activity A convenience script.
#
# Runs the three chunk-size profiles (small / medium / large) end-to-end:
#   build index -> run eval -> print KPIs
# Then summarises the comparison in one table.

set -euo pipefail

CORPUS="${CORPUS:-data/corpus}"

declare -a PROFILES=(
    "small:300:30"
    "medium:500:50"
    "large:800:80"
)

echo "=== W6 Activity A — chunk-size sweep ==="
echo "Corpus: $CORPUS"
echo ""

# Build the three indexes
for profile in "${PROFILES[@]}"; do
    IFS=':' read -r name size overlap <<< "$profile"
    out="data/embeddings_${name}.json"
    echo "[1/3] Building ${name} (size=${size}, overlap=${overlap})..."
    python scripts/build_index.py \
        --corpus "$CORPUS" \
        --size "$size" --overlap "$overlap" \
        --out "$out"
    echo ""
done

# Run the eval for each
for profile in "${PROFILES[@]}"; do
    IFS=':' read -r name size overlap <<< "$profile"
    label="wk6-chunk-${name}"
    index="data/embeddings_${name}.json"
    echo "[2/3] Eval for ${name}..."
    python scripts/run_rag_eval.py --label "$label" --index "$index"
    echo ""
done

# Compute KPIs side by side
echo "[3/3] Comparison:"
echo ""
printf "%-10s %-12s %-12s %-12s\n" "Profile" "Hit rate" "Cost/q" "p95 latency"
echo "------------------------------------------------------------"
for profile in "${PROFILES[@]}"; do
    IFS=':' read -r name size overlap <<< "$profile"
    label="wk6-chunk-${name}"
    hit=$(python scripts/compute_kpis.py --metric retrieval_hit_rate --label "$label" --plain)
    cost=$(python scripts/compute_kpis.py --metric cost_per_query --label "$label" --plain)
    lat=$(python scripts/compute_kpis.py --metric latency_p95 --label "$label" --plain)
    printf "%-10s %-12s %-12s %-12s\n" "$name" "$hit" "$cost" "$lat"
done

echo ""
echo "Done. Add the table above to wk6-snapshot.md under '## Activity A — chunk-size sweep'."
