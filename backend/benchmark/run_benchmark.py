"""
ARGUS — Benchmark Harness & Three-Way Comparison (backend/benchmark/run_benchmark.py)

Evaluates three surveillance systems against the authoritative 10-call ground truth:
1. Keyword Baseline (Deterministic rule scanner, naive: any candidate = violation)
2. Gemini Detection Only (Gemini Flash candidate flagging without investigation)
3. Full ARGUS Pipeline (End-to-end: Transcription -> DLP -> Detection -> File Search -> Investigation)

Key Benchmark Principles (Section 18):
- Evaluates against backend/benchmark/ground_truth.json (3 HIGH, 2 MEDIUM, 2 LOW, 3 CLEAN).
- Call #9 (CALL_RM005_CUST005_20260319_1200 - ambiguous suitability) is strictly excluded
  from precision, recall, and F1 metrics and reported separately as judgment-dependent.
- Full-pipeline recall is bounded by Detection recall (the Investigator only filters, never discovers).
- Latency statistics are derived directly from pipeline_stage_timing in Cloud SQL.
- Outputs backend/benchmark/benchmark_report.json and backend/benchmark/benchmark_report.md.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import statistics

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings
from backend.adapters.database import db_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("argus.benchmark")

GROUND_TRUTH_FILE = PROJECT_ROOT / "backend" / "benchmark" / "ground_truth.json"
CANDIDATES_DIR = PROJECT_ROOT / "backend" / "compliance" / "candidates"
REPORT_JSON_FILE = PROJECT_ROOT / "backend" / "benchmark" / "benchmark_report.json"
REPORT_MD_FILE = PROJECT_ROOT / "backend" / "benchmark" / "benchmark_report.md"

CALL_9_ID = "CALL_RM005_CUST005_20260319_1200"


def load_ground_truth() -> List[Dict[str, Any]]:
    """Loads authoritative ground truth metadata for the 10 demo calls."""
    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["ground_truth"]


def evaluate_keyword_baseline_for_call(call_id: str) -> Dict[str, Any]:
    """
    Evaluates System 1: Keyword Baseline (Phase 6 Deterministic Scanner).
    Naive decision rule: Any candidate flagged is treated as a confirmed violation.
    """
    cand_path = CANDIDATES_DIR / f"{call_id}.json"
    if not cand_path.exists() and call_id.startswith("CALL_"):
        cand_path = CANDIDATES_DIR / f"{call_id[5:]}.json"

    if not cand_path.exists():
        return {
            "has_violation": False,
            "candidate_count": 0,
            "severity": "CLEAN",
            "category": None
        }

    with open(cand_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    candidates = data.get("candidates", [])
    if not candidates:
        return {
            "has_violation": False,
            "candidate_count": 0,
            "severity": "CLEAN",
            "category": None
        }

    # Highest severity among rule candidates
    best = candidates[0]
    return {
        "has_violation": True,
        "candidate_count": len(candidates),
        "severity": best.get("confidence_signal", "LOW"),
        "category": best.get("category"),
    }


def evaluate_gemini_detection_for_call(call_id: str) -> Dict[str, Any]:
    """
    Evaluates System 2: Gemini Detection Only.
    Naive decision rule: Any candidate flagged by Gemini Flash is treated as a confirmed violation.
    """
    sql = "SELECT candidate_id, category, severity_hint FROM candidate WHERE call_id = %s"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (call_id,))
            cands = cur.fetchall()

    if not cands:
        return {
            "has_violation": False,
            "candidate_count": 0,
            "severity": "CLEAN",
            "category": None
        }

    return {
        "has_violation": True,
        "candidate_count": len(cands),
        "severity": cands[0]["severity_hint"],
        "category": cands[0]["category"]
    }


def evaluate_full_pipeline_for_call(call_id: str) -> Dict[str, Any]:
    """
    Evaluates System 3: Full ARGUS Pipeline.
    Decision rule: Investigation Agent CONFIRMED outcome with all 4 hard guardrails enforced.
    """
    call_sql = "SELECT has_violation, finding_count, severity FROM `call` WHERE id = %s"
    inv_sql = "SELECT outcome, reasoning FROM investigation WHERE call_id = %s"

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(call_sql, (call_id,))
            call_row = cur.fetchone()

            cur.execute(inv_sql, (call_id,))
            inv_rows = cur.fetchall()

    has_violation = bool(call_row and call_row.get("has_violation"))
    severity = call_row.get("severity") if call_row and has_violation else "CLEAN"

    outcomes = [r["outcome"] for r in inv_rows] if inv_rows else []
    return {
        "has_violation": has_violation,
        "finding_count": call_row.get("finding_count", 0) if call_row else 0,
        "severity": severity or "CLEAN",
        "investigation_outcomes": outcomes
    }


def calculate_metrics(predictions: List[bool], ground_truth: List[bool]) -> Dict[str, float]:
    """Computes Precision, Recall, F1, Accuracy, TP, FP, FN, TN."""
    tp = sum(1 for p, g in zip(predictions, ground_truth) if p and g)
    fp = sum(1 for p, g in zip(predictions, ground_truth) if p and not g)
    fn = sum(1 for p, g in zip(predictions, ground_truth) if not p and g)
    tn = sum(1 for p, g in zip(predictions, ground_truth) if not p and not g)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(predictions) if predictions else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4)
    }


def fetch_pipeline_timing_stats() -> Dict[str, Any]:
    """Queries Cloud SQL pipeline_stage_timing for real execution latencies."""
    sql = """
    SELECT stage_name, duration_ms 
    FROM pipeline_stage_timing 
    ORDER BY stage_name, duration_ms
    """
    stage_durations: Dict[str, List[int]] = {}
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            for r in cur.fetchall():
                st = r["stage_name"]
                d = r["duration_ms"]
                stage_durations.setdefault(st, []).append(d)

    timing_summary: Dict[str, Any] = {}
    total_durations = []

    for stage, vals in stage_durations.items():
        if vals:
            timing_summary[stage] = {
                "mean_ms": round(statistics.mean(vals), 1),
                "median_ms": round(statistics.median(vals), 1),
                "min_ms": min(vals),
                "max_ms": max(vals),
                "sample_count": len(vals)
            }

    # Query total run duration from pipeline_run
    run_sql = "SELECT total_duration_ms FROM pipeline_run WHERE total_duration_ms > 0"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(run_sql)
            runs = [r["total_duration_ms"] for r in cur.fetchall()]

    if runs:
        timing_summary["end_to_end"] = {
            "mean_ms": round(statistics.mean(runs), 1),
            "median_ms": round(statistics.median(runs), 1),
            "min_ms": min(runs),
            "max_ms": max(runs),
            "sample_count": len(runs)
        }

    return timing_summary


def run_benchmark_evaluation() -> Dict[str, Any]:
    """Executes the complete three-way benchmark and produces structured results."""
    gt_items = load_ground_truth()

    call_evaluations = []
    
    gt_binary_eval = []
    baseline_binary_eval = []
    detection_binary_eval = []
    pipeline_binary_eval = []

    call_9_eval = {}

    for item in gt_items:
        call_id = item["call_id"]
        gt_sev = item["ground_truth_severity"]
        gt_has_violation = (gt_sev != "CLEAN")

        # Evaluate System 1: Keyword Baseline
        sys1 = evaluate_keyword_baseline_for_call(call_id)
        # Evaluate System 2: Gemini Detection Only
        sys2 = evaluate_gemini_detection_for_call(call_id)
        # Evaluate System 3: Full ARGUS Pipeline
        sys3 = evaluate_full_pipeline_for_call(call_id)

        eval_record = {
            "call_id": call_id,
            "ground_truth": {
                "severity": gt_sev,
                "category": item.get("ground_truth_category"),
                "has_violation": gt_has_violation,
                "note": item.get("note")
            },
            "keyword_baseline": sys1,
            "detection_only": sys2,
            "full_pipeline": sys3,
        }
        call_evaluations.append(eval_record)

        # Separate Call #9
        if call_id == CALL_9_ID:
            call_9_eval = eval_record
        else:
            gt_binary_eval.append(gt_has_violation)
            baseline_binary_eval.append(sys1["has_violation"])
            detection_binary_eval.append(sys2["has_violation"])
            pipeline_binary_eval.append(sys3["has_violation"])

    # Compute Comparative Metrics
    metrics_baseline = calculate_metrics(baseline_binary_eval, gt_binary_eval)
    metrics_detection = calculate_metrics(detection_binary_eval, gt_binary_eval)
    metrics_pipeline = calculate_metrics(pipeline_binary_eval, gt_binary_eval)

    # Fetch latency diagnostics from Cloud SQL
    timings = fetch_pipeline_timing_stats()

    is_mock = settings.is_mock()

    benchmark_report = {
        "title": "ARGUS Compliance Surveillance Three-Way Benchmark",
        "timestamp": "2026-10-15T08:30:00Z",
        "provider_mode": "mock" if is_mock else "vertex_ai",
        "mock_mode": is_mock,
        "models": {
            "flash": settings.GEMINI_FLASH_MODEL,
            "transcribe": settings.GEMINI_TRANSCRIBE_MODEL,
        },
        "theoretical_grounding": {
            "recall_bound": "Full-pipeline recall is fundamentally bounded by Detection recall. The Investigation Agent acts strictly as a forensic filter and never discovers candidates that Detection missed."
        },
        "comparative_metrics": {
            "keyword_baseline": {
                "name": "Keyword Rules Baseline",
                "description": "Deterministic regex and keyword scanner (Phase 6 rule engine alone; any candidate = violation)",
                **metrics_baseline
            },
            "gemini_detection_only": {
                "name": "Gemini Detection Only",
                "description": "Gemini Flash candidate detector without forensic investigation (any candidate = violation)",
                **metrics_detection
            },
            "full_argus_pipeline": {
                "name": "Full ARGUS Pipeline",
                "description": "Autonomous multi-stage pipeline: Gemini STT -> DLP -> Detection -> File Search -> Investigation with 4 Hard Guardrails",
                **metrics_pipeline
            }
        },
        "call_9_analysis": {
            "call_id": CALL_9_ID,
            "description": "Ambiguous suitability evaluation (Moderate risk profile, Low investment experience).",
            "ground_truth_note": "A genuine judgment call; either CONFIRMED-LOW or DISMISSED is acceptable. Excluded from strict precision/recall.",
            "keyword_baseline_outcome": call_9_eval.get("keyword_baseline", {}),
            "gemini_detection_outcome": call_9_eval.get("detection_only", {}),
            "full_pipeline_outcome": call_9_eval.get("full_pipeline", {}),
        },
        "stage_latency_diagnostics": timings,
        "calls_breakdown": call_evaluations
    }

    # Save to JSON
    REPORT_JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_JSON_FILE, "w", encoding="utf-8") as jf:
        json.dump(benchmark_report, jf, indent=2)

    # Generate Markdown Report
    generate_markdown_report(benchmark_report)

    return benchmark_report


def generate_markdown_report(data: Dict[str, Any]):
    """Generates an auditable markdown benchmark report."""
    m_base = data["comparative_metrics"]["keyword_baseline"]
    m_det = data["comparative_metrics"]["gemini_detection_only"]
    m_pipe = data["comparative_metrics"]["full_argus_pipeline"]
    timings = data.get("stage_latency_diagnostics", {})

    md_lines = [
        "# ARGUS — Three-Way Compliance Intelligence Benchmark",
        "",
        f"**Environment:** {'MOCK MODE (Offline Synthetic Fixtures)' if data['mock_mode'] else 'LIVE GCP (Vertex AI)'}  ",
        f"**Evaluation Models:** `{data['models']['flash']}` (Detection & Investigation), `{data['models']['transcribe']}` (Ingestion)  ",
        f"**Corpus Evaluated:** 10 Standardized Regulatory Compliance Calls (3 HIGH, 2 MEDIUM, 2 LOW, 3 CLEAN)  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Comparative Performance",
        "",
        "| Evaluation Metric | System 1: Keyword Baseline | System 2: Gemini Detection Only | System 3: Full ARGUS Pipeline |",
        "|---|:---:|:---:|:---:|",
        f"| **Precision** | {m_base['precision'] * 100:.1f}% | {m_det['precision'] * 100:.1f}% | **{m_pipe['precision'] * 100:.1f}%** |",
        f"| **Recall** | {m_base['recall'] * 100:.1f}% | {m_det['recall'] * 100:.1f}% | **{m_pipe['recall'] * 100:.1f}%** |",
        f"| **F1 Score** | {m_base['f1'] * 100:.1f}% | {m_det['f1'] * 100:.1f}% | **{m_pipe['f1'] * 100:.1f}%** |",
        f"| **Accuracy** | {m_base['accuracy'] * 100:.1f}% | {m_det['accuracy'] * 100:.1f}% | **{m_pipe['accuracy'] * 100:.1f}%** |",
        f"| **True Positives (TP)** | {m_base['tp']} / 6 | {m_det['tp']} / 6 | **{m_pipe['tp']} / 6** |",
        f"| **False Positives (FP)** | {m_base['fp']} | {m_det['fp']} | **{m_pipe['fp']}** |",
        f"| **False Negatives (FN)** | {m_base['fn']} | {m_det['fn']} | **{m_pipe['fn']}** |",
        "",
        "> [!IMPORTANT]",
        "> **Theoretical Recall Bound Directive:**",
        f"> {data['theoretical_grounding']['recall_bound']}",
        "",
        "---",
        "",
        "## 2. Call #9 Analysis (Ambiguous Suitability Case)",
        "",
        f"- **Call ID:** `{data['call_9_analysis']['call_id']}`",
        f"- **Context:** {data['call_9_analysis']['description']}",
        f"- **Methodological Note:** {data['call_9_analysis']['ground_truth_note']}",
        f"- **System 1 (Keyword Baseline):** Fired candidate? `{data['call_9_analysis']['keyword_baseline_outcome'].get('has_violation')}`",
        f"- **System 2 (Gemini Detection):** Candidate staged? `{data['call_9_analysis']['gemini_detection_outcome'].get('has_violation')}`",
        f"- **System 3 (Full Pipeline):** Final outcome: `{data['call_9_analysis']['full_pipeline_outcome'].get('investigation_outcomes', ['DISMISSED'])[0] if data['call_9_analysis']['full_pipeline_outcome'].get('investigation_outcomes') else 'DISMISSED'}`",
        "",
        "---",
        "",
        "## 3. Real Pipeline Stage Latencies (from `pipeline_stage_timing`)",
        "",
        "| Pipeline Stage | Mean Duration (ms) | Median Duration (ms) | Min (ms) | Max (ms) | Sample Count |",
        "|---|:---:|:---:|:---:|:---:|:---:|",
    ]

    for stage, sdata in timings.items():
        md_lines.append(
            f"| `{stage}` | {sdata['mean_ms']} | {sdata['median_ms']} | {sdata['min_ms']} | {sdata['max_ms']} | {sdata['sample_count']} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## 4. Detailed Per-Call Evaluation Ledger",
        "",
        "| Call ID | Ground Truth | System 1 (Rule Baseline) | System 2 (Detection Only) | System 3 (Full ARGUS) |",
        "|---|:---:|:---:|:---:|:---:|",
    ])

    for c in data["calls_breakdown"]:
        cid = c["call_id"]
        gt_s = c["ground_truth"]["severity"]
        s1_s = "VIOLATION" if c["keyword_baseline"]["has_violation"] else "CLEAN"
        s2_s = "VIOLATION" if c["detection_only"]["has_violation"] else "CLEAN"
        s3_s = "VIOLATION" if c["full_pipeline"]["has_violation"] else "CLEAN"
        md_lines.append(f"| `{cid}` | **{gt_s}** | {s1_s} | {s2_s} | **{s3_s}** |")

    md_lines.append("")
    with open(REPORT_MD_FILE, "w", encoding="utf-8") as mf:
        mf.write("\n".join(md_lines))


def main():
    logger.info("Starting ARGUS Three-Way Benchmark Harness...")
    report = run_benchmark_evaluation()
    m_base = report["comparative_metrics"]["keyword_baseline"]
    m_det = report["comparative_metrics"]["gemini_detection_only"]
    m = report["comparative_metrics"]["full_argus_pipeline"]
    logger.info(
        f"Benchmark Complete! Full ARGUS Pipeline Precision: {m['precision']*100:.1f}%, "
        f"Recall: {m['recall']*100:.1f}%, F1: {m['f1']*100:.1f}%"
    )
    print("\n[ARGUS Benchmark] Three-Way Comparison Results:")
    print(f" - Keyword Regex Baseline: Precision {m_base['precision']*100:.1f}%, Recall {m_base['recall']*100:.1f}%, F1 {m_base['f1']*100:.1f}%")
    print(f" - Gemini Detection Only: Precision {m_det['precision']*100:.1f}%, Recall {m_det['recall']*100:.1f}%, F1 {m_det['f1']*100:.1f}%")
    print(f" - ARGUS Full Pipeline: Precision {m['precision']*100:.1f}%, Recall {m['recall']*100:.1f}%, F1 {m['f1']*100:.1f}%")
    print(f"Report written to:\n - {REPORT_JSON_FILE}\n - {REPORT_MD_FILE}\n")


if __name__ == "__main__":
    main()
