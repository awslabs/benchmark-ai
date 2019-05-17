#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import time

from benchmarkai import emit

data = [
    {"epoch": 0, "train_loss": 0.460807, "loss": 0.192550, "accuracy": 0.944300},
    {"epoch": 1, "train_loss": 0.162091, "loss": 0.135516, "accuracy": 0.960900},
    {"epoch": 2, "train_loss": 0.113452, "loss": 0.109727, "accuracy": 0.966900},
    {"epoch": 3, "train_loss": 0.085680, "loss": 0.098235, "accuracy": 0.969900},
    {"epoch": 4, "train_loss": 0.068107, "loss": 0.092545, "accuracy": 0.972900},
    {"epoch": 5, "train_loss": 0.055417, "loss": 0.091006, "accuracy": 0.973900},
    {"epoch": 6, "train_loss": 0.046595, "loss": 0.098780, "accuracy": 0.972000},
    {"epoch": 7, "train_loss": 0.039786, "loss": 0.118688, "accuracy": 0.965500},
    {"epoch": 8, "train_loss": 0.033924, "loss": 0.103051, "accuracy": 0.970900},
    {"epoch": 9, "train_loss": 0.031788, "loss": 0.095670, "accuracy": 0.972900},
    {"epoch": 10, "train_loss": 0.026517, "loss": 0.110327, "accuracy": 0.971000},
    {"epoch": 11, "train_loss": 0.024278, "loss": 0.094628, "accuracy": 0.975700},
    {"epoch": 12, "train_loss": 0.020678, "loss": 0.104235, "accuracy": 0.975800},
    {"epoch": 13, "train_loss": 0.017242, "loss": 0.105687, "accuracy": 0.974900},
    {"epoch": 14, "train_loss": 0.016686, "loss": 0.104539, "accuracy": 0.975200},
    {"epoch": 15, "train_loss": 0.015184, "loss": 0.094542, "accuracy": 0.976900},
    {"epoch": 16, "train_loss": 0.014336, "loss": 0.098181, "accuracy": 0.978100},
    {"epoch": 17, "train_loss": 0.010966, "loss": 0.098650, "accuracy": 0.978600},
    {"epoch": 18, "train_loss": 0.011719, "loss": 0.110302, "accuracy": 0.973900},
    {"epoch": 19, "train_loss": 0.008234, "loss": 0.112208, "accuracy": 0.974600},
    {"epoch": 20, "train_loss": 0.007219, "loss": 0.111866, "accuracy": 0.975500},
    {"epoch": 21, "train_loss": 0.006741, "loss": 0.116808, "accuracy": 0.974400},
    {"epoch": 22, "train_loss": 0.007437, "loss": 0.117510, "accuracy": 0.973900},
    {"epoch": 23, "train_loss": 0.006743, "loss": 0.108727, "accuracy": 0.977800},
    {"epoch": 24, "train_loss": 0.005527, "loss": 0.133827, "accuracy": 0.972300},
]


def main():
    logging.basicConfig(level=logging.DEBUG)

    logging.info("🍹  Hello Benchmark AI 🏝")

    logging.info("-- Simulating MNIST training --")

    begin = time.time()
    for point in data:
        time.sleep(1)
        elapsed = time.time() - begin
        logging.info(f"elapsed: {elapsed}")
        emit(point)

    logging.info("-- done --")
    logging.info("Bye 😎  bye")


if __name__ == "__main__":
    main()
