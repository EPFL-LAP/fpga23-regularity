"""Sets the necessary environment variables, for calling HSPICE and VPR.
"""

import os

#HSPICE command
os.environ["HSPICE"] = "%%hspice_call%%" 

#VPR command
os.environ["VPR_RUN_PATH"] = "%%vpr_run_path%%%s/"
os.environ["CLEAR_VPR_RUN"] = "rm -rf %%vpr_run_path%%%s/*"
os.environ["VPR"] = "docker exec %%vpr_container%% /bin/bash -c \"cd /workspace/%s/ && ../build/vpr/vpr %s --random_sort_nets true --random_sort_nets_seed %SHUFFLE_SEED%\"" 

#Maximum parallel number of HSPICE jobs (depends on both the number of cores and licenses)
os.environ["HSPICE_CPU"] = "%%max_hspice_cpu%%"

#Maximum number of parallel VPR and other non-SPICE jobs
os.environ["VPR_CPU"] = "%%max_vpr_cpu%%"
