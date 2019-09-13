#!/usr/bin/env python

import logging
import time

for i in range(1000):
    print(f"accuracy={i}", flush=True)
    logging.basicConfig(level=logging.DEBUG)
    logging.info(f"accuracy={i}")
    logging.error(f"accuracy={i}")
    time.sleep(1)
