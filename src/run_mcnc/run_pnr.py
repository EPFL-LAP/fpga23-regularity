"""Runs a VPR flow on the given architecture, circuit, and placement seed.

Parameters
----------
arc_dir : str
    Directory holding the architecture files.
arc : str
    Name of the architecture.
circ : str
    Name of the circuit.
seed : int
    Placement seed.
"""

import time
import os
import argparse
import sys
sys.path.insert(0,'..')

import setenv_testing

parser = argparse.ArgumentParser()
parser.add_argument("--arc_dir")
parser.add_argument("--benchmark_path")

seeds = [19225, 25124, 43033, 50936, 5300]

grid_sizes =  {\
               'spla': 22,
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
               'misex3': 15\
              }

args = parser.parse_args()

wd = os.getcwd()
os.chdir(args.arc_dir)
##########################################################################
def call_vpr(arc, circ, seed):
    """Calls VPR

    Parameters
    ----------
    arc : str
        Name of the architecture.
    circ : str
        Name of the circuit.
    seed : int
        Placement seed.

    Returns
    -------
    None
    """

    vpr_arguments = ["%s.xml" % arc,\
                     "%s.blif" % circ\
                    ]
 
    vpr_switches = ["--pack",\
                    "--place",\
                    "--seed %d" % seed\
                   ]
   
    vpr_switches += ["--route",\
                     "--read_rr_graph %s_rr.xml" % arc,\
                     "--route_chan_width 352",\
                     "--router_lookahead map",\
                     "--routing_failure_predictor off",\
                     "--max_router_iterations 300",\
                     "--incremental_reroute_delay_ripup on",\
                     "--router_max_convergence_count 1",\
                     "--max_criticality %s" % "0.99"\
                    ]

    final_res_file = "vpr_%s_%d.log" % (circ, seed)
    #if os.path.exists(final_res_file):
    #    return

    rr_file = "%s_rr.xml" % arc
    os.system("lz4 -d -f %s.lz4" % rr_file)

    default_base_costs_content = "0 0 0 0 0 0\n1 0.001000\n0 -9"
    with open("base_costs.dump", "w") as outf:
        outf.write(default_base_costs_content)

    run_req_files = ["%s.xml" % arc,\
                     "%s_rr.xml" % arc,\
                     "base_costs.dump",\
                     "%s/%s.blif" % (args.benchmark_path, circ)\
                    ]

    sandbox = "sandbox_%s_%s_%d_%s" % (os.getcwd().replace('/', "__"), circ, seed, str(time.time()))
    os.system("mkdir %s" % (os.environ["VPR_RUN_PATH"] % sandbox))

    for f in run_req_files:
        os.system("cp %s %s/" % (f, os.environ["VPR_RUN_PATH"] % sandbox))

    elim = " --random_sort_nets true --random_sort_nets_seed %SHUFFLE_SEED%"

    vpr_call = "time %s" % (os.environ["VPR"].replace(elim, '').replace(" -it ", " -i ") % (sandbox, ' '.join(vpr_arguments + vpr_switches)))
    print vpr_call
    os.system(vpr_call)

    os.system("cp %s/vpr_stdout.log ./vpr_%s_%d.log" % (os.environ["VPR_RUN_PATH"] % sandbox, circ, seed))

    os.system("rm -rf %s" % (os.environ["VPR_RUN_PATH"] % sandbox))
##########################################################################

for circ in grid_sizes:
    arc = "agilex_%d_%d" % (grid_sizes[circ], grid_sizes[circ])
    for seed in seeds:
        call_vpr(arc, circ, seed)
        os.system("rm -f %s_rr.xml" % arc)

os.chdir(wd)
