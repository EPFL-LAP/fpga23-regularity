import time
import os
import argparse
import random
import math
import sys
sys.path.insert(0,'..')
sys.path.insert(0,'../..')

from parallelize import Parallel

parser = argparse.ArgumentParser()
parser.add_argument("--max_cpu")
args = parser.parse_args()

max_cpu = 1
try:
    max_cpu = int(args.max_cpu)
except:
    pass
sleep_interval = 5

root_dir = os.path.abspath("../../cleaned_patterns/")
arc_dirs = ["%s/%s/%s/" % (root_dir, feature_dir, sol_dir) for feature_dir in os.listdir(root_dir)\
            for sol_dir in os.listdir("%s/%s" % (root_dir, feature_dir))]

print arc_dirs, len(arc_dirs)

calls = []
for d in arc_dirs:
    if not os.path.isdir(d) or not "sol" in d:
        continue
    calls.append("python -u run_pnr.py --arc_dir %s" % d)

print calls, len(calls)

runner = Parallel(max_cpu, sleep_interval)
runner.init_cmd_pool(calls)
runner.run()
