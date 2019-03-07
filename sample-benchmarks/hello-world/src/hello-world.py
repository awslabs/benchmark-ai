import random

import time
from benchmarkai import emit


def main():
    begin = time.time()
    print("Hello Benchmark AI")
    time.sleep(2 + 3 * random.random())
    elapsed = time.time() - begin
    emit({"elapsed": elapsed})
    print("Bye Benchmark AI")


if __name__ == "__main__":
    main()
