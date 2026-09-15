"""compare_three_models.py — W4 activity three-way comparison.

After running compare_models.py with --models llama3.2:3b (using qwen3.5:latest) (after
Lab Step 3 with gpt-4o-mini and gpt-4o), this script pulls the
three-way summary from data/answers.db.

Usage:
    python compare_three_models.py
"""
import sqlite3
from pathlib import Path


DB_PATH = Path("data/answers.db")


def main():
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found. Run compare_models.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Summary table
    print("\n=== Three-way model comparison ===\n")
    cur.execute("""
        SELECT
            model,
            COUNT(*) AS n,
            ROUND(SUM(cost_usd), 6) AS total_cost_usd,
            ROUND(AVG(cost_usd), 6) AS avg_cost_usd,
            ROUND(AVG(confidence), 2) AS avg_confidence
        FROM answers
        WHERE model IN ('gpt-4o-mini', 'gpt-4o', 'qwen3.5:latest')

        GROUP BY model
        ORDER BY total_cost_usd DESC
    """)
    rows = cur.fetchall()
    print(f"{'model':<15} {'n':<6} {'total_$':<15} {'avg_$':<13} {'avg_conf':<10}")
    print("-" * 65)
    for model, n, total, avg, conf in rows:
        print(f"{model:<15} {n:<6} {total:<15} {avg:<13} {conf:<10}")

    # Spot-check a question where the quality gap usually shows
    print("\n\n=== Sample answers for the schema-versioning question ===\n")
    cur.execute("""
        SELECT model, substr(content, 1, 200)
        FROM answers
        WHERE question LIKE '%schema_version%'
           OR question LIKE '%schema versioning%'
        ORDER BY model
    """)
    for model, content in cur.fetchall():
        print(f"--- {model} ---")
        print(content)
        print()

    conn.close()


if __name__ == "__main__":
    main()
