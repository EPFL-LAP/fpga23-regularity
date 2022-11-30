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
parser.add_argument("--arc")
parser.add_argument("--circ")
parser.add_argument("--seed")

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
                     "--incremental_reroute_delay_ripup off",\
                     "--router_max_convergence_count 1",\
                     "--max_criticality %s" % "0.00"\
                    ]

    rr_file = "%s_rr.xml" % arc
    #if not os.path.exists(rr_file):
    #    os.system("lz4 -d %s.lz4" % rr_file)

    run_req_files = ["%s.xml" % arc,\
                     "%s_rr.xml" % arc,\
                     "base_costs.dump",\
                     "../benchmarks/%s.blif" % circ\
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

call_vpr(args.arc, args.circ, int(args.seed))
os.chdir(wd)
