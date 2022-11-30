import time
import os
import argparse

TECH = '4'

parser = argparse.ArgumentParser()
parser.add_argument("--grid_w")
parser.add_argument("--grid_h")
parser.add_argument("--arc_name")
parser.add_argument("--arc_dir")
parser.add_argument("--run_dir")
parser.add_argument("--measure_delays")

args = parser.parse_args()

wd = os.getcwd()
src_dir = "%s/src/generate_architecture/" % args.run_dir
##########################################################################
def resize_arc(grid_w, grid_h, arc_name, out_arc_name):
    """Calls the architecture generation script.

    Parameters
    ----------
    grid_w : int
        Grid width. Might change due to physical length balancing.
    grid_h : int
        Grid height. Might change due to physical length balancing.
    arc_name : str
        Name of the architecture to be resized.
    out_arc_name : str
        Name of the output architecture.
       
    Returns
    -------
    None
    """

    #Default parameters:
    arc_to_resize = "%s.xml" % out_arc_name 
    wire_file = "%s.wire" % out_arc_name
    padding_file = "%s_padding.log" % out_arc_name
    pattern_file = "%s.pattern" % out_arc_name

    os.system("cp %s.xml %s%s" % (arc_name, src_dir, arc_to_resize))
    os.system("cp %s.wire %s%s" % (arc_name, src_dir, wire_file))
    os.system("cp %s_padding.log %s%s" % (arc_name, src_dir, padding_file))
    os.system("cp final.pattern %s%s" % (src_dir, pattern_file))

    os.chdir(src_dir)

    arc_gen_switches = ["--K 6",\
                        "--N 8",\
                        "--density 0.5",\
                        "--tech %s" % TECH,\
                        "--wire_file %s" % wire_file,\
                        "--import_padding %s" % padding_file,\
                        "--physical_square 1",\
                        "--arc_name %s.xml" % out_arc_name,\
                        "--grid_w %d" % grid_w,\
                        "--grid_h %d" % grid_h,\
                        "--load_pattern_from_file %s" % pattern_file,\
                       ]

    if args.measure_delays is None or int(args.measure_delays) == 0:
        arc_gen_switches.append("--change_grid_dimensions %s" % arc_to_resize)

    call = ' '.join(["time python -u %s/arc_gen.py" % src_dir] + arc_gen_switches)

    os.system(call)
##########################################################################

grid_w = int(args.grid_w)
grid_h = int(args.grid_h)

out_arc_name = "%s_%d_%d" % (args.arc_name, grid_w, grid_h)

os.chdir(args.run_dir)
target_dir = os.getcwd()

resize_arc(grid_w, grid_h, args.arc_name, out_arc_name)
os.system("mv %s* %s/" % (out_arc_name, target_dir))
os.chdir(wd)
#os.system("rm -rf %s/src/" % args.run_dir)
