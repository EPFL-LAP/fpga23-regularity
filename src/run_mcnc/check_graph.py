filename = "full_ripup_avalanche_at_1.1/agilex_full_ripup_avalanche_at_1.1_5_5_rr.xml"

with open(filename, "r") as inf:
    lines = inf.readlines()

get_attr = lambda line, attr : line.split("%s=\"" % attr, 1)[1].split('"', 1)[0]

seg_ids = {'H' : '0', 'V' : '1'}
chan_nodes = {}
coord_lookup = {}
for lcnt, line in enumerate(lines):
    if "CHANX" in line:
        if get_attr(lines[lcnt + 3], "segment_id") != seg_ids['H']:
            print "Wrong segment id for H wire."
            raise ValueError
        low = (get_attr(lines[lcnt + 1], "xlow"), get_attr(lines[lcnt + 1], "ylow"))
        high = (get_attr(lines[lcnt + 1], "xhigh"), get_attr(lines[lcnt + 1], "yhigh"))
        if high != low:
            print "H wire different low and high coords."
            raise ValueError

        name = "H1R" if get_attr(line, "direction") == "INC_DIR" else "H1L"
        node_id = get_attr(line, "id")
        attr_dict = {node_id : name}
        coord_lookup.update({node_id : low})
        try:
            chan_nodes[low].update(attr_dict)
        except:
            chan_nodes.update({low : attr_dict})

    if "CHANY" in line:
        if get_attr(lines[lcnt + 3], "segment_id") != seg_ids['V']:
            print "Wrong segment id for V wire."
            raise ValueError
        low = (get_attr(lines[lcnt + 1], "xlow"), get_attr(lines[lcnt + 1], "ylow"))
        high = (get_attr(lines[lcnt + 1], "xhigh"), get_attr(lines[lcnt + 1], "yhigh"))
        if high != low:
            print "V wire different low and high coords."
            raise ValueError

        name = "V1U" if get_attr(line, "direction") == "INC_DIR" else "V1D"
        node_id = get_attr(line, "id")
        attr_dict = {node_id : name}
        coord_lookup.update({node_id : low})
        try:
            chan_nodes[low].update(attr_dict)
        except:
            chan_nodes.update({low : attr_dict})

clb = ['H1L', 'H1L', 'H1R', 'H1R', 'V1D', 'V1D', 'V1U', 'V1U']
h_io = ['H1L', 'H1L', 'H1R', 'H1R']
v_io = ['V1D', 'V1D', 'V1U', 'V1U']

edges = {}
for line in lines:
    if "<edge " in line:
        src = get_attr(line, "src_node")
        sink = get_attr(line, "sink_node")
        if src in coord_lookup and sink in coord_lookup:
            src_coords = coord_lookup[src]
            sink_coords = coord_lookup[sink]
            try:
                edges[src].append(sink)
            except:
                edges.update({src : [sink]})

for coords in sorted(chan_nodes):
    print coords
    wires = sorted([v for u, v in chan_nodes[coords].items()])
    if coords[0] == '0':
        if wires != v_io:
            print "Vertical I/Os wrong wires!"
            raise ValueError
    elif coords[1] == '0':
        if wires != h_io:
            print "Horizontal I/Os wrong wires!"
            raise ValueError
    else:
        if wires != clb:
            print "CLB tile wrong wires!"
            raise ValueError

    for wire in sorted(chan_nodes[coords], key = lambda w : (chan_nodes[coords][w], w)):
        print chan_nodes[coords][wire], "->"
        for v in edges.get(wire, []):
            sink_coords = coord_lookup[v]
            print ">>", chan_nodes[sink_coords][v], sink_coords 
    raw_input()
    
