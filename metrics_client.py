import redis
import threading
import time
import argparse
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, Response

# Argument parser to accept command-line parameters
parser = argparse.ArgumentParser(description='Redis-Prometheus Metrics Server')
parser.add_argument('--redis_port', type=int, default=6379, help='Port for Redis server')
parser.add_argument('--prometheus_port', type=int, default=15000, help='Port for Prometheus metrics')
args = parser.parse_args()

# Redis Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = args.redis_port
REDIS_COUNTER_KEY = "task_waitingqueue_counter"
REDIS_TIME_KEY = "task_times" # Store elapsed execution time

# Prometheus configuration
PROMETHEUS_PORT = args.prometheus_port

# Initialize Redis
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Flask App for Prometheus Metrics
app = Flask(__name__)

# Create Prometheus Registry and Metrics
registry = CollectorRegistry()
task_waiting_queue = Gauge(
    "waiting_queue_tasks",
    "Total number of tasks added to the waiting queue (pending to be computed)",
    registry=registry
)
task_execution_time = Gauge(
    "task_execution_time_seconds",
    "Elapsed execution time of the last genetic algorithm lifecycle",
    registry=registry
)

def update_metrics_from_redis():
    """
    Reads the counter from Redis and updates Prometheus metrics.
    """
    while True:
        try:
            # Read Redis counter value
            counter_value = r.get(REDIS_COUNTER_KEY)
            execution_time_value = r.get(REDIS_TIME_KEY)
            
            if counter_value:
                
                task_waiting_queue.set(int(counter_value))  # Increment counter

            if execution_time_value:
                task_execution_time.set(float(execution_time_value))  # Update execution time metric

            time.sleep(1)  # Update interval

        except redis.exceptions.ConnectionError as e:
            print(f"Redis is not reachable: {e}")
            time.sleep(1)
        except ValueError as e:
            print(f"Invalid counter value in Redis: {e}")

# Start background thread to update metrics
thread = threading.Thread(target=update_metrics_from_redis, daemon=True)
thread.start()

@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Flask route that serves Prometheus metrics.
    """
    metrics_data = generate_latest(registry)

    return Response(metrics_data, content_type=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PROMETHEUS_PORT)
