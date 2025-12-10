# COMPSs Workload Applications Used in VERGE WP3 Experiments

This repository contains the Python scripts included inside the COMPSs container image used for the VERGE WP3 experiments. These applications correspond to the computational workloads executed to evaluate **task-based scheduling**, **autoscaling**, and **execution-time monitoring** in the scenarios described in *Deliverable D3.2*.

The applications represent two distinct algorithmic patterns frequently used in WP3 evaluations:

1. **A genetic algorithm workload**, aligned with the GA-based experiments referenced in the deliverable.
2. **A blocked matrix-multiplication workload**, used to benchmark parallel execution, DAG behavior, and resource-allocation effects (see the *benchmarking application DAG* presented in Section 3.2).
3. **A Prometheus metrics exporter**, aligned with the monitoring instrumentation described in WP3 for autoscaling and performance tracking (e.g., Grafana dashboards in autoscaling evaluations).

These scripts were embedded in the COMPSs container image deployed on Kubernetes during the experiments.

---

## 1. `gen.py` — Genetic-Algorithm Benchmark Application

### General description of what the app does

`gen.py` implements a **distributed genetic algorithm**, where a population evolves through repeated selection, crossover, mutation, and fitness evaluation. Each part of the algorithm is mapped to PyCOMPSs tasks, enabling parallel execution across multiple workers.
In short, the application generates an initial population, evaluates it, evolves it over several generations, and reports the execution time of each cycle into Redis for monitoring.

---

### Role in experiments

* Represents an **iterative compute workload** with repeated evaluation, mutation, and evolution cycles.
* Mirrors the structure of **multi-stage workflows** used to test:

  * vertical/horizontal scaling behavior,
  * task distribution efficiency,
  * queue sizes and execution-time effects (e.g., cumulative delays shown in Figure 3-18).
* Reports execution-time metrics to Redis, which are later scraped by Prometheus—consistent with the monitoring setup shown in D3.2’s autoscaling evaluation (Grafana dashboards).

### Functional overview

* Defines COMPSs tasks for:

  * fitness computation,
  * population grading,
  * mutation and crossover,
  * individual creation and population sorting.
* Runs for several lifecycles, accumulating execution metrics.

---

## 2. `matmul.py` — Blocked Matrix-Multiplication Application

### General description of what the app does

`matmul.py` performs a **blocked matrix multiplication** using PyCOMPSs tasks. Instead of multiplying whole matrices at once, the application divides them into smaller blocks and computes each partial multiplication via distributed tasks. This approach stresses parallelism, data locality, and worker utilization.
The application repeats the multiplication for several iterations and publishes timing information to Redis.

---

### Role in experiments

* Models a **regular, highly parallel workload**, enabling controlled evaluation of:

  * task-granularity effects,
  * scaling decisions,
  * worker utilization patterns,
  * execution-time variability under autoscaling.
* Matches the type of compute-intensive benchmark used in Section 3 (Task-based scheduling, Autoscaling).

### Functional overview

* Generates distributed block matrices using COMPSs tasks.
* Computes each partial product block via a fused multiply–add task.
* Repeats the multiplication for several iterations to generate consistent performance data.
* Publishes execution metrics to Redis → Prometheus → ServiceMonitor.

---

## 3. `metrics_client.py` — Prometheus Metrics Exporter

### General description of what the app does

`metrics_client.py` acts as a **Prometheus exporter**. It periodically reads metrics produced by the GA and MatMul applications (e.g., execution times, queue counters) from Redis and exposes them through a `/metrics` HTTP endpoint. A Kubernetes **ServiceMonitor** collects these metrics and forwards them to Prometheus and Grafana.

This script closes the monitoring loop required for evaluating autoscaling and scheduling mechanisms.

---

### Role in experiments

The autoscaling and scheduling results in D3.2 (e.g., Grafana visualizations of CPU usage, execution times, queue evolution) rely on a monitoring pipeline. The pipeline described in the experiments corresponds to:

```
Application → Redis → Prometheus ServiceMonitor → Grafana
```

This file implements the **Prometheus endpoint** that allows the ServiceMonitor to collect metrics.

### Functional overview

* A background thread periodically reads:

  * GA or MatMul execution times,
  * queue size or runtime counters,
  * task metrics stored in Redis.
* Exposes them as Prometheus gauges via `/metrics`.
* Serves as the bridge between application-level performance data and the observability stack used in VERGE WP3.

---

# Summary: Relation to VERGE D3.2

The three scripts correspond to the application workloads and monitoring components required for:

* **Task-based scheduling evaluations** (Section 3.2)
  Benchmark workflows and DAG-structured tasks.

* **Autoscaling experiments** (Section 3.1)
  Metrics and execution traces collected via Redis → Prometheus → Grafana.

* **Edge-resource-management analysis**
  Use of repeatable workloads (GA and MatMul) for evaluating:

  * vertical and horizontal scaling,
  * task delay accumulation,
  * worker elasticity,
  * execution-time profiles.

These workloads were packaged inside the COMPSs container image used on Kubernetes during the VERGE WP3 experiments.

---
