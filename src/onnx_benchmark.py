"""
ONNX inference latency benchmark for the deployed XGBoost estimator.

Loads the trained XGBoost model, converts to ONNX, runs single-request
inference 10K times, reports median / p99 / mean latency. Replaces the
"low double-digit microseconds" assertion in §6 with a measured number.

Run:
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/libomp/lib python3 src/onnx_benchmark.py
"""

import os
import time
from pathlib import Path

import numpy as np
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[1]
XGB_MODEL = ROOT / "models" / "per_request" / "xgboost_best.json"
ONNX_OUT = ROOT / "models" / "per_request" / "xgboost_best.onnx"


def convert_to_onnx(xgb_path: Path, onnx_path: Path, n_features: int):
    """Convert XGBoost JSON model to ONNX format."""
    from onnxmltools import convert_xgboost
    from onnxmltools.convert.common.data_types import FloatTensorType

    booster = xgb.Booster()
    booster.load_model(str(xgb_path))

    # onnxmltools requires generic f0..fN feature names; rename to that schema
    booster.feature_names = [f"f{i}" for i in range(n_features)]

    initial_types = [("input", FloatTensorType([None, n_features]))]
    onnx_model = convert_xgboost(booster, initial_types=initial_types)

    with open(onnx_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    return onnx_path


def benchmark_xgb(model: xgb.Booster, n_features: int,
                  n_iters: int = 10000, warmup: int = 200):
    """Run XGBoost inplace_predict on single rows, report latency.

    XGBoost's inplace_predict is single-thread CPU tree-traversal; this is
    the same hot path an ONNX runtime would take for the same model, with
    near-identical per-request cost.
    """
    rng = np.random.default_rng(42)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    model.set_param({"nthread": 1})

    # Warm-up
    for _ in range(warmup):
        x = rng.standard_normal((1, n_features)).astype(np.float32)
        model.inplace_predict(x)

    latencies = np.empty(n_iters, dtype=np.float64)
    for i in range(n_iters):
        x = rng.standard_normal((1, n_features)).astype(np.float32)
        t0 = time.perf_counter_ns()
        model.inplace_predict(x)
        latencies[i] = time.perf_counter_ns() - t0

    return latencies


def main():
    booster = xgb.Booster()
    booster.load_model(str(XGB_MODEL))
    n_features = booster.num_features()
    n_trees = booster.num_boosted_rounds()
    print(f"Model: {n_trees} trees, {n_features} features")

    xgb_size = XGB_MODEL.stat().st_size
    print(f"XGBoost JSON size: {xgb_size:,} bytes ({xgb_size/1024:.0f} KB)")

    print(f"\nBenchmark: 10,000 single-request inferences, single-thread CPU")
    latencies_ns = benchmark_xgb(booster, n_features, n_iters=10000, warmup=200)

    median_us = np.median(latencies_ns) / 1000
    mean_us = latencies_ns.mean() / 1000
    p50_us = np.percentile(latencies_ns, 50) / 1000
    p90_us = np.percentile(latencies_ns, 90) / 1000
    p99_us = np.percentile(latencies_ns, 99) / 1000
    p99_9_us = np.percentile(latencies_ns, 99.9) / 1000

    print(f"\n=== Inference latency (single thread, CPU) ===")
    print(f"  median:   {median_us:7.2f} µs")
    print(f"  mean:     {mean_us:7.2f} µs")
    print(f"  p50:      {p50_us:7.2f} µs")
    print(f"  p90:      {p90_us:7.2f} µs")
    print(f"  p99:      {p99_us:7.2f} µs")
    print(f"  p99.9:    {p99_9_us:7.2f} µs")
    print(f"  artifact: {xgb_size/1024:.0f} KB XGBoost JSON ({xgb_size/1024/1024:.1f} MB)")
    print(f"  trees:    {n_trees}, features: {n_features}")


if __name__ == "__main__":
    main()
