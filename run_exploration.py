import argparse
import copy
import os

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

param_combs = {
                "unconstrained" : {"ENFORCE_HOP_OPTIMALITY"       : False,\
                                   "ENFORCE_FANIN"                : False,\
                                   "ENFORCE_FANOUT"               : False,\
                                   "ENFORCE_EXTERNAL_SYMMETRY"    : False,\
                                   "ENFORCE_INTERNAL_SYMMETRY"    : False,\
                                   "ENFORCE_CONTINUATION"         : False,\
                                   "ENFORCE_RELAXED_CONTINUATION" : False,\
                                   "ENFORCE_TWO_TURNS"            : False,\
                                   "ENFORCE_ONE_TURN"             : False,\
                                   "LIMIT_MUX_SIZE_NUMBER"        : -1,\
                                   "LIMIT_FANOUT_SIZE_NUMBER"     : -1,\
                                   "ENFORCE_MUX_PAIR_INPUT_SHARE" : -1,\
                                   "WL_TRADEOFF"                  : 0.0,\
                                   "FLOORPLAN_SEED"               : 19225,\
                                  }
              }

#Limiting mux size number:
for name, cnt in (("one", 1), ("two", 2), ("four", 4)):
    param_combs.update({"%s_mux_size" % name : copy.deepcopy(param_combs["unconstrained"])})
    param_combs["%s_mux_size" % name].update({"LIMIT_MUX_SIZE_NUMBER" : cnt})
########################

#Limiting mux and fanout size number:
for name, cnt in (("one", 1), ("two", 2), ("four", 4)):
    param_combs.update({"%s_fanout_size" % name : copy.deepcopy(param_combs["%s_mux_size" % name])})
    param_combs["%s_fanout_size" % name].update({"LIMIT_FANOUT_SIZE_NUMBER" : cnt})
########################

#Enforcing mux pair input sharing:
for name, cnt in (("one", 1), ("two", 2), ("three", 3), ("four", 4), ("five", 5)):
    param_combs.update({"%s_input_shared" % name : copy.deepcopy(param_combs["one_fanout_size"])})
    param_combs["%s_input_shared" % name].update({"ENFORCE_MUX_PAIR_INPUT_SHARE" : cnt})
    param_combs["%s_input_shared" % name].update({"ENFORCE_FANIN" : True})
    param_combs["%s_input_shared" % name].update({"ENFORCE_FANOUT" : True})
########################

#Optimizing wirelength:
for wl in (0.1, 0.3, 0.5, 0.7, 0.9):
    param_combs.update({"wl_%.1f" % wl : copy.deepcopy(param_combs["unconstrained"])})
    param_combs["wl_%.1f" % wl].update({"WL_TRADEOFF" : wl})
    param_combs["wl_%.1f" % wl].update({"ENFORCE_FANIN" : True})
    param_combs["wl_%.1f" % wl].update({"ENFORCE_FANOUT" : True})
########################

#Enforcing turns and symmetries:
param_combs.update({"all_turns" : copy.deepcopy(param_combs["wl_0.5"])})
param_combs["all_turns"].update({"ENFORCE_TWO_TURNS" : True, "ENFORCE_RELAXED_CONTINUATION" : True})
param_combs["all_turns"].update({"ENFORCE_FANIN" : True})
param_combs["all_turns"].update({"ENFORCE_FANOUT" : True})

param_combs.update({"internal_symmetry" : copy.deepcopy(param_combs["wl_0.5"])})
param_combs["internal_symmetry"].update({"ENFORCE_INTERNAL_SYMMETRY" : True})
param_combs["internal_symmetry"].update({"ENFORCE_FANIN" : True})
param_combs["internal_symmetry"].update({"ENFORCE_FANOUT" : True})

param_combs.update({"external_symmetry" : copy.deepcopy(param_combs["wl_0.5"])})
param_combs["external_symmetry"].update({"ENFORCE_EXTERNAL_SYMMETRY" : True})
param_combs["external_symmetry"].update({"ENFORCE_FANIN" : True})
param_combs["external_symmetry"].update({"ENFORCE_FANOUT" : True})

param_combs.update({"full_symmetry" : copy.deepcopy(param_combs["wl_0.5"])})
param_combs["full_symmetry"].update({"ENFORCE_INTERNAL_SYMMETRY" : True, "ENFORCE_EXTERNAL_SYMMETRY" : True})
param_combs["full_symmetry"].update({"ENFORCE_FANIN" : True})
param_combs["full_symmetry"].update({"ENFORCE_FANOUT" : True})
########################

