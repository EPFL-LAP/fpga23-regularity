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

grid_sizes =  {'spla': 22,\
               'diffeq': 13,\
               'clma': 31,\
               'ex5p': 12,\
               's38584.1': 26,\
               'seq': 16,\
               'ex1010': 23,\
               's38417': 23,\
               'apex2': 16,\
               's298': 15,\
               'apex4': 14,\
               'elliptic': 19,\
               'alu4': 15,\
               'tseng': 13,\
               'pdc': 24,\
               'frisc': 22,\
               'misex3': 15,\
               'gnl' : 39,\
              }

unique_sizes = sorted(set(grid_sizes.values()))

root_dir = os.path.abspath("../../cleaned_patterns/")
pattern_dirs = [d for d in os.listdir(root_dir) if os.path.isdir("%s/%s" % (root_dir, d))]

patterns = sorted(["%s/%s/%s" % (root_dir, d, f) for d in pattern_dirs\
                   for f in os.listdir("%s/%s" % (root_dir, d)) if f.endswith(".ilp")])

print patterns

#Create the necessary directories and copy the needed files.
for pattern in patterns:
    local_dir = pattern.rsplit('.', 1)[0]
    os.system("rm -rf %s/" % local_dir)
    os.system("mkdir %s/" % local_dir)
    os.system("cp %s %s/" % (pattern, local_dir))
    os.system("cp -r essential_files/* %s" % local_dir)

    print pattern
    os.system("python finalize_pattern.py --all_edges all_edges.list --pattern %s/%s" % (local_dir, pattern.rsplit('/', 1)[1]))

#Spice all models for the smallest grid size.
calls = []
min_grid_size = min(grid_sizes.values())
size = min_grid_size
meas = " --measure_delays 1"
for pattern in patterns:
    rundir = pattern.rsplit('.', 1)[0]
    os.system("rm -rf %s/src/" % rundir)
    os.system("mkdir %s/src/" % rundir)
    os.system("cp -r ../ %s/src/" % rundir) 
    calls.append("python run_arc_gen_pattern_swap_only.py --grid_w %d --grid_h %d --arc_name agilex --run_dir %s/ %s"\
                 % (size, size, rundir, meas))
runner = Parallel(max_cpu, sleep_interval)
runner.init_cmd_pool(calls)
runner.run()
del runner

#Resize all models to all needed grid sizes.
calls = []
meas = " --measure_delays 0"
for pattern in patterns:
    rundir = pattern.rsplit('.', 1)[0]
    for size in unique_sizes:
        if size == min_grid_size:
            continue
        os.system("cp %s/agilex_%d_%d.xml %s/agilex.xml" % (rundir, min_grid_size, min_grid_size, rundir))
        calls.append("python run_arc_gen_pattern_swap_only.py --grid_w %d --grid_h %d --arc_name agilex --run_dir %s/ %s"\
                    % (size, size, rundir, meas))

print calls

runner = Parallel(max_cpu, sleep_interval)
runner.init_cmd_pool(calls)
runner.run()
del runner
