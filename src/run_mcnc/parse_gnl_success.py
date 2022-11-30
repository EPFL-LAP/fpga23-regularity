import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--data_dir")

args = parser.parse_args()

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

##########################################################################
def parse_log(log):
    """Parses a VPR log to determine when routing succeeded.

    Parameters
    ----------
    log : str
        Name of the log file.

    Returns
    -------
    int
        Iteration of success. None if routing failed.
    """

    with open(log, "r") as inf:
        lines = inf.readlines()

    total = -1
    succeeded = False
    for line in lines:
        if line.startswith("Router Stats:"):
            total = int(line.split("total_connections_routed: ", 1)[1].split(" total", 1)[0])
        if "Successfully routed after" in line and "routing iterations" in line:
            succeeded = True
    return total, succeeded


    for line in lines:
        if "Successfully routed after" in line and "routing iterations" in line:
            return int(line.split()[-3])
        if line.lstrip().startswith("300"):
            print log
            return str(line.split()[9][:-1])

    return None 
##########################################################################
os.chdir(args.data_dir)
arc_iters = []
for b in sorted(grid_sizes):
    arc_iters.append(parse_log("vpr_%s_19225.log" % b))

print arc_iters