#Enforcing hop-optimality:
param_combs.update({"hop_optimality" : copy.deepcopy(param_combs["one_fanout_size"])})
param_combs["hop_optimality"].update({"ENFORCE_HOP_OPTIMALITY" : True})
param_combs["hop_optimality"].update({"ENFORCE_FANIN" : True})
param_combs["hop_optimality"].update({"ENFORCE_FANOUT" : True})
########################

with open("src/generate_architecture/config.py", "r") as inf:
    default_txt = inf.read()

##########################################################################
def fill_in(comb):
    """Fills in a configuration file.

    Parameters
    ----------
    comb : str
        Name of the combination as stored in the param_combs dictionary.

    Returns
    -------
    str
        Filled-in configuration.
    """

    txt = ""
    for line in default_txt.splitlines():
        replaced = False
        for key, val in param_combs[comb].items():
            if line.startswith("%s " % key):
                new_line = line.replace("= %s" % line.split('=', 1)[-1].split()[0], "= %s" % str(val))
                txt += new_line + "\n"
                replaced = True
                break
        if not replaced:
            txt += line + "\n"

    return txt
##########################################################################

with open("src/setenv.py", "r") as inf:
    setenv_txt = inf.read()


# WL = 1.0 does not require running avalanche routing. Hence just modify the floorplan seed and solve the ILPs:

run = lambda d : "cd run_exploration/%s/src/generate_architecture/ && python -u ilp_setup.py --config config --vpr_log sample_vpr.log && mkdir ../test_%s && cp sample_ilp.log ../test_%s/ilp_iter_1.log && cp sample_ilp.log ../test_%s/ilp_iter_2.log && rm sample_ilp.log" % (d, d, d, d)

for seed in (19225, 25124, 43033, 50936, 5300):
    key = "wl_1.0_%d" % seed
    comb = copy.deepcopy(param_combs["wl_0.1"])
    comb["WL_TRADEOFF"] = 1.0
    comb["FLOORPLAN_SEED"] = seed
    param_combs.update({key : comb})
    txt = fill_in(key)
    del param_combs[key]
    os.system("mkdir run_exploration/wl_1.0_shuffle_seed_%d" % seed) 
    os.system("cp -r src run_exploration/wl_1.0_shuffle_seed_%d/" % seed)
    with open("run_exploration/wl_1.0_shuffle_seed_%d/src/generate_architecture/config.py" % seed, "w") as outf:
       outf.write(txt)
    with open("run_exploration/wl_1.0_shuffle_seed_%d/src/setenv.py" % seed, "w") as outf:
       outf.write(setenv_txt.replace("%SHUFFLE_SEED%", str(seed)))
    os.system(run("wl_1.0_shuffle_seed_%d" % seed))

for comb in param_combs:
    txt = fill_in(comb)
    for seed in (19225, 25124, 43033, 50936, 5300):
        os.system("mkdir run_exploration/%s_shuffle_seed_%d" % (comb, seed))
        os.system("cp -r src run_exploration/%s_shuffle_seed_%d/" % (comb, seed))
        with open("run_exploration/%s_shuffle_seed_%d/src/generate_architecture/config.py" % (comb, seed), "w") as outf:
            outf.write(txt)
        with open("run_exploration/%s_shuffle_seed_%d/src/setenv.py" % (comb, seed), "w") as outf:
            outf.write(setenv_txt.replace("%SHUFFLE_SEED%", str(seed)))

run = lambda d : "cd run_exploration/%s/src/generate_architecture/ && python -u explore_avalanche.py --base_cost 1.0 --scaling_factor 9 --avalanche_iter 25 --adoption_threshold 1.1 --wd test_%s" % (d, d)

all_dirs = sorted(os.listdir("run_exploration"))
calls = []
for d in all_dirs:
    if "wl_1.0" in d:
        continue
    calls.append(run(d))

runner = Parallel(max_cpu, sleep_interval)
runner.init_cmd_pool(calls)
runner.run()

del runner

#Run the reference avalanche-search-only experiments:

comb = "avalanche_only"
calls = []
for seed in (19225, 25124, 43033, 50936, 5300):
    os.system("mkdir run_exploration/%s_shuffle_seed_%d" % (comb, seed))
    os.system("cp -r src run_exploration/%s_shuffle_seed_%d/" % (comb, seed))
    with open("run_exploration/%s_shuffle_seed_%d/src/setenv.py" % (comb, seed), "w") as outf:
        outf.write(setenv_txt.replace("%SHUFFLE_SEED%", str(seed)))
    calls.append(run("%s_shuffle_seed_%d" % (comb, seed)).replace("explore_avalanche.py", "explore_avalanche_no_ilp.py"))

runner = Parallel(max_cpu, sleep_interval)
runner.init_cmd_pool(calls)
runner.run()
