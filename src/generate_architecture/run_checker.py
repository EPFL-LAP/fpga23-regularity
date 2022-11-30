import os
import check_rr_graph

arc_name = "agilex"
grid_sizes = {"alu4" : 15, "ex5p" : 12, "tseng" : 13}
benchmarks = ["alu4", "ex5p", "tseng"]
init = True

os.chdir("../debug_wafer/")

print "WARNING: RR-graph checks work only for individual FPGAs, not wafers."
print "Runing checks on individual FPGAs. Pre-VPR RR-graphs will have to be used."
rr_names = ["%s_W%d_H%d_rr.xml" % (arc_name, grid_sizes[b], grid_sizes[b]) for b in benchmarks]
for rr_name in rr_names:
    print "Checking %s..." % rr_name
    reload(check_rr_graph)
    check_rr_graph.check_rr_all(rr_name, None if init else "stored_edges.save")

exit(0)

check_rr_graph.check_rr_all("../debug_wafer/agilex_W12_H12_rr.xml", None)#"../debug_wafer/stored_edges.save")

