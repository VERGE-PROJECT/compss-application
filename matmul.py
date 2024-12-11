import time
import numpy as np

from pycompss.api.task import task
from pycompss.api.api import compss_barrier

from pycompss.api.parameter import INOUT
from pycompss.api.api import compss_barrier
from pycompss.api.api import compss_wait_on
import redis

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_QUEUE = 'task_times_queue'
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

@task(returns=1)
def generate_block(size, num_blocks, seed=0, set_to_zero=False):
    """
    Generate a square block of given size.
    :param size: <Integer> Block size
    :param num_blocks: <Integer> Number of blocks
    :param seed: <Integer> Random seed
    :param set_to_zero: <Boolean> Set block to zeros
    :return: Block
    """

    if not set_to_zero:
        b = np.array(range(1, size*size+1)).reshape(size, size)
    else:
        b = np.zeros((size, size))
    return b

@task(C=INOUT)
def fused_multiply_add(A, B, C):
    """
    Multiplies two Blocks and accumulates the result in an INOUT Block (FMA).
    :param A: Block A
    :param B: Block B
    :param C: Result Block
    :return: None
    """

    C += np.dot(A, B)

def dot(A, B, C):
    """
    A COMPSs blocked matmul algorithm.
    :param A: Block A
    :param B: Block B
    :param C: Result Block
    :return: None
    """
    n, m = len(A), len(B[0])
    # as many rows as A, as many columns as B
    for i in range(n):
        for j in range(m):
            for k in range(n):
                fused_multiply_add(A[i][k], B[k][j], C[i][j])


def main(num_blocks, elems_per_block, seed, number_iterations):
    """
    Matmul main.
    :param num_blocks: <Integer> Number of blocks
    :param elems_per_block: <Integer> Number of elements per block
    :param sleep_tasks: <Integer> Number of WarmUp tasks
    :param seed: <Integer> Random seed
    :return: None
    """
        
    compss_barrier()
    start_time = time.time()

    for n in range(number_iterations):
        # Generate the dataset in a distributed manner
        # i.e: avoid having the master a whole matrix
        A, B, C = [], [], []
        matrix_name = ["A", "B"]

        for i in range(num_blocks):
            for l in [A, B, C]:
                l.append([])
            # Keep track of blockId to initialize with different random seeds
            bid = 0
            for j in range(num_blocks):
                for ix, l in enumerate([A, B]):
                    l[-1].append(generate_block(elems_per_block, num_blocks, seed=seed + bid, set_to_zero=False))
                    bid += 1
                C[-1].append(generate_block(elems_per_block, num_blocks, set_to_zero=True))
        compss_barrier()
        initialization_time = time.time()

        # Do matrix multiplication
        start_time = time.time()

        dot(A, B, C)

        compss_barrier()
        multiplication_time = time.time()

        r.lpush(REDIS_QUEUE, f"{multiplication_time - initialization_time}")

        print("-----------------------------------------")
        print("-------------- RESULTS ------------------")
        print("-----------------------------------------")
        print("Initialization time: %f" % (initialization_time -
                                        start_time))
        print("Multiplication time: %f" % (multiplication_time -
                                        initialization_time))
        print("Total time: %f" % (multiplication_time - start_time))
        print("-----------------------------------------")

def parse_args():
    """
    Arguments parser.
    Code for experimental purposes.
    :return: Parsed arguments.
    """
    import argparse
    description = 'COMPSs blocked matmul implementation'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-b', '--num_blocks', type=int, default=1,
                        help='Number of blocks (N in NxN)'
                        )
    parser.add_argument('-e', '--elems_per_block', type=int, default=2,
                        help='Elements per block (N in NxN)'
                        )
    parser.add_argument('--seed', type=int, default=0,
                        help='Pseudo-Random seed'
                        )
    parser.add_argument('-n', '--number_iterations', type=int, default=10,
                        help='Number of matmul iterations'
                        )

    return parser.parse_args()


if __name__ == "__main__":
    opts = parse_args()
    main(**vars(opts))