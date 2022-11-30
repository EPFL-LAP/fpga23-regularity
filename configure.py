from paths import *

with open("src/setenv_template.py", "r") as inf:
    setenv_txt = inf.read()

setenv_txt = setenv_txt.replace("%%hspice_call%%", hspice_call)
setenv_txt = setenv_txt.replace("%%max_hspice_cpu%%", str(max_hspice_cpu))
setenv_txt = setenv_txt.replace("%%max_vpr_cpu%%", str(max_vpr_cpu))

exploration_txt = setenv_txt.replace("%%vpr_run_path%%", vpr_exploration_run_path)
exploration_txt = exploration_txt.replace("%%vpr_container%%", vpr_exploration_container)
with open("src/setenv.py", "w") as outf:
    outf.write(exploration_txt)

testing_txt = setenv_txt.replace("%%vpr_run_path%%", vpr_testing_run_path)
testing_txt = testing_txt.replace("%%vpr_container%%", vpr_testing_container)
elim = " --random_sort_nets true --random_sort_nets_seed %SHUFFLE_SEED%"
testing_txt = testing_txt.replace(elim, '').replace("exec", "exec -it")
with open("src/run_mcnc/setenv_testing.py", "w") as outf:
    outf.write(testing_txt)

with open("src/generate_architecture/config_template.py", "r") as inf:
    txt = inf.read()

txt = txt.replace("%%cplex_path%%", cplex_path)
with open("src/generate_architecture/config.py", "w") as outf:
    outf.write(txt)
