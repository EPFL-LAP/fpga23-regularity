"""Please specify the necessary paths below."""

#Full HSPICE call:
hspice_call = "/edadk/bin/eda snps hspice64"

#Full CPLEX path:
cplex_path = "/home/snikolic/CPLEX_Studio1210/cplex/bin/x86-64_linux/cplex"

#Absolute path of VPR installation (exploration build):
vpr_exploration_run_path = "/home/snikolic/FPGA23/vtr-verilog-to-routing-8.0.0/"

#Name of the VPR Docker container (exploration build):
vpr_exploration_container = "pedantic_kirch"
#It is assumed that the volume is mounted at >>workspace<<, as in official VTR build instructions.

#Absolute path of VPR installation (testing build):
vpr_testing_run_path = "/home/snikolic/FPL21/vtr-verilog-to-routing-8.0.0/"

#Name of the VPR Docker container (testing build):
vpr_testing_container = "upbeat_wiles"
#It is assumed that the volume is mounted at >>workspace<<, as in official VTR build instructions.

#Maximum parallel number of HSPICE jobs (depends on both the number of cores and licenses):
max_hspice_cpu = 20

#Maximum number of parallel VPR and other non-SPICE jobs:
max_vpr_cpu = 47
