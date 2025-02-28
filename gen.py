#!/usr/bin/python
#
#  Copyright 2002-2022 Barcelona Supercomputing Center (www.bsc.es)
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

# -*- coding: utf-8 -*-

import argparse
import random
import sys
import time
from pycompss.api.task import task
from pycompss.api.parameter import *
from pycompss.api.api import compss_wait_on
import redis
import json

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_QUEUE = 'task_times'
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

def getParents(population, target, retain=0.2):
    fitInd = [(p, fitness(p, target)) for p in population]
    sortFitIndices(fitInd)
    numRetain = int(len(population) * retain)
    return [fitInd[i][0] for i in range(numRetain)]


@task(fitInd=COLLECTION_INOUT)
def sortFitIndices(fitInd):
    sortFitInd = sorted(fitInd, key=lambda i: i[1])
    for i in range(len(fitInd)):
        fitInd[i] = sortFitInd[i]


@task(returns=list)
def mutate(p, seed):
    random.seed(seed)
    ind = random.randint(0, len(p) - 1)
    p[ind] = random.randint(min(p), max(p))
    return p


@task(returns=list)
def crossover(male, female):
    half = int(len(male) / 2)
    child = male[:half] + female[half:]
    return child


@task(returns=list)
def individual(size, seed):
    random.seed(seed)
    return [random.randint(0, 100) for _ in range(size)]


def genPopulation(numIndividuals, size, seed):
    return [individual(size, seed + i) for i in range(numIndividuals)]


@task(returns=float)
def fitness(individual, target):
    value = sum(individual)
    return abs(target - value)


@task(returns=1, population=COLLECTION_IN)
def grade(population, target):
    values = map(fitness, population, [target for _ in range(len(population))])
    return sum(values) / float(len(population))


def evolve(population, target, seed, retain=0.2, random_select=0.05, mutate_rate=0.01):
    # Get parents
    parents = getParents(population, target, retain)

    # Add genetic diversity
    for p in population:
        if p not in parents and random_select > random.random():
            parents.append(p)

    # Mutate some individuals
    for p in parents:
        if mutate_rate > random.random():
            p = mutate(p, seed)
            seed += 1
    random.seed(seed)

    # Crossover parents to create childrens
    childrens = []
    numParents = len(parents)
    while len(childrens) < len(population) - numParents:
        male = random.randint(0, numParents - 1)
        female = random.randint(0, numParents - 1)
        if male != female:
            childrens.append(crossover(parents[male], parents[female]))

    newpopulation = parents + childrens
    # Return population
    return newpopulation

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Genetic Algorithm Implementation with PyCOMPSs")
    parser.add_argument('-n', '--num_individuals', type=int, default=100,
                        help="Number of individuals in the population")
    parser.add_argument('-s', '--size', type=int, default=100,
                        help="Size of each individual (number of genes)")
    parser.add_argument('-x', '--target', type=int, default=200,
                        help="Target value for fitness function")
    parser.add_argument('-l', '--lifecycles', type=int, default=10,
                        help="Number of generations (life cycles)")
    parser.add_argument('-gf', '--get-fitness', type=str, choices=['True', 'False'], default="True",
                        help="Enable ('True') or disable ('False') fitness history (default: 'True').")

    args = parser.parse_args()

    args.get_fitness = args.get_fitness == "True"

    return args

def main():
    # Input parameters
    args = parse_args()

    N = args.num_individuals # 100  # individuals
    size = args.size # 100  # size of individuals
    x = args.target # 200  # target
    lifeCycles = args.lifecycles # 10
    get_fitness = args.get_fitness # True or False

    seed = 1234

    print("----- PARAMS -----")
    print(f" - N: {N}")
    print(f" - size: {size}")
    print(f" - x: {x}")
    print(f" - lifeCycles: {lifeCycles}")
    print("------------------")

    st = time.time()
    p = genPopulation(N, size, seed)
    et = time.time()

    print("genPopulation: Elapsed Time {} (s)".format(et - st))
    if get_fitness:
        fitnessHistory = [grade(p, x)]

    for i in range(lifeCycles):
        cycle_start = time.time()  # Start timing the lifecycle
        p = evolve(p, x, seed)
        p = compss_wait_on(p) # Wait until all tasks in the lifecycle finish
        cycle_end = time.time()
        elapsed_time = cycle_end - cycle_start
        r.set(REDIS_QUEUE, elapsed_time)
        print(f"ELAPSED TIME IS: {elapsed_time}")

        seed += 1
        if get_fitness:
            fitnessHistory.append(grade(p, x))
    else:
        p = compss_wait_on(p)
        print("genAlgorithm: Elapsed Time {} (s)".format(time.time() - et))
        print("Final result: %s" % str(p))
        if get_fitness:
            fitnessHistory.append(grade(p, x))
            fitnessHistory = compss_wait_on(fitnessHistory)
            print("final fitness: {}".format(fitnessHistory))

if __name__ == "__main__":
    main()