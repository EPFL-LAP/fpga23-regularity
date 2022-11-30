"""Expresses the given pattern with presence/absence indicators on the complete list of edges.

Parameters
----------
all_edges : str
    Name of the file holding the list of all edges that could exist in the pattern.
pattern : str
    Name of the file holding the pattern (in the stored_edges.save format).

Returns
-------
None
"""

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--all_edges")
parser.add_argument("--pattern")

args = parser.parse_args()

with open(args.pattern, "r") as inf:
    lines = inf.readlines()

used = []
for line in lines:
    if line[0] != '~':
        used.append(line)

txt = ""
with open(args.all_edges, "r") as inf:
    lines = inf.readlines()
    
for line in lines:
    if not line in used and not line.strip() in used:
        line = '~' + line
    txt += line

pattern_dir = args.pattern.rsplit('/', 1)[0]
with open("%s/final.pattern" % pattern_dir, "w") as outf:
    outf.write(txt)
