import time
import os
import argparse
import random
import math
import sys
sys.path.insert(0,'..')
sys.path.insert(0,'../..')

seeds = [19225]

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

grid_sizes = {\
"synth_p0.70_size10000_seed25891" : 39,\
"synth_p0.70_size10000_seed30331" : 39,\
"synth_p0.70_size10000_seed40493" : 39,\
"synth_p0.70_size10000_seed42057" : 39,\
"synth_p0.70_size10000_seed47660" : 39,\
"synth_p0.70_size10000_seed51127" : 39,\
"synth_p0.70_size10000_seed58338" : 39,\
"synth_p0.70_size10000_seed75796" : 39,\
"synth_p0.70_size10000_seed78380" : 39,\
"synth_p0.70_size10000_seed84443" : 39,\
}

root_dir = os.path.abspath("../../cleaned_patterns/")
arc_dirs = ["%s/%s/%s/" % (root_dir, feature_dir, sol_dir) for feature_dir in os.listdir(root_dir)\
            for sol_dir in os.listdir("%s/%s" % (root_dir, feature_dir))]
print arc_dirs, len(arc_dirs)

wd = os.getcwd()
calls = []
for d in arc_dirs:
    if not os.path.isdir(d) or not "sol" in d:
        continue
    for size in sorted(set(grid_sizes.values())):
        arc = "agilex_%d_%d" % (size, size)
        rr_file = "%s_rr.xml" % arc
        os.chdir(d)
        os.system("rm -f %s" % rr_file)
        os.system("lz4 -d %s.lz4" % rr_file)
        os.chdir('..')
        os.system("cp -r %s/benchmarks ./" % wd)
        os.chdir(wd)

    for b in sorted(grid_sizes):
        for s in seeds:
            calls.append("python -u run_pnr_gnl.py --arc_dir %s --arc %s --circ %s --seed %d"\
                         % (d, arc, b, s))
print calls, len(calls)

runner = Parallel(max_cpu, sleep_interval)
runner.init_cmd_pool(calls)
runner.run()
