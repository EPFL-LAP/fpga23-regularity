import os

wd = os.getcwd()

for d in sorted(os.listdir("run_exploration/")):
    solutions = []
    ad = "run_exploration/%s" % d
    try:
        solutions = ["%s/src/test_%s/%s" % (ad, d, f) for f in os.listdir("%s/src/test_%s" % (ad, d)) if f.startswith("ilp_iter") and f.endswith(".log")]
    except:
        print "No solutions found in %s. Check if the run has completed." % d
        continue

    final_sol = sorted(solutions, key = lambda f : int(f.rsplit(".log", 1)[0].rsplit('_', 1)[-1]))[-2]
    print final_sol

    os.system("mkdir cleaned_patterns/%s/" % d)

    #Strip the usage info, to make the format compatible with the testing flow.
    with open(final_sol, "r") as inf:
        lines = inf.readlines()

    cleaned_lines = []
    for line in lines:
        if len(line.split()) == 2:
            cleaned_lines.append(line.split()[0])
        elif not line.isspace():
            cleaned_lines.append(line.strip())
    txt = "\n".join(cleaned_lines)
    with open("cleaned_patterns/%s/sol_0.ilp" % d, "w") as outf:
        outf.write(txt)


