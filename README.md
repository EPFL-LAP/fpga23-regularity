# Regularity Matters: Designing Practical FPGA Switch-Blocks

This repository holds the source code of the regular FPGA switch-block pattern exploration tool presented in the paper entitled "Regularity Matters: Designing Practical FPGA Switch-Blocks".
It is an extension of the ["Turning PathFinder Upside-Down: Exploring FPGA Switch-Blocks by Negotiating Switch Presence"](https://github.com/EPFL-LAP/fpl21-avalanche) paper.
The main difference is the addition of an ILP generator which models the various types of regularity constraints that have been explored. It can be found in [ilp_setup.py](https://github.com/EPFL-LAP/fpga23-regularity/blob/main/src/generate_architecture/ilp_setup.py).


## Setting up VPR (Exploration)

Extensions to VTR version 8.0 (the latest stable release at the time of writing the paper) are distributed as a patch in [vpr/exploration/vtr8_avalanche.patch](https://github.com/EPFL-LAP/fpga23-regularity/blob/main/vpr/exploration/vtr8_avalanche.patch).
Running [vpr/exploration/get_avalanche_vpr.sh](https://github.com/EPFL-LAP/fpga23-regularity/blob/main/vpr/exploration/get_avalanche_vpr.sh) from within that directory will download VTR 8.0 and apply the patch, after which VTR can be built as usual.
Automated file configuration assumes that VTR is deployed as a container as described in [vtr-verilog-to-routing/dev/DOCKER_DEPLOY.md](https://github.com/verilog-to-routing/vtr-verilog-to-routing/blob/e5ff75cc76f83ee2a7a5c4bbda0a278e6980239c/dev/DOCKER_DEPLOY.md).
However, with some slight modifications of the setenv.py files, this can be avoided.

## Setting up VPR (Testing)

In principle, postrouting results of testing the obtained architectures should not depend on the unused modifications of VPR. However, we have observed some slight variation between the build used for exploration (allows net order shuffling) and testing (does not allow net order shuffling). For exact reproduction of the results from the submitted version of the paper, we also provide a patch describing all the changes made to VPR in the test version. These can be found in [vpr/testing](https://github.com/EPFL-LAP/fpga23-regularity/blob/main/vpr/testing).

## Configuring Paths

Please edit the [paths.py](https://github.com/EPFL-LAP/fpga23-regularity/blob/main/paths.py) file according to your setup. Then run [configure.py](https://github.com/EPFL-LAP/fpga23-regularity/blob/main/configure.py) to apply the changes to all necessary files.



## SPICE Models (mandatory step)

Please follow the instructions from [EPFL-LAP/fpga21-scaled-tech](https://github.com/EPFL-LAP/fpga21-scaled-tech) to set up the SPICE models.

## Reproducing the Results

To reproduce the results of the paper, please follow the steps below.

1. `python run_exploration.py [--max_cpu NUM_CPU]`
2. `python cp_results.py`
3. `cd src/run_mcnc`
4. `python resize_all_grids.py [--max_cpu NUM_CPU]`
5. `python run_mcnc.py [--max_cpu NUM_CPU]`
6. `python run_gnl.py [--max_cpu NUM_CPU]`
7. `python collect_and_plot.py [--data_dir DATA_DIR]`

At the end of the process, plots from the paper should appear in the figs/ directory. Final exploration results, along with VPR logs and intermediate files will be in the cleaned_patterns/ directory.

## Using the Switch-Block Exploration Scripts

Using the scripts for performing an exploration other than the ones set up by run_exploration.py is achieved by navigating to src/generate_architectur/ and running the explore_avalanche.py script as described in [EPFL-LAP/fpl21-avalanche](https://github.com/EPFL-LAP/fpl21-avalanche). Constraint specification is done through the [config.py](https://github.com/EPFL-LAP/fpga23-regularity/blob/main/src/generate_architecture/config.py) file. Support for new constraint types can be added by modifying the [ilp_setup.py](https://github.com/EPFL-LAP/fpga23-regularity/blob/main/src/generate_architecture/ilp_setup.py) file. 

## Contact

If you find any bugs please open an issue. For all other questions, including getting access to the development branch, please contact Stefan Nikolic (firstname dot lastname at epfl dot ch).

