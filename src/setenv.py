"""Sets the necessary environment variables, for calling HSPICE and VPR.
"""

import os

#HSPICE command
os.environ["HSPICE"] = "/edadk/bin/eda snps hspice64" 

#VPR command
os.environ["VPR_RUN_PATH"] = "/home/snikolic/FPGA23/vtr-verilog-to-routing-8.0.0/%s/"
os.environ["CLEAR_VPR_RUN"] = "rm -rf /home/snikolic/FPGA23/vtr-verilog-to-routing-8.0.0/%s/*"
os.environ["VPR"] = "docker exec pedantic_kirch /bin/bash -c \"cd /workspace/%s/ && ../build/vpr/vpr %s --random_sort_nets true --random_sort_nets_seed %SHUFFLE_SEED%\"" 

#Maximum parallel number of HSPICE jobs (depends on both the number of cores and licenses)
os.environ["HSPICE_CPU"] = "20"

#Maximum number of parallel VPR and other non-SPICE jobs
os.environ["VPR_CPU"] = "47"
