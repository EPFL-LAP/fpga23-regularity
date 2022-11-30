import os
import ast
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

if int(matplotlib.__version__[0]) < 2: 
        print "Please update matplotlib to version > 2.0 to get the appropriate subplot height ratios."

parser = argparse.ArgumentParser()
parser.add_argument("--data_dir")

args = parser.parse_args()

if args.data_dir is None:
    args.data_dir = os.path.abspath("../../cleaned_patterns/")

keys = ['all_turns', 'external_symmetry', 'five_input_shared', 'four_fanout_size', 'four_input_shared', 'four_mux_size', 'full_symmetry', 'hop_optimality', 'internal_symmetry', 'one_fanout_size', 'one_input_shared', 'one_mux_size', 'three_input_shared', 'two_fanout_size', 'two_input_shared', 'two_mux_size', 'unconstrained', 'wl_0.1', 'wl_0.3', 'wl_0.5', 'wl_0.7', 'wl_0.9', 'wl_1.0', 'avalanche_only']

mcnc_res_dict = {}
gnl_res_dict = {}
for key in keys:
    mcnc_res_dict.update({key : []})
    gnl_res_dict.update({key : []})
    for seed in (19225, 25124, 43033, 50936, 5300):
        os.system("python -u parse_delays.py --data_dir %s/%s_shuffle_seed_%d/sol_0/ > tmp.log" % (args.data_dir, key, seed))
        with open("tmp.log", "r") as inf:
            td = float(inf.readlines()[-1].strip())
        os.system("rm -f tmp.log")
        mcnc_res_dict[key].append(td)

        os.system("python -u parse_gnl_success.py --data_dir %s/%s_shuffle_seed_%d/sol_0/ > tmp.log" % (args.data_dir, key, seed))
        with open("tmp.log", "r") as inf:
            gnl = ast.literal_eval(inf.readlines()[-1].strip())
        os.system("rm -f tmp.log")
        gnl_res_dict[key].append(gnl)

fanin_impact = {\
    "order" : ["one_mux_size", "two_mux_size", "four_mux_size", "unconstrained", "avalanche_only"],\
    "labels" : ['1', '2', '4', r"$\infty$", "Avalanche only"],\
    "xs_key" : "one_mux_size",\
    "rotation" : 0,\
    "xlabel" : "\n# allowed different mux sizes",\
    "filename" : "figure_4.pdf",\
}

fanout_impact = {\
    "order" : ["one_fanout_size", "two_fanout_size", "four_fanout_size", "unconstrained", "avalanche_only"],\
    "labels" : ['1', '2', '4', r"$\infty$", "Avalanche only"],\
    "xs_key" : "one_fanout_size",\
    "rotation" : 0,\
    "xlabel" : "\n# allowed different mux and fanout sizes",\
    "filename" : "figure_7.pdf",\
}

sharing_impact = {\
    "order" : ["one_fanout_size", "one_input_shared", "two_input_shared", "three_input_shared", "four_input_shared", "five_input_shared"],\
    "labels" : ['0', '1', '2', '3', '4', '5'],\
    "xs_key" : "one_input_shared",\
    "rotation" : 0,\
    "xlabel" : "\n# shared inputs per mux pair (out of 6)",\
    "filename" : "figure_9.pdf",\
}

wl_impact = {\
    "order" : ["one_fanout_size", "wl_0.1", "wl_0.3", "wl_0.5", "wl_0.7", "wl_0.9", "wl_1.0"],\
    "labels" : ['0.0', '0.1', '0.3', '0.5', '0.7', '0.9', '1.0'],\
    "xs_key" : "wl_0.1",\
    "rotation" : 0,\
    "xlabel" : r"$\Lambda$",\
    "filename" : "figure_11.pdf",\
}

feature_impact = {\
    "order" : ["wl_0.5", "all_turns", "internal_symmetry", "external_symmetry", "full_symmetry"],\
    "labels" : ["reference", "all turns", "internal symmetry", "external symmetry", "full symmetry"],\
    "xs_key" : "wl_0.5",\
    "rotation" : 10,\
    "xlabel" : "",\
    "filename" : "figure_14.pdf",\
}

hop_optimality_impact = {\
    "order" : ["one_fanout_size", "hop_optimality"],\
    "labels" : ["reference", "hop optimality"],\
    "xs_key" : "one_fanout_size",\
    "rotation" : 0,\
    "xlabel" : "",\
    "filename" : "figure_16.pdf",\
}

fig_data = {"fanin_impact" : fanin_impact, "fanout_impact" : fanout_impact,\
            "sharing_impact" : sharing_impact, "wl_impact" : wl_impact,\
            "feature_impact" : feature_impact, "hop_optimality_impact" : hop_optimality_impact}

