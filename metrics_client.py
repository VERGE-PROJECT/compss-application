import argparse
from prometheus_client import CollectorRegistry, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, Response
import os
import re
import socket
import redis
import threading
import time
import sys

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_QUEUE = 'task_times_queue'
DEFAULT_PROMETHEUS_PORT = 15000
BATCHING_SIZE = 10 # Size of Redis POP elements in the queue

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

app = Flask(__name__)

def parse_buckets(bucket_string):
    """
    Parses a comma-separated string of buckets into a list of floats.
    Example input: "0.001,0.005,0.01,0.1,1,10"
    """
    try:
        return [
            float(bucket) if bucket.lower() not in ['inf', '-inf']
            else float('inf') if bucket.lower() == 'inf' else float('-inf')
            for bucket in bucket_string.split(',')
        ]
    except ValueError:
        raise argparse.ArgumentTypeError("Buckets must be a comma-separated list of numeric values, with 'inf' or '-inf' for infinity.")

def create_histogram_registry(buckets=None):
    """
    Creates a new Prometheus histogram registry and returns it along with the histogram object.
    """
    if buckets is None:
        # Default buckets if none are provided
        buckets = [0.0001, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.1, 1, 10, 50, 100, 200, float('inf')]
    
    registry = CollectorRegistry()

    execution_time_task_histogram = Histogram(
        'task_execution_time_seconds', 'Time taken for each fused_multiply_add task',
        ['worker'], registry=registry,
        buckets=buckets
    )
    return registry, execution_time_task_histogram

def process_redis_queue():
    """
    Processes the tasks in the Redis queue and adds their values to the histogram.
    Returns the updated registry and histogram.
    """

    global registry_histogram, execution_time_task_histogram
    hostname_worker = socket.gethostname()

    while True:
        try:
            queue_value = r.rpop(REDIS_QUEUE, BATCHING_SIZE)        

            if queue_value:
                for q in queue_value:
                    execution_time_task_histogram.labels(worker=hostname_worker).observe(float(q.decode("utf-8")))
            else:
                time.sleep(0.1)

        except redis.exceptions.ConnectionError as e:
            print(f"Redis is not ready or unreachable: {e}")
            time.sleep(1)  # Retry after a delay if Redis is down

@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Flask route that serves Prometheus metrics after reading and processing all the data files.
    """
    # Read data files and create the histogram
    global registry_histogram  # Use the global registry

    # Generate the latest metrics in Prometheus format
    metrics_data = generate_latest(registry_histogram)

    return Response(metrics_data, content_type=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Prometheus Histogram Metrics Service")
    parser.add_argument('--buckets', type=parse_buckets, 
                        help="Comma-separated list of bucket values for the histogram (e.g., 0.001,0.005,0.01,0.1,1,10).")
    
    args = parser.parse_args()
    
    registry_histogram, execution_time_task_histogram = create_histogram_registry(buckets=args.buckets)

    thread = threading.Thread(target=process_redis_queue, daemon=True)
    thread.start()

    # Start the Flask app for serving metrics
    app.run(host='0.0.0.0', port=DEFAULT_PROMETHEUS_PORT)
