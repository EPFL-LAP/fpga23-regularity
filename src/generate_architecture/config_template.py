import math

cplex_path = "%%cplex_path%%"

#Physical settings:
##########################################################################

wires = ["H1_L_0", "H1_L_1", "H2_L_0", "H4_L_0", "H6_L_0",\
         "H1_R_0", "H1_R_1", "H2_R_0", "H4_R_0", "H6_R_0",\
         "V1_D_0", "V1_D_1", "V4_D_0",\
         "V1_U_0", "V1_U_1", "V4_U_0"]

MAX_LUT_OFFSET = 1

MUX_WIDTH = 552   #nm (in 4nm node)
MUX_HEIGHT = 264  #nm (in 4nm node)
LUT_HEIGHT = 2112 #nm (in 4nm node)

MUX_COL_HEIGHT = int(math.floor(float(LUT_HEIGHT) / MUX_HEIGHT))
MUX_COL_CNT = int(math.ceil(float(len(wires)) / MUX_COL_HEIGHT))

norm = max(MUX_WIDTH, MUX_HEIGHT)
MUX_WIDTH = round(float(MUX_WIDTH) / norm, 4)
MUX_HEIGHT = round(float(MUX_HEIGHT) / norm, 4)

##########################################################################

#Constraint group enablers:
##########################################################################

ENFORCE_HOP_OPTIMALITY       = True       #Enforces hop-distance optimality.

ENFORCE_FANIN                = True       #Enforces fanin cardinality on all wires.

ENFORCE_FANOUT               = True       #Enforces fanout cardinality on all wires.

ENFORCE_EXTERNAL_SYMMETRY    = False      #Specifies that wires of the same length going
                                          #in opposite directions must have mutually symmetric fanouts.

ENFORCE_INTERNAL_SYMMETRY    = False      #Specifies that the fanout of each wire must be symmetric.

ENFORCE_CONTINUATION         = False      #Specifies that each wire must continue to the same wire.

ENFORCE_RELAXED_CONTINUATION = False      #Specifies that each wire must continue to any wire going in the same direction.

ENFORCE_TWO_TURNS            = False      #Specifies that each wire must turn to each of the two remaining
                                          #directions at least once.

ENFORCE_ONE_TURN             = False      #Specifies that each wire must turn at least once.

LIMIT_MUX_SIZE_NUMBER        = 1          #Specifies the number of different mux sizes that a pattern can have.

LIMIT_FANOUT_SIZE_NUMBER     = 1          #Specifies the number of different mux sizes that a pattern can have.

ALLOWED_MUX_SIZES            = [s for s in range(0, 21)] #Describes the allowed mux sizes.

ALLOWED_FANOUT_SIZES         = [s for s in range(0, 21)] #Describes the allowed mux sizes.

MAX_SWITCH_NUMBER            = 96         #Limits the maximum number of switches.

ENFORCE_MUX_PAIR_INPUT_SHARE = -1         #Forces each mux to form a pair with another with which it shares at least the
                                          #specified number of inputs.
         
#Eliminate dominated constraints.
if ENFORCE_TWO_TURNS:
    ENFORCE_ONE_TURN = False

if ENFORCE_CONTINUATION:
    ENFORCE_RELAXED_CONTINUATION = False

if ENFORCE_FANIN:
    LIMIT_MUX_SIZE_NUMBER = -1 
    MAX_SWITCH_NUMBER = -1
if ENFORCE_FANOUT:
    LIMIT_FANOUT_SIZE_NUMBER = -1 
    MAX_SWITCH_NUMBER = -1
    
if not (ENFORCE_FANIN or ENFORCE_FANOUT)  and not MAX_SWITCH_NUMBER:
    print "Neither fanin nor fanout are bound and switch count is unlimited."
    raise ValueError
##########################################################################

#Default numerical parameter values:
##########################################################################

DEFAULT_FANIN  = 6      #Default fanin to enforce on all wires.
DEFAULT_FANOUT = 6      #Default fanout to enforce on all wires.

##########################################################################

#Trade-off parameters:
##########################################################################

WL_TRADEOFF       = 0.0      #Specifies the trade-off between wirelength minimization (1) and usage maximization (0).

APPROXIMATE_USAGE = 0.0      #Specifies the desired distance of a random approximating usage sequence from the actual observed
                             #usage, expressed as the fraction of the distance from (others => 0).

##########################################################################

#Random seeds:
##########################################################################

FLOORPLAN_SEED = 19225      #Seed for optimizing the multiplexer arrangement.
USAGE_SEED     = 19225      #Seed for approximating usage at the desired distance from the original.

##########################################################################

#Global and debug parameters:
##########################################################################

SRV       = True      #Specifies that the script is being run on the server (changes CPLEX path).
verbose   = False     #Specifies that comments in the ILP should be preserved.

LP_RELAX  = False     #Converts binary variables to 0-1 bounded continuous.
                      #Useful for inspecting relaxation tightness.

INDEX_THR = 100       #Specifies the maximum number of shortest paths for which all shortest paths and the corresponding
                      #switch sets needed to realize them are enumerated, for later use in the set-indexing formulation
                      #of the hop-optimality enforcing constraints. Distances larger than that are implicitly represented
                      #through order constraints and continuity (see Papadimitriou's Hamiltonian path SAT encoding).

##########################################################################
