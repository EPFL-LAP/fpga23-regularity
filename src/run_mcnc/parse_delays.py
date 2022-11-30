"""Parses the delays from the VPR logs.

Parameters
----------
data_dir : str
    Directory holding the logs.

Returns
-------
Dict[str, float]
    A dictionary of geomean postplacement delays.
Dict[str, float]
    A dictionary of geomean routed delays.
"""

import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--data_dir")

args = parser.parse_args()

wd = os.getcwd()

os.chdir(args.data_dir)

##########################################################################
def parse(log):
    """Parses the given log.

    Parameters
    ----------
    log : str
        Name of the log file.

    Returns
    -------
    Tuple(float, float)
        Postplacement and routed delays.
    """

    with open(log, "r") as inf:
        lines = inf.readlines()

    pwns = None
    rwns = None
    for line in lines:
        if "Placement estimated setup Worst Negative Slack" in line:
            pwns = -1 * float(line.split()[-2])
        elif "Final critical path:" in line:
            rwns = float(line.split()[3])
    if rwns is None:
        print log

    return pwns, rwns
##########################################################################

##########################################################################
def populate_dicts():
    """Populates both dictionaries with raw results.

    Parameters
    ----------
    None

    Returns
    -------
    Dict[str, Dict[int, float]]
        Posplacement delay dictionary.
    Dict[str, Dict[int, float]]
        Routed delay dictionary.
    """

    postplacement = {}
    routed = {}
    for f in os.listdir('.'):
        if f.startswith("vpr") and not "synth" in f:
            circ = f.split('_')[1]
            seed = int(f.split('_')[2].split('.')[0])
            pwns, rwns = parse(f)
            try:
                postplacement[circ].update({seed : pwns})
            except:
                postplacement.update({circ : {seed : pwns}})
            try:
                routed[circ].update({seed : rwns})
            except:
                routed.update({circ : {seed : rwns}})

    return postplacement, routed
##########################################################################

##########################################################################
def condense_dict(d):
    """Condenses the given dictionary by computing median values for all
    benchmarks and the overall geomean.

    Parameters
    ----------
    d : Dict[str, Dict[int, float]]
        A dictionary of delays.
    
    Returns
    -------
    Dict[str, float]
        A condensed version of the dictionrary.
    float
        Geomean delay.
    """

    median = {c : list(sorted(d[c].values()))[len(d[c]) / 2] for c in d}

    geomean = 1.0
    for c in median:
        geomean *= median[c]
    geomean = geomean ** (1.0 / len(median))

    
    return median, geomean
##########################################################################

postplacement, routed = populate_dicts()

postplacement_median, postplacement_geomean = condense_dict(postplacement)
routed_median, routed_geomean = condense_dict(routed)

print postplacement_median
print postplacement_geomean
print routed_median
print routed_geomean
