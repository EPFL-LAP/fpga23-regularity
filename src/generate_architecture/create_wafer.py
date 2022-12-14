"""Merges several FPGAs into one wafer on which designs can be simultaneously routed, independent of
one another.

Parameters
----------
arc : str
    Name of the architecture file to be used in the wafer.
tech : str
    Technology node.
wafer_w : int
    Width of the wafer matrix.
wafer_h : int
    Height of the wafer matrix.
fpga_sizes : Optional[str], default = None
    Comma-separated list of FPGA sizes to be included in the wafer.
    If not specified, the matrix is generated by replicating the original
    architecture.
wire_file : Optional[str], default = None
    The wire specification file. Only needed if internal resizing is being done.
padding_file : Optional[str], default = None
    The padding log file. Only needed if internal resizing is being done.
first_clique_iter : Optional[int], default = None
    Specifies if the FPGA resizer should be called in the firts clique search iteration mode.
circs : str
    A list of (circuit, placement seed) pairs to be implemented in the wafer.
merge_circs : Optional[bool], default = False
    Instructs the script to perform circuit merging. Otherwise, only the architecture
    and the RR-graph are merged. Since we use precomputed optimistic placement delay matrices,
    both packing and placement are invariant to SB-pattern changes and should be computed only
    once per channel segmentation.
replace_circs_only : Optional[bool], default = False
    Instructs the script to only replace the circuits, without regenerating the wafer.
adoption_threshold : Optional[float], default = 1.2
    Threshold for utilization drop above which all switches are adopted into the pattern.

Returns
-------
None
"""

import time
import os
import argparse
import hashlib
from ast import literal_eval

parser = argparse.ArgumentParser()
parser.add_argument("--arc")
parser.add_argument("--tech")
parser.add_argument("--wafer_w")
parser.add_argument("--wafer_h")
parser.add_argument("--fpga_sizes")
parser.add_argument("--wire_file")
parser.add_argument("--padding_file")
parser.add_argument("--first_clique_iter")
parser.add_argument("--circs")
parser.add_argument("--merge_circs")
parser.add_argument("--replace_circs_only")
parser.add_argument("--adoption_threshold")

args = parser.parse_args()

circs = literal_eval(args.circs)

MERGE_CIRCS = False
try:
    MERGE_CIRCS = int(args.merge_circs)
except:
    pass

grid_w = -1
grid_h = -1

FPGA_SIZES = None
try:
    FPGA_SIZES = sorted([int(s) for s in args.fpga_sizes.split(',')])
except:
    pass

if FPGA_SIZES == None:
    wafer_w = int(args.wafer_w)
    wafer_h = int(args.wafer_h)
else:
    wafer_h = 1
    wafer_w = len(FPGA_SIZES)

REPLACE_CIRCS_ONLY = False
try:
    REPLACE_CIRCS_ONLY = int(args.replace_circs_only)
except:
    pass

get_attr = lambda line, attr : line.split("%s=\"" % attr)[1].split('"')[0]

##########################################################################
def get_fpga_dimensions(filename):
    """Returns the dimensions of an FPGA.

    Parameters
    ----------
    filename : str
        Name of the file holding the architecture description.

    Returns
    -------
    Tuple[int]
        Grid width and height.
    """

    with open(filename, "r") as inf:
        lines = inf.readlines()

    for line in lines:
        if "<fixed_layout" in line:
            return int(get_attr(line, "width")), int(get_attr(line, "height"))
##########################################################################

