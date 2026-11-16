"""Run jafgen with every random draw seeded; writes `jaffle-data/raw_*.csv` under the working directory.

Usage: `python -m slayer_evals.dataset.jafgen_child <seed> <years>`. Meant for a throwaway child process: it reseeds
the global generators and replaces `uuid.uuid4`.
"""

import random
import sys
import uuid

import numpy as np
from faker import Faker
from jafgen.simulation import Simulation

PREFIX = "raw"


def main(seed: int, years: int) -> None:
    # jafgen's modules seed Faker on import, so every seed is set after importing them.
    random.seed(seed)
    np.random.seed(seed % 2**32)
    Faker.seed(seed)
    ids = random.Random(f"{seed}:uuid")
    uuid.uuid4 = lambda: uuid.UUID(int=ids.getrandbits(128), version=4)
    sim = Simulation(years, PREFIX)
    sim.run_simulation()
    sim.save_results()


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
