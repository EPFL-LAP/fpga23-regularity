"""Runs all the scripts necessary to plot Figures 11--13.
"""

import os

fig_11_header = "\"\"\"Holds the data necessary to produce Figure 11 of the paper.\n\"\"\"\n\n"
fig_11_footer = "curves = [c1, c2, c3, c4, c5, c6]"

fig_11_cmds = ["#Result of: python local_wires.py --K 6 --N 8 --tech 16 --density 0.5 --all_endpoints 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 7 --density 0.5 --all_endpoints 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 5 --density 0.5 --all_endpoints 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 4 --density 0.5 --all_endpoints 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 3.0 --density 0.5 --all_endpoints 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 3.1 --density 0.5 --all_endpoints 1",\
              ]

fig_11_ins = [["c1 = (", ", \"F16\")\n\n"],\
              ["c2 = (", ", \"F7\")\n\n"],\
              ["c3 = (", ", \"F5\")\n\n"],\
              ["c4 = (", ", \"F4\")\n\n"],\
              ["c5 = (", ", \"F3a\")\n\n"],\
              ["c6 = (", ", \"F3b\")\n\n"],\
             ]

fig_12_header = "\"\"\"Holds the data necessary to produce Figure 12 of the paper.\n\"\"\"\n\n"
fig_12_footer = "curves = [c1, c2, c3, c4]"

fig_12_cmds = ["#Result of: python local_wires.py --K 6 --N 8 --tech 4 --density 0.5 --all_endpoints 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 4 --density 0.5 --all_endpoints 1 --insert_rep 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 4 --density 0.5 --all_endpoints 1 --insert_rep 1 --rep_at_lut_x 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 4 --density 0.5 --all_endpoints 1 --use_my 1",\
              ]

fig_12_ins = [["c1 = (", ", \"F4 Mx\")\n\n"],\
              ["c2 = (", ", \"F4 Mx with in-line repeaters\")\n\n"],\
              ["c3 = (", ", \"F4 Mx with repeaters at LUT output\")\n\n"],\
              ["c4 = (", ", \"F4 My long vertical line\")\n\n"],\
             ]

fig_13_header = "\"\"\"Holds the data necessary to produce Figure 13 of the paper.\n\"\"\"\n\n"
fig_13_footer = "curves = [c1, c2, c3, c4, c5, c6]"

fig_13_cmds = ["#Result of: python local_wires.py --K 6 --N 8 --tech 16 --density 0.5 --all_endpoints 1 --use_my 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 7 --density 0.5 --all_endpoints 1 --use_my 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 5 --density 0.5 --all_endpoints 1 --use_my 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 4 --density 0.5 --all_endpoints 1 --use_my 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 3.0 --density 0.5 --all_endpoints 1 --use_my 1",\
               "#Result of: python local_wires.py --K 6 --N 8 --tech 3.1 --density 0.5 --all_endpoints 1 --use_my 1",\
              ]

fig_13_ins = [["c1 = (", ", \"F16\")\n\n"],\
              ["c2 = (", ", \"F7\")\n\n"],\
              ["c3 = (", ", \"F5\")\n\n"],\
              ["c4 = (", ", \"F4\")\n\n"],\
              ["c5 = (", ", \"F3a\")\n\n"],\
              ["c6 = (", ", \"F3b\")\n\n"],\
             ]

##########################################################################
def call(header, footer, cmds, inserts, filename):
    """Calls the appropriate scripts and stores the output in the appropriate form.

    Parameters
    ----------
    header : str
        Store file header.
    footer : str
        Store file footer.
    cmds : List[str]
        A list of scripts to call.
    inserts : List[List[str]]
        A list of string pairs which whould surround the script output.
    filename : str
        Name of the store file.

    Returns
    -------
    None
    """

    txt = header
    for i, cmd in enumerate(cmds):
        os.system("python -u %s > dump" % cmd.split("python ", 1)[1])
        txt += cmd + "\n"
        with open("dump", "r") as inf:
            res = inf.readlines()[-1].strip()
        os.system("rm -f dump")
        txt += ''.join([inserts[i][0]] + [res] + [inserts[i][1]])
    txt += footer

    with open(filename, "w") as outf:
        outf.write(txt)
##########################################################################

call(fig_11_header, fig_11_footer, fig_11_cmds, fig_11_ins, "figure_11.py")
call(fig_12_header, fig_12_footer, fig_12_cmds, fig_12_ins, "figure_12.py")
call(fig_13_header, fig_13_footer, fig_13_cmds, fig_13_ins, "figure_13.py")