##########################################################################
def resize_fpgas():
    """Generates FPGAs of all needed sizes, if they do not exist already.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    if FPGA_SIZES is None:
        return

    arc_gen_switches = ["--K 6",\
                        "--N 8",\
                        "--density 0.5",\
                        "--tech %s" % args.tech,\
                        "--physical_square 1",\
                        "--wire_file %s" % args.wire_file,\
                        "--change_grid_dimensions %s" % args.arc,\
                        "--import_padding %s" % args.padding_file,\
                        "--make_sb_clique 1",\
                        "--first_clique_iter %s" % args.first_clique_iter,\
                        "--no_stored_unused_edge_increase 1",\
                       ]

    if args.adoption_threshold is not None:
        arc_gen_switches += ["--adoption_threshold %f" % float(args.adoption_threshold)]


    name_template = args.arc.rsplit(".xml", 1)[0] + "_W%d_H%d.xml"
    rr_template = args.arc.rsplit(".xml", 1)[0] + "_W%d_H%d_rr.xml"
    for size in FPGA_SIZES:
        name = name_template % (size, size)
        arc_gen_args = ["--arc_name %s_W%d_H%d.xml" % (args.arc.rsplit(".xml", 1)[0], size, size),\
                        "--grid_w %d" % size,\
                        "--grid_h %d" % size\
                       ]
        arc_gen_call = ' '.join(["python -u arc_gen.py"] + arc_gen_switches + arc_gen_args)
        os.system(arc_gen_call)
        os.system("lz4 -d %s.lz4" % (rr_template % (size, size)))
##########################################################################

##########################################################################
def merge_arcs(filename, out_filename):
    """Merges the architecture descriptions into a wafer.

    Parameters
    ----------
    filename : str
        Name of the architecture file.
    out_filename : str
        Name of the file in which to store the wafer.

    Returns
    -------
    str
        SHA256 hash of the merged architecture file.
    """

    with open(filename, "r") as inf:
        lines = inf.readlines()

    header = []
    rd_header = True
    for lcnt, line in enumerate(lines):
        if "<layout>" in line:
            rd_header = False
        elif "<fixed_layout" in line:
            global grid_w
            grid_w = int(get_attr(line, "width"))
            global grid_h
            grid_h = int(get_attr(line, "height"))
        elif "</layout>" in line:
            break
        if rd_header:
            header.append(line)

    header = ''.join(header)
    body = ''.join(lines[(lcnt + 1):])

    indent = "    "
    io_template = 3 * indent + "<single type=\"io\" x=\"%d\" y=\"%d\" priority=\"100\"/>\n"
    corner_template = 3 * indent + "<single type=\"EMPTY\" x=\"%d\" y=\"%d\" priority=\"101\"/>\n"
    single_declarations = []

    if FPGA_SIZES is None:
        io_cols = []
        x_offset = 0
        for i in range(0, wafer_w):
            io_cols.append(x_offset + 0)
            io_cols.append(x_offset + grid_w - 1)
            x_offset += grid_w
    
        io_rows = []
        y_offset = 0
        for i in range(0, wafer_h):
            io_rows.append(y_offset + 0)
            io_rows.append(y_offset + grid_h - 1)
            y_offset += grid_h
    
        for col in io_cols:
            for y in range(0, grid_h * wafer_h):
                if y in io_rows:
                    single_declarations.append(corner_template % (col, y))
                else:
                    single_declarations.append(io_template % (col, y))
    
        for row in io_rows:
            for x in range(1, grid_w * wafer_w):
                single_declarations.append(io_template % (x, row))
        
        total_w = grid_w * wafer_w
        total_h = grid_h * wafer_h
    else:
        dimensions = [tuple(get_fpga_dimensions("%s_W%d_H%d.xml" % (args.arc.rsplit(".xml", 1)[0], s, s)))
                      for s in FPGA_SIZES]
        total_w = sum([s[0] for s in dimensions])
        total_h = max([s[1] for s in dimensions])

        x_offset = y_offset = 0
        for grid_w, grid_h in dimensions:
            corners = [(0, 0), (0, grid_h - 1), (grid_w - 1, 0), (grid_w - 1, grid_h - 1)]
            for x in range(0, grid_w):
                for y in range(0, total_h):
                    if y >= grid_h or (x, y) in corners:
                        single_declarations.append(corner_template % (x_offset + x, y))
                    elif (x in (0, grid_w - 1)) or (y in (0, grid_h - 1)):
                        single_declarations.append(io_template % (x_offset + x, y))
            x_offset += grid_w
                    
    layout = indent + "<layout>\n"
    layout += 2 * indent + "<fixed_layout name=\"fix\" width=\"%d\" height=\"%d\">\n"\
                              % (total_w, total_h)
    layout += ''.join(single_declarations)
    layout += 3 * indent + "<fill type=\"clb\" priority=\"10\"/>\n"
    layout += 2 * indent + "</fixed_layout>\n"
    layout += indent + "</layout>\n"

    txt = header + layout + body
    with open(out_filename, "w") as outf:
        outf.write(txt)

    return hashlib.sha256(txt.encode()).hexdigest()
##########################################################################

##########################################################################
def translate_rr_graph(filename, x_offset, y_offset, init_node):
    """Translates the RR-graph of a single FPGA to be put on the wafer.

    Parameters
    ----------
    filename : str
        Name of the file containing the RR-graph.
    x_offset : int
        Horizontal shift of the RR-graph in the number of tiles.
    y_offset : int
        Vertical shift of the RR-graph in the number of tiles.
    init_node : int
        New first node count, to appear in the merged graph.

    Returns
    -------
    List[str]
        A list of all coordinate-dependant tags
        (channels, grid, rr_nodes, rr_edges).
    int
        Largest node id.
    """

    #------------------------------------------------------------------------#
    def translate_channels(lines, lcnt):
        """Parses and translates all channel declarations.

        Parameters
        ----------
        lines : List[str]
            Lines read from the RR-graph file.
        lcnt : int
            Number of the line from which to start searching for channels.

        Returns
        -------
        str
            Text of the translated x-channels.
        str
            Text of the translated y-channels.
        int
            Number of the first line right after the channels.
        """

        while True:
            if not "<channels>" in lines[lcnt]:
                lcnt += 1
                continue
            lcnt += 1
            break

        x_txt = ""
        y_txt = ""
        
        for l, line in enumerate(lines[lcnt:]):
            if "</channels>" in line:
                break
            elif "<channel" in line:
                continue
            elif "x_list" in line:
                old_y = int(line.split()[1].split('"')[1])
                new_y = old_y + y_offset
                x_line = line.replace(line.split()[1], "index=\"%d\"" % new_y) 
                x_txt += x_line
            elif "y_list" in line:
                line = line.replace(line.split()[1], "index=\"%d\""\
                     % (int(line.split()[1].split('"')[1]) + x_offset))
                y_txt += line

        return x_txt, y_txt, lcnt + l + 1
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def translate_grid(lines, lcnt):
        """Parses and translates all grid entries.

        Parameters
        ----------
        lines : List[str]
            Lines read from the RR-graph file.
        lcnt : int
            Number of the line from which to start searching for the grid.

        Returns
        -------
        str
            Text of the translated grid.
        int
            Number of the first line right after the grid.
        """

        while True:
            if not "<grid>" in lines[lcnt]:
                lcnt += 1
                continue
            lcnt += 1
            break

        txt = ""
        empty_line = None
        for l, line in enumerate(lines[lcnt:]):
            if "</grid>" in line:
                break
            line = line.replace(line.split()[1], "x=\"%d\""\
                 % (int(line.split()[1].split('"')[1]) + x_offset))
            line = line.replace(line.split()[2], "y=\"%d\""\
                 % (int(line.split()[2].split('"')[1]) + y_offset))
            txt += line
            if empty_line is None:
                empty_line = line

        if FPGA_SIZES is not None:
            dimensions = [tuple(get_fpga_dimensions("%s_W%d_H%d.xml" % (args.arc.rsplit(".xml", 1)[0], s, s)))
                          for s in FPGA_SIZES]
            total_w = sum([s[0] for s in dimensions])
            total_h = max([s[1] for s in dimensions])
            grid_w, grid_h = dimensions[FPGA_SIZES.index(int(filename.split("_H")[1].split("_rr.xml")[0]))]
            for y in range(grid_h, total_h):
                for x in range(0, grid_w):
                    line = empty_line.replace(empty_line.split()[1], "x=\"%d\""\
                         % (x + x_offset))
                    line = line.replace(empty_line.split()[2], "y=\"%d\"" % y)
                    txt += line

        return txt, lcnt + l + 1
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def translate_node(lines, lcnt):
        """Parses and translates a single node.

        Parameters
        ----------
        lines : List[str]
            Lines read from the RR-graph file.
        lcnt : int
            Number of the start line of the node to be parsed.

        Returns
        -------
        str
            Text of the translated node.
        int
            Number of the first line right after the node.
        int
            New ID of the parsed node.
        """

        get_attr_word = lambda line, attr : [w for w in line.split() if "%s=\"" % attr in w][0]\
                                            if "%s=\"" % attr in line else None

        #........................................................................#
        def advance(line, attrs, inc):
            """Advances line updating by one line.

            Parameters
            ----------
            line : str
                Line to be modified.
            attr : List[str]
                Attributes to be changed.
            inc : List[int]
                Values by which to increase the attributes.

            Returns
            -------
            str
                The updated line.
            """
      
            if attrs is None:
                return line

            for i, attr in enumerate(attrs):
                attr_word = get_attr_word(line, attr)
                line = line.replace(attr_word, "%s=\"%d\"" % (attr, int(attr_word.split('"')[1]) + inc[i]))
            
            return line
        #........................................................................#

        attrs = [["id"], ["xlow", "ylow", "xhigh", "yhigh"], None, None]\
              + ([None] if "CHAN" in lines[lcnt] else [])
        inc = [[init_node], [x_offset, y_offset, x_offset, y_offset], 0, 0]\
            + ([0] if "CHAN" in lines[lcnt] else [])
    
        endlcnt = lcnt + len(attrs)
        node_lines = [advance(line, attrs[l], inc[l]) for l, line in enumerate(lines[lcnt : endlcnt])] 
        node_cnt = int(get_attr(node_lines[0], "id"))

        return ''.join(node_lines), endlcnt, node_cnt
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def translate_nodes(lines, lcnt):
        """Parses and translates all nodes.

        Parameters
        ----------
        lines : List[str]
            Lines read from the RR-graph file.
        lcnt : int
            Number of the line from which to start searching for nodes.

        Returns
        -------
        str
            Text of the translated nodes.
        int
            Number of the first line right after the nodes.
        int
            Largest node ID.
        """

        while True:
            if not "<rr_nodes>" in lines[lcnt]:
                lcnt += 1
                continue
            lcnt += 1
            break

        max_node_cnt = -1
        txt = ""
        while True:
            if "</rr_nodes>" in lines[lcnt]:
                break
            node, lcnt, node_cnt = translate_node(lines, lcnt)
            txt += node
            max_node_cnt = max(max_node_cnt, node_cnt)

        return txt, lcnt, max_node_cnt
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def translate_edges(lines, lcnt):
        """Parses and translates all edges.

        Parameters
        ----------
        lines : List[str]
            Lines read from the RR-graph file.
        lcnt : int
            Number of the line from which to start searching for edges.

        Returns
        -------
        str
            Text of the translated edges.
        int
            Number of the first line right after the edges.
        """

        while True:
            if not "<rr_edges>" in lines[lcnt]:
                lcnt += 1
                continue
            lcnt += 1
            break

        txt = ""
        for l, line in enumerate(lines[lcnt:]):
            if "</rr_edges>" in line:
                break
            line = line.replace(line.split()[1], "src_node=\"%d\""\
                 % (int(line.split()[1].split('"')[1]) + init_node))
            line = line.replace(line.split()[2], "sink_node=\"%d\""\
                 % (int(line.split()[2].split('"')[1]) + init_node))
            txt += line
            
        return txt, lcnt + l + 1
    #------------------------------------------------------------------------#

    with open(filename, "r") as inf:
        lines = inf.readlines()

    x_chans, y_chans, lcnt = translate_channels(lines, 0)
    grid, lcnt = translate_grid(lines, lcnt)
    nodes, lcnt, max_node_cnt = translate_nodes(lines, lcnt)
    edges, lcnt = translate_edges(lines, lcnt)

    return x_chans, y_chans, grid, nodes, edges, max_node_cnt
##########################################################################

##########################################################################
def merge_rr_graphs(filename, out_filename):
    """Merges the RR-graphs into a wafer.

    Parameters
    ----------
    filename : str
        Name of the RR-graph file.
    out_filename : str
        Name of the file in which to store the wafer.

    Returns
    -------
    None
    """

    with open(filename, "r") as inf:
        lines = inf.readlines()

    header = ''.join(lines[:3])
    invariant = "" 
    rd = False
    for line in lines:
        if "<switches>" in line:
            rd = True
        if rd:
            invariant += line
        if "</block_types>" in line:
            break

    all_chans = []
    all_grids = []
    all_nodes = []
    all_edges = []
    init_node = 0
   
    if FPGA_SIZES is None: 
        for x in range(0, wafer_w):
            for y in range(0, wafer_h):
                x_chans, y_chans, grid, nodes, edges, last_used_node\
                = translate_rr_graph(filename, x * grid_w, y * grid_h, init_node)
                init_node = last_used_node + 1
                all_chans.append(x_chans)
                all_chans.append(y_chans)
                all_grids.append(grid)
                all_nodes.append(nodes)
                all_edges.append(edges)
    else:
        dimensions = [tuple(get_fpga_dimensions("%s_W%d_H%d.xml" % (args.arc.rsplit(".xml", 1)[0], s, s)))
                      for s in FPGA_SIZES]
        x = y = 0
        for i, dim in enumerate(dimensions):
            print x, y
            w, h = dim
            local_filename = "%s_W%d_H%d_rr.xml" % (filename.rsplit("_rr.xml", 1)[0], FPGA_SIZES[i], FPGA_SIZES[i])
            x_chans, y_chans, grid, nodes, edges, last_used_node\
            = translate_rr_graph(local_filename, x, y, init_node)
            init_node = last_used_node + 1
            all_chans.append(x_chans)
            all_chans.append(y_chans)
            all_grids.append(grid)
            all_nodes.append(nodes)
            all_edges.append(edges)
            x += w

    all_chans = sorted(list(set(all_chans)), key = lambda c : (int(get_attr(c.splitlines()[0], "index")), c))

    indent = "    "
    txt = header
    txt += ''.join(all_chans)
    txt += indent + "</channels>\n"
    txt += invariant
    txt += indent + "<grid>\n"
    txt += ''.join(all_grids)
    txt += indent + "</grid>\n" 
    txt += indent + "<rr_nodes>\n"
    txt += ''.join(all_nodes)
    txt += indent + "</rr_nodes>\n"
    txt += indent + "<rr_edges>\n"
    txt += ''.join(all_edges)
    txt += indent + "</rr_edges>\n"
    txt += "</rr_graph>\n"

    with open(out_filename, "w") as outf:
        outf.write(txt)
##########################################################################

##########################################################################
def merge_circuits(circs, arc_filename, rr_filename, arc_hash):
    """Merges together blif files with appropriately renamed signals,
    produces packings and placements for each of them, and then merges them
    together as well.

    Parameters
    ----------
    circs : List[Tuple[str, int]]
        A list of (circ, seed) pairs to be merged.
    arc_filename : str
        Name of the architecture file that enters the wafer.
    rr_filename : str
        Name of the RR-graph file that enters the wafer.
    arc_hash : str
        SHA256 hash of the wafer architecture file.

    Returns
    -------
    None
    """

    #------------------------------------------------------------------------#
    def prefix_signals(circ, prefix):
        """Prefixes all signal identifiers in a circuit with a given prefix,
        so as to make different copies unique.

        Parameters
        ----------
        circ : str
            Name of the .blif file.
        prefix : str
            Prefix to be prepended to the signal names.
        
        Returns
        -------
        None
        """

        #........................................................................#
        def is_invariant(word):
            """Checks if the word is invariant. Invariant words are keywords and constants.
        
            Parameters
            ----------
            word : str
                Word to be checked.
            
            Returns
            -------
            bool
                True if the word is invariant, False otherwise.
            """

            #Keywords
            if word.startswith('.'):
                return True

            #Latch types
            if word in ("re", '2'):
                return True

            #Line continuation
            if word == "\\":
                return True

            if all(c in ('0', '1', '-') for c in word):
                return True

            return False
        #........................................................................#

        with open(circ, "r") as inf:
            lines = inf.readlines()

        txt = ""
        for line in lines:
            processed_words = []
            for w in line.split():
                if is_invariant(w):
                    processed_words.append(w)
                else:
                    processed_words.append("%s_%s" % (prefix, w))
            txt += ' '.join(processed_words) + "\n"

        with open("%s_%s.blif" % (circ.rsplit(".blif", 1)[0], prefix), "w") as outf:
            outf.write(txt[:-1])
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def produce_files(ind, x, y):
        """Calls VPR to produce the packing and placement files.
        
        Parameters
        ----------
        ind : int
            Index of the (circ, seed) pair.
        x : int
            Start column of the translated placement.
        y : int
            Start row of the translated placement.

        Returns
        -------
        None
        """

        local_arc_filename = arc_filename if FPGA_SIZES is None else\
                             "%s_W%d_H%d.xml" % (arc_filename.rsplit(".xml", 1)[0],\
                                                 FPGA_SIZES[ind], FPGA_SIZES[ind])
        local_rr_filename = rr_filename if FPGA_SIZES is None else\
                            "%s_W%d_H%d_rr.xml" % (rr_filename.rsplit("_rr.xml", 1)[0],\
                                                   FPGA_SIZES[ind], FPGA_SIZES[ind])

        circ, seed = circs[ind]
        delay_matrix = local_arc_filename.replace(".xml", "_placement_delay.matrix")
        prefix = "circ_%d" % ind
        wd = os.getcwd()
        os.system("mkdir %s" % prefix)

        run_req_files = ["base_costs.dump",\
                         circ,\
                         local_arc_filename,\
                         local_rr_filename,\
                         delay_matrix\
                        ]
    
        for f in run_req_files:
            os.system("cp %s %s/" % (f, prefix))
        os.chdir(prefix)

        prefix_signals(circ, prefix)
        os.system("rm -f %s" % circ)
        run_req_files.remove(circ)
        circ = "%s_%s.blif" % (circ.rsplit(".blif", 1)[0], prefix)
        run_req_files.append(circ)

        with open(local_rr_filename, "r") as inf:
            lines = inf.readlines()
            chan_w = int(get_attr(lines[2], "chan_width_max"))

        vpr_arguments = [local_arc_filename,\
                         circ\
                        ]

        vpr_switches = ["--pack",\
                        "--place",\
                        "--seed %d" % seed,\
                        "--import_place_delay_model %s" % delay_matrix,\
                        "--read_rr_graph %s" % local_rr_filename,\
                        "--route_chan_width %d" % chan_w\
                       ]

        sandbox = "sandbox_%s_%s" % (os.getcwd().replace('/', "__"), str(time.time()))
        os.system("mkdir %s" % (os.environ["VPR_RUN_PATH"] % sandbox))

        for f in run_req_files:
            os.system("cp %s %s/" % (f, os.environ["VPR_RUN_PATH"] % sandbox))

        vpr_call = "time %s" % (os.environ["VPR"] % (sandbox, ' '.join(vpr_arguments + vpr_switches)))
        os.system(vpr_call)
    
        for f in os.listdir(os.environ["VPR_RUN_PATH"] % sandbox):
            os.system("cp %s/%s ./" % (os.environ["VPR_RUN_PATH"] % sandbox, f))
    
        os.system("rm -rf %s" % (os.environ["VPR_RUN_PATH"] % sandbox))

        #........................................................................#
        def translate_placement():
            """Translates the placement coordinates.
            
            Parameters
            ----------
            None
            
            Returns
            -------
            None
            """

            placement_filename = circ.replace(".blif", ".place")
            with open(placement_filename, "r") as inf:
                lines = inf.readlines()
           
            txt = ""
            for line in lines:
                if line.startswith(prefix) or line.startswith("out:%s" % prefix):
                    words = line.split()
                    words[1] = str(int(words[1]) + x)
                    words[2] = str(int(words[2]) + y)
                    txt += "\t".join(words) + "\n"
                else:
                    txt += line

            with open(placement_filename, "w") as outf:
                outf.write(txt)
        #........................................................................#

        translate_placement()

        os.chdir(wd)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def merge_blifs():
        """Merges all blifs into a single file.

        Parameters
        ----------
        None
        
        Returns
        -------
        None
        """

        all_inputs = ""
        all_outputs = ""
        all_nets = ""
        for ind in range(0, len(circs)):
            circ, seed = circs[ind]
            prefix = "circ_%d" % ind
            blif_filename = "%s/%s_%s.blif" % (prefix, circ.rsplit(".blif", 1)[0], prefix)
            with open(blif_filename, "r") as inf:
                lines = inf.readlines()
            state = "idle"
            for line in lines[1:-1]:
                if line.startswith(".inputs"):
                    state = "ins"
                    all_inputs += line.split(".inputs")[1]
                    continue
                elif line.startswith(".outputs"):
                    state = "outs"
                    if ind < len(circs) - 1:
                        all_inputs = all_inputs[:-1] + " \\\n"
                    all_outputs += line.split(".outputs")[1]
                    continue
                elif state == "outs" and line.startswith('.'):
                    state = "nets"
                    if ind < len(circs) - 1:
                        all_outputs = all_outputs[:-1] + " \\\n"
                    all_nets += line
                    continue
                if state == "ins":
                    all_inputs += line
                elif state == "outs":
                    all_outputs += line
                elif state == "nets":
                    all_nets += line

        txt = ".model wafer_top\n"
        txt += ".inputs %s" % all_inputs
        txt += ".outputs %s" % all_outputs
        txt += "%s.end" % all_nets

        with open("wafer.blif", "w") as outf:
            outf.write(txt)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def merge_packings(arc_hash):
        """Merges all packed netlists into a single file.

        Parameters
        ----------
        arc_hash : str
            SHA256 hash of the wafer architecture file.
        
        Returns
        -------
        str
            SHA256 hash of the combined packing.
        """

        #........................................................................#
        def swap_instance(line, num):
            """Swaps the current instance number for the given number.

            Parameters
            ----------
            line : str
                Line to be modified.
            num : int
                The new instance number.
            
            Returns
            -------
            str
                The updated line.
            int
                The next instance number.
            """

            try:
                instance = get_attr(line, "instance")
            except:
                return line, num

            if instance.startswith("clb[") or instance.startswith("io["):
                line = line.replace(instance, instance.replace(instance.split('[')[1].split(']')[0], str(num)))
                return line, num + 1
            else:
                return line, num
        #........................................................................#

        all_inputs = ""
        all_outputs = ""
        all_clocks = ""
        all_blocks = ""
        instance_counter = 0
        for ind in range(0, len(circs)):
            inputs_read = outputs_read = clocks_read = False
            circ, seed = circs[ind]
            prefix = "circ_%d" % ind
            packing_filename = "%s/%s_%s.net" % (prefix, circ.rsplit(".blif", 1)[0], prefix)
            with open(packing_filename, "r") as inf:
                lines = inf.readlines()
            for line in lines[:-1]:
                if not inputs_read and "<inputs>" in line:
                    inputs_read = True
                    all_inputs += line.split('>')[1].split("</")[0] + ' '
                elif not outputs_read and "<outputs>" in line:
                    outputs_read = True
                    all_outputs += line.split('>')[1].split("</")[0] + ' '
                elif not clocks_read and "<clocks>" in line:
                    clocks_read = True
                    clocks = line.split('>')[1].split("</")[0]
                    if clocks:
                        all_clocks += clocks + ' '
                    continue
                if clocks_read:
                    line, instance_counter = swap_instance(line, instance_counter)
                    all_blocks += line

        txt = "<?xml version=\"1.0\"?>\n"
        txt += "<block name=\"wafer.net\" instance=\"FPGA_packed_netlist[0]\" architecture_id=\"SHA256:%s\">\n"\
             % arc_hash
        #NOTE: As of VTR8.0 atom_netlist_id hash is not required although VPR itself does generate it.

        indent = "    "
        txt += indent + "<inputs>%s</inputs>\n" % all_inputs[:-1]
        txt += indent + "<outputs>%s</outputs>\n" % all_outputs[:-1]
        txt += indent + "<clocks>%s</clocks>\n" % all_clocks[:-1]
        txt += all_blocks
        txt += "</block>"

        with open("wafer.net", "w") as outf:
            outf.write(txt)

        return hashlib.sha256(txt.encode()).hexdigest()
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def merge_placements(net_hash):
        """Merges all placements into a single file.

        Parameters
        ----------
        net_hash : str
            SHA256 hash of the combined packed netlist file.
        
        Returns
        -------
        str
            SHA256 hash of the combined placement.
        """

        block_coords = []
        for ind in range(0, len(circs)):
            circ, seed = circs[ind]
            prefix = "circ_%d" % ind
            placement_filename = "%s/%s_%s.place" % (prefix, circ.rsplit(".blif", 1)[0], prefix)
            with open(placement_filename, "r") as inf:
                lines = inf.readlines()
            for line in lines:
                if line.startswith(prefix) or line.startswith("out:%s" % prefix):
                    block_coords.append(line)
    
        if FPGA_SIZES is None:
            total_w = grid_w * wafer_w
            total_h = grid_h * wafer_h
        else:
            dimensions = [tuple(get_fpga_dimensions("%s_W%d_H%d.xml" % (args.arc.rsplit(".xml", 1)[0], s, s)))
                          for s in FPGA_SIZES]
            total_w = sum([s[0] for s in dimensions])
            total_h = max([s[1] for s in dimensions])

        txt = "Netlist_File: wafer.net Netlist_ID: SHA256:%s\n" % net_hash
        txt += "Array size: %d x %d logic blocks\n\n" % (total_w, total_h)
        
        txt += "#block name x\ty\tsubblk\tblock number\n"
        txt += "#----------	--\t--\t------\t------------\n"
        txt += ''.join(block_coords)

        with open("wafer.place", "w") as outf:
            outf.write(txt)

        return hashlib.sha256(txt.encode()).hexdigest()
    #------------------------------------------------------------------------#

    x = y = 0
    for ind in range(0, len(circs)):
        produce_files(ind, x, y)
        if FPGA_SIZES is None:
            x += 1
            if x >= wafer_w:
                x = 0
                y += 1
        else:
            x += tuple(get_fpga_dimensions("%s_W%d_H%d.xml" % (args.arc.rsplit(".xml", 1)[0],\
                                                               FPGA_SIZES[ind], FPGA_SIZES[ind])))[0]

    merge_blifs()
    net_hash = merge_packings(arc_hash)
    place_hash = merge_placements(net_hash)
##########################################################################

##########################################################################
def generate_sdc(circs):
    """Generates separate virtual clocks for IOs of all circuits.

    Parameters
    ----------
    circs : List[Tuple[str, int]]
        List of circuits, as for merge_circuits.

    Returns
    -------
    None
    """

    template = "create_clock -period 0 %s\n"\
             + "set_input_delay -clock %s -max 0 [get_ports {%s*}]\n"\
             + "set_output_delay -clock %s -max 0 [get_ports {%s*}]\n"\

    clks = []
    txt = ""
    for ind in range(0, len(circs)):
        circ, seed = circs[ind]
        prefix = "circ_%d" % ind
        packing_filename = "%s/%s_%s.net" % (prefix, circ.rsplit(".blif", 1)[0], prefix)
        with open(packing_filename, "r") as inf:
            lines = inf.readlines()
        clk = ''
        for line in lines:
            if "<clocks>" in line:
                clk = line.split('>')[1].split("</")[0]
                break
        if not clk:
            clk = "virtual_io_clock_%s" % prefix
            txt += template % ("-name " + clk, clk, prefix, clk, prefix)
        else:
            txt += template % (clk, clk, prefix, clk, prefix)
        clks.append(clk)

    if len(clks) > 1:
        txt += "set_clock_groups -exclusive %s" % (' '.join(["-group {%s}" % clk for clk in clks]))

    with open("wafer.sdc", "w") as outf:
        outf.write(txt)
##########################################################################

##########################################################################
def replace_hashes():
    """Replaces the hashes in the packed netlist and the placement files,
    as otherwise, when recomputation is not performed, VPR will crash.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    with open("wafer.xml", "r") as inf:
        txt = inf.read()

    arc_hash = hashlib.sha256(txt.encode()).hexdigest()
    
    with open("wafer.net", "r") as inf:
        lines = inf.readlines()

    lines[1] = lines[1].replace(lines[1].split()[-1], "architecture_id=\"SHA256:%s\">" % arc_hash)

    txt = ''.join(lines)
    with open("wafer.net", "w") as outf:
        outf.write(txt)

    net_hash = hashlib.sha256(txt.encode()).hexdigest()

    with open("wafer.place", "r") as inf:
        lines = inf.readlines()

    lines[0] = lines[0].replace(lines[0].split()[-1], "SHA256:%s" % net_hash)
    
    txt = ''.join(lines)
    with open("wafer.place", "w") as outf:
        outf.write(txt)