##########################################################################
def plot_mcnc(fig_key):
    """Plots an MCNC run figure.

    Parameters
    ----------
    fig_key : str
        Key indexing the figure data.

    Returns
    -------
    None
    """

    plt.ylim(1.37, 1.47)
    plt.yticks([1 + f / 100.0 for f in range(37, 47)])

    group_spacing = 10
    point_spacing = 1

    xs = [gcnt * group_spacing + pcnt * point_spacing for gcnt in range(0, len(fig_data[fig_key]["order"]))\
                                                      for pcnt in range(0, len(mcnc_res_dict[fig_data[fig_key]["xs_key"]]))]

    ys = []
    for key in fig_data[fig_key]["order"]:
        ys += sorted(mcnc_res_dict[key])

    plt.scatter(xs, ys)
    plt.xticks([gcnt * group_spacing + len(mcnc_res_dict[fig_data[fig_key]["xs_key"]]) / 2\
                     * point_spacing for gcnt in range(0, len(fig_data[fig_key]["order"]))],\
                fig_data[fig_key]["labels"], fontsize = 8, rotation = fig_data[fig_key]["rotation"])

    ax = plt.gca()
    for k, key in enumerate(fig_data[fig_key]["order"]):
        xlow = k * group_spacing
        width = len(mcnc_res_dict[key]) * point_spacing
        height = max(mcnc_res_dict[key]) - min(mcnc_res_dict[key])
        ylow = min(mcnc_res_dict[key])
    
        inc = 0.5 * point_spacing
        ax.add_patch(Rectangle((xlow - 1.5 * inc, ylow - 0.002), width + inc, height + 0.004, alpha=0.15))
    
        lxs = [xlow - 1.5 * inc, xlow - 1.5 * inc + width + inc]
        lys = [sum(mcnc_res_dict[key]) / float(len(mcnc_res_dict[key])), sum(mcnc_res_dict[key]) / float(len(mcnc_res_dict[key]))]
        plt.plot(lxs, lys, color="orange")
    
    plt.grid(visible = True, which = "both", axis = "y", color = "0.8", linewidth = "0.5")
    plt.ylabel("Geomean routed delay [ns]")
    
    plt.xlabel(fig_data[fig_key]["xlabel"])
    
    plt.tight_layout()
    plt.savefig("../../figs/%s" % fig_data[fig_key]["filename"])
    plt.close()
##########################################################################

##########################################################################
def plot_gnl(fig_key):
    """Plots a GNL run figure.

    Parameters
    ----------
    fig_key : str
        Key indexing the figure data.

    Returns
    -------
    None
    """

    keys = fig_data[fig_key]["order"]

    tds = {}
    res = {}
    for k, key in enumerate(keys):
        sorting = [n[1] for n in sorted([(sum([v[0] for v in gnl_res_dict[key][s]]), s) for s in range(0, len(gnl_res_dict[key]))])]
        sorted_res = []
        sorted_tds = []
        for s in range(0, len(gnl_res_dict[key])):
            sorted_res.append(gnl_res_dict[key][sorting[s]])
            sorted_tds.append(mcnc_res_dict[key][sorting[s]])
    
        tds.update({key : sorted_tds})
        res.update({key : sorted_res})
    
    group_spacing = 10
    point_spacing = 1

    xs = [gcnt * group_spacing + pcnt * point_spacing for gcnt in range(0, len(res)) for pcnt in range(0, len(res[fig_data[fig_key]["xs_key"]]))]
    
    max_succeeded = 0
    min_succeeded = float("inf")
    for key in res:
        for seed in res[key]:
            for cnt, success in seed:
                if success:
                    max_succeeded = max(max_succeeded, cnt)
                    min_succeeded = min(min_succeeded, cnt)
    
    expanded_xs = []
    for x in xs:
        for i in range(0, len(res[fig_data[fig_key]["xs_key"]][0])):
            expanded_xs.append(x)
    
    ys = []
    colors = []
    failures = []
    for key in keys:
        for i in range(0, len(res[key])):
            ys += sorted([v[0] / 1000.0 for v in res[key][i]])
            colors += ["blue" if vv[1] else "red" for vv in sorted([v for v in res[key][i]])]
            failures.append(len([v for v in res[key][i] if not v[1]]))
    
    flat_tds = []
    for k, key in enumerate(keys):
        flat_tds += tds[key]
   
    if int(matplotlib.__version__[0]) < 2: 
        fig, ax = plt.subplots(2, 1)
    else:
        fig, ax = plt.subplots(2, 1, gridspec_kw={'height_ratios': [4, 1]})
    
    for i, x in enumerate(xs):
        if False and x == 1:
            ax[0].text(x - 3.3, max_succeeded * 1.02 / 1000.0, "# circuits that failed to route (out of 10)" , fontsize=8)
        if failures[i]:
            ax[0].text(x - 0.3, max_succeeded * 1.02 / 1000.0, str(failures[i]), fontsize=9)
    
    
    ax[0].scatter(expanded_xs, ys, color = colors, alpha=0.3)
    ax[0].set_xticks([])
    
    ax[1].set_xticks([gcnt * group_spacing + len(res[fig_data[fig_key]["xs_key"]]) / 2 * point_spacing for gcnt in range(0, len(res))])
    ax[1].set_xticklabels(fig_data[fig_key]["labels"], fontsize = 8, rotation = fig_data[fig_key]["rotation"])
    
    ax[0].set_ylim(min_succeeded * 0.95 / 1000.0,  max_succeeded * 1.05 / 1000.0)
    
    ax[0].set_ylabel(r"Total connections routed [$10^3$]")
    ax[1].set_ylabel("Routed delay [ns]")
    
    
    for i in range(0, len(keys)):
        ax[1].scatter(xs[i * 5 : (i + 1) * 5], flat_tds[i * 5 : (i + 1) * 5], color = "blue")
    
    ax[0].grid(visible = True, which = "both", axis = "y", color = "0.8", linewidth = "0.5")
    
    plt.tight_layout()
    plt.savefig("../../figs/gnl_%s" % fig_data[fig_key]["filename"])
    plt.close()
##########################################################################

for fig in fig_data:
    plot_mcnc(fig)
    plot_gnl(fig)