##########################################################################
        
##########################################################################
def rescale_avalanche_costs():
    """Scales down the avalanche costs by the number of FPGAs on the wafer.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    with open("base_costs.dump", "r") as inf:
        lines = inf.readlines()

    avalanche_p = float(lines[0].split()[0]) / (wafer_w * wafer_h)
    avalanche_h = float(lines[0].split()[1]) / (wafer_w * wafer_h)
    avalanche_d = float(lines[0].split()[2]) / (wafer_w * wafer_h)
    lines[0] = "%f %f %f\n" % (avalanche_p, avalanche_h, avalanche_d)

    txt = ''.join(lines)
    with open("base_costs.dump", "w") as outf:
        outf.write(txt)
##########################################################################

if not REPLACE_CIRCS_ONLY: 
    resize_fpgas()
    arc_filename = args.arc 
    rr_filename = arc_filename.rsplit(".xml", 1)[0] + "_rr.xml"

    arc_hash = merge_arcs(arc_filename, "wafer.xml")
    merge_rr_graphs(rr_filename, "wafer_rr.xml")
else:
    with open("wafer.xml", "r") as inf:
        arc_hash = hashlib.sha256(inf.read().encode()).hexdigest()

if MERGE_CIRCS:
    merge_circuits(circs, arc_filename, rr_filename, arc_hash)
    generate_sdc(circs)
else:
    replace_hashes()
