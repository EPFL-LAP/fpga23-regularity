import os
import argparse
import networkx as nx
import math
import random
import statistics
import copy
import numpy
import importlib

from collections import namedtuple

parser = argparse.ArgumentParser()
parser.add_argument("--vpr_log")
parser.add_argument("--config")
args = parser.parse_args()

#Load the specified configuration:
if args.config is None:
    args.config = "config"

config = importlib.import_module(args.config)
if "__all__" in config.__dict__:
    names = config.__dict__["__all__"]
else:
    names = [x for x in config.__dict__ if not x.startswith("_")]
globals().update({k: getattr(config, k) for k in names})


Switch = namedtuple("Switch", ["driver", "target", "lut_offset"])

##########################################################################
def euclidean(vec1, vec2):
    """Computes the Euclidean distance between two vectors.

    Parameters
    ----------
    vec1 : List[int]
        First vector.
    vec2 : List[int]
        Second vector.

    Returns
    -------
    float
        Euclidean distance.
    """

    array1, array2 = numpy.array(vec1), numpy.array(vec2)
    differences = array1 - array2
    squared_sums = numpy.dot(differences.T, differences)
    distance = numpy.sqrt(squared_sums)

    return distance
##########################################################################

##########################################################################
class OptimalDistances(object):
    """Models the constraints for enforcing that the switch pattern
    provides the optimal coverage of all offsets within a certain range,
    in terms of hop count.

    Parameters
    ----------
    wires : List[str]
        List of wires available in the architecture.
    max_lut_offset : int
        Maximum LUT-level offset for the switches.
    """

    #------------------------------------------------------------------------#
    def __init__(self, wires, max_lut_offset):
        """Constructor of the OptimalDistances class."""

        self.wires = tuple(sorted(wires))
        self.max_lut_offset = max_lut_offset

        self.offsets = None
        self.bin_vars = []
        self.general_vars = []
        self.csts = []
        self.user_cuts = []
        self.lazy_csts = []
        self.bounds = []

        self.all_switches = []

        for driver in wires:
            for target in wires:
                for lut_offset in range(-1 * max_lut_offset, max_lut_offset + 1):
                    switch = Switch(driver, target, lut_offset)
                    if not self.is_u_turn(switch):
                        self.all_switches.append(switch)
                        self.bin_vars.append(self.switch_var(switch))
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def land(self, a, b = None, res_var = None):
        """Generates constraints for forming a logical and between the two variables.

        Parameters
        ----------
        a : str
            Variable.
        b : Optional[str], default = None
            Variable.
            If b is None, a is assumed to be a list of variables.
        res_var : Optional[str], default = None
            Specifies the name of the resulting variable.

        Returns
        -------
        List[str]
            Constraints.
        str
            Result variable.
        """


        if b is not None:
            csts = []
            ab = "%s_land_%s" % (a, b)
            if res_var is not None:
                ab = res_var
            csts.append("%s + %s - %s <= 1" % (a, b, ab))
            csts.append("%s - %s <= 0" % (ab, a))
            csts.append("%s - %s <= 0" % (ab, b))
        else:
            ab = ""
            for v in a:
                ab += "%s_land_" % v
            ab = ab[:-len("_land_")]
            if res_var is not None:
                ab = res_var
            csts = []
            cst = ""
            for v in a:
                cst += " + %s" % v
                csts.append("%s - %s <= 0" % (ab, v))
            cst += " - %s" % ab
            cst += " <= %d" % (len(a) - 1)
            csts.insert(0, cst[len(" + "):])

        return csts, ab
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def lor(self, a, b = None, res_var = None):
        """Generates constraints for forming a logical or between the two variables.

        Parameters
        ----------
        a : str
            Variable.
        b : Optional[str], default = None
            Variable.
            If b is None, a is assumed to be a list of variables.
        res_var : Optional[str], default = None
            Specifies the name of the resulting variable.

        Returns
        -------
        List[str]
            Constraints.
        str
            Result variable.
        """


        if b is not None:
            csts = []
            ab = "%s_lor_%s" % (a, b)
            if res_var is not None:
                ab = res_var
            csts.append("%s + %s - %s >= 0" % (a, b, ab))
            csts.append("%s - %s >= 0" % (ab, a))
            csts.append("%s - %s >= 0" % (ab, b))
        else:
            ab = ""
            for v in a:
                ab += "%s_lor_" % v
            ab = ab[:-len("_lor_")]
            if res_var is not None:
                ab = res_var
            csts = []
            cst = ""
            for v in a:
                cst += " + %s" % v
                csts.append("%s - %s >= 0" % (ab, v))
            cst += " - %s" % ab
            cst += " >= 0"
            csts.insert(0, cst[len(" + "):])

        return csts, ab
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def continuous_indicator(self, indicator_var, continuous_var, linearized_var, continuous_ub, shift = 0.0):
        """Generates constraints necessary for linearization of a product of a
        nonnegative continuous variable and a binary indicator variable.

        Parameters
        ----------
        indicator_var : str
            Name of the binary indicator variable.
        continuous_var : str
            Name of the continous variable.
        linearized_var : str
            Name of the linearized product variable.
        continuous_ub : float
            Maximum value attainable by the continuous variable.
        shift : Optional[float], default = 0.0
            
        
        Returns
        -------
        None
        """

        continuous_ub += shift

        self.csts.append("%.4f %s - %s >= 0" % (continuous_ub, indicator_var, linearized_var))
        self.csts.append("%s - %s <= %.4f" % (linearized_var, continuous_var, shift))
        self.csts.append("%s + %.4f %s - %s <= %.4f" % (continuous_var, continuous_ub, indicator_var, linearized_var,\
                                                        continuous_ub - shift))

        self.bounds.append("0 <= %s <= %.4f" % (linearized_var, continuous_ub))
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def equals_const_indicator(self, indicator_var, observed_var, target_value, observed_ub):
        """Generates the constraints which set an indicator variable to 1 if another
        variable equals the specified constant and to 0 otherwise.

        Parameters
        ----------
        indicator_var : str
            Name of the binary indicator variable.
        observed_var : str
            Variable the value of which is being tracked.
        target_value : int
            Value used to set the indicator.
        observed_ub : int
            Maximum value attainable by the continuous variable.

        Returns
        -------
        None
        """

        geq_ind = "%s_delta_geq_ind" % indicator_var
        leq_ind = "%s_delta_leq_ind" % indicator_var

        delta = 0.3
        #When x = (b + delta) or x = (b - delta), half the constraints don't work (either geq or leq can be both 1 and 0),
        #so we need to make this fractional.

        #Mz1 >= x - (b - delta)
        self.csts.append("%d %s - %s >= - %.4f" % (observed_ub, geq_ind, observed_var, target_value - delta))
        #M(1-z1) >= (b - delta) - x
        self.csts.append("%s - %d %s >= %.4f" % (observed_var, observed_ub, geq_ind, target_value - delta - observed_ub))

        #Mz2 >= (b + delta) - x
        self.csts.append("%d %s + %s >= %.4f" % (observed_ub, leq_ind, observed_var, target_value + delta))
        #M(1-z2) >= x - (b + delta)
        self.csts.append("- %s - %d %s >= %.4f" % (observed_var, observed_ub, leq_ind, -1 * target_value - delta - observed_ub))

        csts, prod_var = self.land(geq_ind, leq_ind)
        self.csts += csts
        self.csts.append("%s - %s = 0" % (indicator_var, prod_var))

        self.bin_vars.append(geq_ind)
        self.bin_vars.append(leq_ind)
        self.bin_vars.append(prod_var)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def generate_different_mux_size_bounding_constraints(self, allowed_mux_sizes, max_size_number, bound_fanout = False):
        """Generates constraints necessary for bounding the number of different
        multiplexer sizes present in the pattern.

        Parameters
        ----------
        allowed_mux_sizes : List[int]
            List of allowed multiplexer sizes.
        max_size_number : int
            Maximum number of different sizes that can appear in the pattern.
        bound_fanout : Optional[bool], default = False
            Specifies that the number of different fanout sizes should be bounded instead.

        Returns
        -------
        None
        """

        size_wire_pair_var = lambda wire_index, size : "%s_size_%d_%d" % ("fanout" if bound_fanout else "mux", wire_index, size)

        #Add available mux size indicators and enforce that exactly one is true:
        for w, wire in enumerate(self.wires):
            cst = ""
            for switch in self.all_switches:
                if bound_fanout:
                    if switch.driver == wire:
                        cst += " + %s" % self.switch_var(switch)
                elif switch.target == wire:
                    cst += " + %s" % self.switch_var(switch)
            one_size_only_cst = ""
            for size in allowed_mux_sizes:
                var = size_wire_pair_var(w, size)
                cst += " - %d %s" % (size, var)
                one_size_only_cst += " + %s" % var
                self.bin_vars.append(var)
            cst += " = 0"
            one_size_only_cst += " = 1"
            self.csts.append(cst)
            self.csts.append(one_size_only_cst)

        #Now loop over all wires and for each size, OR the appropriate indicators to track presence of size on any wire:
        lor_vars = []
        for size in allowed_mux_sizes:
            wire_vars = []
            for w, wire in enumerate(self.wires):
                wire_vars.append(size_wire_pair_var(w, size))
            lor_var = "%s_size_%d_present" % ("fanout" if bound_fanout else "mux", size)
            lor_csts, lor_var = self.lor(wire_vars, res_var = lor_var)
            self.csts += lor_csts
            self.bin_vars.append(lor_var)
            lor_vars.append(lor_var)

        #Finally, bound the number of resulting presence variables:
        cst = ""
        for lor_var in lor_vars:
            cst += " + %s" % lor_var
        cst += " <= %d" % max_size_number
        self.csts.append(cst)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def force_mux_pair_input_sharing(self, min_sharing):
        """Generates constraints that force each mux to participate in a pair
        with which it shares at least min_sharing inputs.

        Parameters
        ----------
        min_sharing : int
            Minimum number of shared inputs among the members of the pair.

        Returns
        -------
        None
        """

        get_wire_switches = lambda wire : {(sw.driver, sw.lut_offset) : sw for sw in sorted(self.all_switches) if sw.target == wire}
        share_single_input_var = lambda sw1, sw2 : "input_shared_%s_and_%s" % (self.switch_var(sw1), self.switch_var(sw2))
        share_meas_var = lambda w1, w2 : "sharing_%d_and_%d" % (w1, w2)
        force_share_var = lambda w1, w2 : "force_input_sharing_%d_and_%d" % (w1, w2)

        assignment_csts = ["" for w in range(0, len(self.wires))]
        for w1 in range(0, len(self.wires)):
            wire1 = self.wires[w1]
            switches1 = get_wire_switches(wire1)
            for w2 in range(w1 + 1, len(self.wires)):
                sharing_counter = ""
                wire2 = self.wires[w2]
                switches2 = get_wire_switches(wire2)
                for driver, sw1 in switches1.items():
                    sw2 = switches2.get(driver, None)
                    if sw2 is None:
                        continue
                    land_csts, land_var = self.land(self.switch_var(sw1), self.switch_var(sw2),\
                                                    res_var = share_single_input_var(sw1, sw2))
                    self.csts += land_csts
                    self.bin_vars.append(land_var)
                    sharing_counter += " + %s" % land_var
                sharing_counter += " - %s = 0" % share_meas_var(w1, w2)
                self.csts.append(sharing_counter)
                force_implication = "%d %s - %s <= 0" % (min_sharing, force_share_var(w1, w2), share_meas_var(w1, w2))
                self.csts.append(force_implication)
                self.bin_vars.append(force_share_var(w1, w2))

                assignment_csts[w1] += " + %s" % force_share_var(w1, w2)
                assignment_csts[w2] += " + %s" % force_share_var(w1, w2)
    
        for w in range(0, len(self.wires)):
            #Force exactly one pair membership on each wire. Because we use implications and not equivalences,
            #each wire is free to belong to multiple pairs as well, but there will always exist at least one assignment of pairs.
            assignment_csts[w] += " = 1"
            self.csts.append(assignment_csts[w])
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def limit_pattern_size(self, pattern_size):
        """Limits the pattern size from above.

        Parameters
        ----------
        pattern_size : int
            Upper bound on the pattern size to be enforced.

        Returns
        -------
        None
        """

        cst = ""
        for switch in self.all_switches:
            cst += " + %s" % self.switch_var(switch)
        cst += " <= %d" % pattern_size

        self.csts.append(cst)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def wl_opt(self, lock_positions = None, limit_cheby = 0):
        """Generates constraints necessary for intraSB wirelength optimization.

        Parameters
        ----------
        lock_positions : Optional[Dict[str, Tuple[int]], default = None
            Specifies a (partial) mux location map. Can be useful for obtaining
            quick initial solutions.
        limit_cheby : Optional[int]
            Instead of locking muxes at the given positions only, it allows them to move to
            positions within Chenyshev distance limit_cheby of the initial location.

        Returns
        -------
        str
            WL objective variable.
        """

        #Variables to store the multiplexer locations:
        mux_pos_vars = {}
        get_mux_pos_var = lambda wire, x, y : "mux_pos___%s___%d___%d" % (wire, x, y)
        self.get_mux_pos_var = get_mux_pos_var

        #Unique position constraints:
        unique_pos = []
        listed_muxes = []
        for wire in self.wires:
            cst = ""
            for x in range(0, MUX_COL_CNT):
                for y in range(0, MUX_COL_HEIGHT):
                    pos_var = get_mux_pos_var(wire, x, y)
                    listed_muxes.append(pos_var)
                    cst += " + %s" % pos_var
                    try:
                        mux_pos_vars[(x, y)].append(pos_var)
                    except:
                        mux_pos_vars.update({(x, y) : [pos_var]})
            cst += " = 1"
            unique_pos.append(cst)

        #No overlaps:
        no_overlap = []
        for coords, pos_vars in sorted(mux_pos_vars.items()):
            cst = ""
            for pos_var in pos_vars:
                cst += " + %s" % pos_var
            cst += " <= 1"
            no_overlap.append(cst)
            self.bin_vars += pos_vars
        
        #Individual lengths:
        len_csts = []
        objs = {}
        obj = ""
        fanin_bounds = {}
        for switch in self.all_switches:
            drvr, trgt, lut_offset = switch
            if not drvr in objs:
                objs.update({drvr : ""})
            if not trgt in fanin_bounds:
                fanin_bounds.update({trgt : ""})
            for drvr_x in range(0, MUX_COL_CNT):
                for drvr_y in range(0, MUX_COL_HEIGHT):
                    drvr_pos_var = get_mux_pos_var(drvr, drvr_x, drvr_y)
                    for trgt_x in range(0, MUX_COL_CNT):
                        for trgt_y in range(0, MUX_COL_HEIGHT):
                            if (drvr != trgt) and (lut_offset == 0) and (drvr_x == trgt_x) and (drvr_y == trgt_y):
                                continue
                            if (drvr == trgt) and ((drvr_x, drvr_y) != (trgt_x, trgt_y)):
                                continue
                            trgt_pos_var = get_mux_pos_var(trgt, trgt_x, trgt_y)
                            switch_width = abs(trgt_x - drvr_x) * MUX_WIDTH
                            switch_height = abs(trgt_y - drvr_y + lut_offset * MUX_COL_HEIGHT) * MUX_HEIGHT
                            switch_len = switch_width + switch_height
                            csts, indicator_var = self.land([self.switch_var(switch), drvr_pos_var, trgt_pos_var])
                            self.bin_vars.append(indicator_var)
                            len_csts += csts
                            objs[drvr] += " + %.4f %s" % (switch_len, indicator_var)
                            fanin_bounds[trgt] += " + %.4f %s" % (switch_len, indicator_var)
                            obj += " + %.4f %s" % (switch_len, indicator_var)

        self.csts += unique_pos
        self.csts += no_overlap
        self.csts += len_csts

        obj_var = "total_wl"
        obj += " - %s = 0" % obj_var

        self.csts.append(obj)

        cheby = lambda x1, y1, x2, y2 : max([abs(x1 - x2), abs(y1 - y2)])
        if lock_positions is not None:
            if limit_cheby == 0:
                for wire, coords in sorted(lock_positions.items()):
                    mux_var = get_mux_pos_var(wire, coords[0], coords[1])
                    if mux_var in listed_muxes:
                        self.csts.append("%s = 1" % mux_var)
            else:
                for wire in self.wires:
                    init_loc = lock_positions[wire]
                    for x in range(0, MUX_COL_CNT):
                        for y in range(0, MUX_COL_HEIGHT):
                            dist = cheby(x, y, init_loc[0], init_loc[1])
                            if dist <= limit_cheby:
                                continue
                            mux_var = get_mux_pos_var(wire, x, y)
                            self.csts.append("%s = 0" % mux_var)

        return obj_var
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def add_fanout_center_constraints(self):
        """Adds constraints to track the position of each driver mux and
        try to locate it at the average of the coordinates of its fanout muxes.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        secondary_objective = ""

        max_x_len = MUX_COL_CNT
        max_y_len = MUX_COL_HEIGHT - 1
        min_len = 0
        global_y_shift = self.max_lut_offset * MUX_COL_HEIGHT
        #Shift all y coordinates, so as to remove the need for negative coordinates.

        for wire in self.wires:
            x_var = "wire_%s_xcoord" % wire
            y_var = "wire_%s_ycoord" % wire
            self.general_vars.append(x_var)
            self.general_vars.append(y_var)
            x_cst = ""
            y_cst = ""
            for x in range(0, MUX_COL_CNT):
                for y in range(0, MUX_COL_HEIGHT):
                    x_cst += " + %d %s" % (x, self.get_mux_pos_var(wire, x, y))
                    y_cst += " + %d %s" % (y + global_y_shift, self.get_mux_pos_var(wire, x, y))
            x_cst += " - %s = 0" % x_var
            y_cst += " - %s = 0" % y_var
            
            self.csts.append(x_cst)
            self.csts.append(y_cst)
            self.bounds.append("0 <= %s <= %.4f" % (x_var, MUX_COL_CNT))
            self.bounds.append("%.4f <= %s <= %.4f" % (global_y_shift, y_var, MUX_COL_HEIGHT + global_y_shift))

            fanout_x_cst = ""
            fanout_y_cst = ""
            for trgt in self.wires:
                trgt_x_var = "wire_%s_xcoord" % trgt
                trgt_y_var = "wire_%s_ycoord" % trgt
                for lut_offset in range(-1 * self.max_lut_offset, self.max_lut_offset + 1):
                    switch = Switch(wire, trgt, lut_offset)
                    if not switch in self.all_switches:
                        continue
                    self.continuous_indicator(self.switch_var(switch), trgt_x_var,\
                                              "%s___xcoord" % self.switch_var(switch), max_x_len)
                    self.continuous_indicator(self.switch_var(switch), trgt_y_var,\
                                              "%s___ycoord" % self.switch_var(switch), max_y_len + global_y_shift,\
                                              shift = lut_offset * MUX_COL_HEIGHT)

                    fanout_x_cst += " + %.4f %s" % (1.0 / DEFAULT_FANIN * MUX_WIDTH, "%s___xcoord" % self.switch_var(switch))
                    fanout_y_cst += " + %.4f %s" % (1.0 / DEFAULT_FANIN * MUX_HEIGHT, "%s___ycoord" % self.switch_var(switch))

            fanout_x_cst += " - %s - %s = 0" % (x_var, "wire_%s_fanout_avg_x_delta" % wire)
            fanout_y_cst += " - %s - %s = 0" % (y_var, "wire_%s_fanout_avg_y_delta" % wire)

            self.csts.append(fanout_x_cst)
            self.csts.append(fanout_y_cst)

            x_ub = MUX_COL_CNT * MUX_WIDTH
            y_ub = (1 + self.max_lut_offset) * MUX_COL_HEIGHT * MUX_HEIGHT
            self.bounds.append("%.4f <= %s <= %.4f" % (-1 * x_ub, "wire_%s_fanout_avg_x_delta" % wire, x_ub))
            self.bounds.append("%.4f <= %s <= %.4f" % (-1 * y_ub, "wire_%s_fanout_avg_y_delta" % wire, y_ub))

            x_abs_delta_var = "wire_%s_fanout_avg_x_abs_delta" % wire
            y_abs_delta_var = "wire_%s_fanout_avg_y_abs_delta" % wire

            self.csts.append("%s - wire_%s_fanout_avg_x_delta >= 0" % (x_abs_delta_var, wire))
            self.csts.append("%s + wire_%s_fanout_avg_x_delta >= 0" % (x_abs_delta_var, wire))
            self.csts.append("%s - wire_%s_fanout_avg_y_delta >= 0" % (y_abs_delta_var, wire))
            self.csts.append("%s + wire_%s_fanout_avg_y_delta >= 0" % (y_abs_delta_var, wire))

            self.bounds.append("0 <= %s <= %.4f" % (x_abs_delta_var, x_ub))
            self.bounds.append("0 <= %s <= %.4f" % (y_abs_delta_var, y_ub))

            secondary_objective += " + %s + %s" % (x_abs_delta_var, y_abs_delta_var)

        self.secondary_objective = secondary_objective
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def assemble_greedy_solution(self, utilizations):
        """Assembles a greedy solution satisfying only the pattern
        size constraints, from which the normalization factors for usage
        and wirelength can be obtained.

        Parameters
        ----------
        utilizations : Dict[Switch, Dict[str, int]]
            A dictionary of observed utilizations.

        Returns
        -------
        float
            Total usage of the greedy solution (maximizing usage).
        float
            Total wirelength of the greedy solution (maximizing usage).
        Dict[str, Tuple[int]]
            Default mux stacking order.
        """

        pattern_size = len(self.wires) * DEFAULT_FANIN
        switches = sorted(utilizations, key = lambda s : (-1 * utilizations[s]["cur"], s))[:pattern_size]

        mux_order = sorted(self.wires)
        coords = {}
        cols = [[]]
        for mux in mux_order:
            if len(cols[-1]) == MUX_COL_HEIGHT:
                cols.append([mux])
            else:
                cols[-1].append(mux)
            coords.update({mux : (len(cols) - 1, len(cols[-1]) - 1)})

        wl = 0
        usage = 0
        for switch in switches:
            usage += utilizations[switch]["cur"]
            wl += abs(coords[switch.target][0] - coords[switch.driver][0]) * MUX_WIDTH
            wl += abs(coords[switch.target][1] - coords[switch.driver][1] + switch.lut_offset * MUX_COL_HEIGHT) * MUX_HEIGHT

        return float(usage), float(wl), coords
    #------------------------------------------------------------------------#

    wire_direction = lambda self, wire : wire.split('_')[1]

    #------------------------------------------------------------------------#
    def is_u_turn(self, switch):
        """Checks if a switch is a U-turn.

        Parameters
        ----------
        switch : Switch
            Switch to be checked.

        Returns
        -------
        bool
            True if U-turn, False otherwise.
        """

        opposites = {'U' : 'D', 'D' : 'U', 'L' : 'R', 'R' : 'L'}

        return self.wire_direction(switch.target) == opposites[self.wire_direction(switch.driver)]
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def get_offset(self, wire):
        """Returns an offset vector of a wire.

        Parameters
        ----------
        wire : str
            Wire name.

        Returns
        -------
        Tuple[int]
            Offset vector of the wire.
        """

        L = self.get_len(wire)
        if self.wire_direction(wire) in ('D', 'L'):
            L *= -1

        offset = (L, 0) if wire[0] == 'H' else (0, L)

        return offset
    #------------------------------------------------------------------------#

    get_len = lambda self, wire : int(wire.split('_', 1)[0][1:])

    cplex_abs = lambda self, a : "%s%d" % ('m' if a < 0 else 'p', abs(a))

    #Variables representing the position in the path occupied by a wire.
    wire_pos_var = lambda self, offset, wire, pos : "offset_%s_%s_%d_%d"\
                 % (self.cplex_abs(offset[0]), self.cplex_abs(offset[1]), self.wires.index(wire), pos)

    #Switch variables.
    switch_var = lambda self, switch : "x_%d_%d_%s"\
               % (self.wires.index(switch.driver), self.wires.index(switch.target), self.cplex_abs(switch.lut_offset))

    #------------------------------------------------------------------------#
    def single_offset_csts(self, offset, opt_len, lazy = False):
        """Generates constraints for a single offset.

        Parameters
        ----------
        offset : Tuple[int]
            Offset that needs to be covered.
        opt_len : int
            Optimal hop-length (e.g., obtained by Dijkstra on a full-switch graph.
        lazy : Optional[bool], default = False
            Consider the constraints lazy.

        Returns
        -------
        None
        """

        if verbose:
            csts = ["\ Offset (%d, %d)\n" % (offset[0], offset[1])]
        else:
            csts = []
        x_reach_cst = ""
        y_reach_cst = ""
        for pos in range(0, opt_len):
            if verbose:
                csts.append("\ Hop %d\n")
            csts.append("")
            for wire in self.wires:
                var = self.wire_pos_var(offset, wire, pos)
                self.bin_vars.append(var)
                csts[-1] += " + %s" % var
                d_x, d_y = self.get_offset(wire)
                if d_x:
                    x_reach_cst += "%s %d %s" % (" +" if d_x > 0 else '', d_x, var)
                if d_y:
                    y_reach_cst += "%s %d %s" % (" +" if d_y > 0 else '', d_y, var)
            csts[-1] += " = 1"

        x_reach_cst += " = %d" % offset[0]
        y_reach_cst += " = %d" % offset[1]

        for pos in range(1, opt_len):
            prev_pos = pos - 1
            for u in self.wires:
                u_var = self.wire_pos_var(offset, u, prev_pos)
                for v in self.wires:
                    v_var = self.wire_pos_var(offset, v, pos)
                    w_sum = ""
                    u_turn = False
                    for w in range(-1 * self.max_lut_offset, self.max_lut_offset + 1):
                        switch = Switch(u, v, w)
                        if self.is_u_turn(switch):
                            u_turn = True
                            break
                        w_sum += " - %s" % self.switch_var(switch)
                    if u_turn:
                        #Eliminate U-turns.
                        csts.append("%s + %s <= 1" % (u_var, v_var))
                        continue

                    if verbose:
                        csts.append("\ Connectivity: %s -> %s @ target hop %d" % (u, v, pos))

                    uv_csts, uv_var = self.land(u_var, v_var)
                    self.bin_vars.append(uv_var)
                    csts += uv_csts
                    csts.append("%s%s <= 0" % (uv_var, w_sum))
                    
        csts.append(x_reach_cst)
        csts.append(y_reach_cst)

        for wire in self.wires:
            max_count = self.max_counts[wire][offset]
            cst = ""
            for pos in range(0, opt_len):
                var = self.wire_pos_var(offset, wire, pos)
                cst += " + %s" % var
            cst += " <= %d" % max_count
            csts.append(cst)

        if lazy:
            self.lazy_csts += csts
        else:
            self.csts += csts
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def check_optimality(self, switches, get_differences = False):
        """Checks the optimality of the given set of switches.

        Parameters
        ----------
        switches : List[Switch]
            Switch set to be checked.
        get_differences : Optional[bool], default = False
            Specifies that the differences between hop distances for each location should be returned.
       
        Returns
        -------
        bool
            True if optimal, False otherwise.
        """

        G = nx.DiGraph()

        for x, y in list(self.offsets.keys()) + [(0, 0)]:
            for wire in self.wires:
                d_x, d_y = self.get_offset(wire)
                sink = "sink_%d_%d" % (x + d_x, y + d_y)
                u = "%d_%d_%s" % (x, y, wire)
                G.add_edge(u, sink)
                for v_wire in self.wires:
                    v = "%d_%d_%s" % (x + d_x, y + d_y, v_wire)
                    if any(Switch(wire, v_wire, lut_offset) in switches for lut_offset\
                           in range(-1 * self.max_lut_offset, self.max_lut_offset + 1)):
                        G.add_edge(u, v)
                if x == y == 0:
                    G.add_edge("src", u)

        distances = nx.single_source_dijkstra_path_length(G, "src")

        differences = []

        for offset, d in self.offsets.items():
            x, y = offset
            if x == y == 0:
                continue
            try:
                if distances["sink_%d_%d" % (x, y)] - 1 != d:
                    print "Offset = (%d, %d). Expected = %d; Observed = %d" % (x, y, d, distances["sink_%d_%d" % (x, y)] - 1)
                    if not get_differences:
                        return False
                differences.append(float(distances["sink_%d_%d" % (x, y)] - 1 - d) / d * 100)
            except:
                #Disconnected sink.
                print "Sink (%d, %d) disconnected" % (x, y)
                if not get_differences:
                    return False
                differences.append(-100.0)

        if not get_differences:
            return True

        return differences
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def get_optimal_hop_counts(self, grid_size = None, check_only = False):
        """Computes the minimum hop counts for all offsets in the specified region,
        assuming that all potential switches are present.

        Parameters
        ----------
        grid_size : Optional[Tuple[int]], default = None
            Specifies the grid size on which to compute the lower bounds.
            If left at the default value, grid dimensions are set to twice the sum
            of lengths of all wires going in the particular direction.
        check_only : Optional[bool], default = False
            Specifies that the routine is called only for optimality checking.

        Returns
        -------
        None
        """

        if grid_size is None:
            grid_size = (sum([self.get_offset(wire)[0] for wire in self.wires if "_R_" in wire]) * 2,\
                         sum([self.get_offset(wire)[1] for wire in self.wires if "_U_" in wire]) * 2)

        G = nx.DiGraph()
        G_with_u_turns = nx.DiGraph()

        for x in range(-1 * grid_size[0], grid_size[0] + 1):
            for y in range(-1 * grid_size[1], grid_size[1] + 1):
                for wire in self.wires:
                    d_x, d_y = self.get_offset(wire)
                    sink = "sink_%d_%d" % (x + d_x, y + d_y)
                    u = "%d_%d_%s" % (x, y, wire)
                    G.add_edge(u, sink)
                    G_with_u_turns.add_edge(u, sink)
                    for v_wire in self.wires:
                        v = "%d_%d_%s" % (x + d_x, y + d_y, v_wire)
                        switch = Switch(wire, v_wire, 0) #LUT-level offset does not matter for lower-bounding.
                        G_with_u_turns.add_edge(u, v)
                        if self.is_u_turn(switch):
                            continue
                        G.add_edge(u, v)
                    if x == y == 0:
                        G.add_edge("src", u)
                        G_with_u_turns.add_edge("src", u)

        distances = nx.single_source_dijkstra_path_length(G, "src")
        if not check_only:
            with_u_turns_distances = nx.single_source_dijkstra_path_length(G_with_u_turns, "src")
        hops = {}
        with_u_turns_hops = {}
        sp_var = lambda spcnt, offset : "sp%d_%s_%s" % (spcnt, self.cplex_abs(offset[0]), self.cplex_abs(offset[1])) 
        self.shortest_paths = {}
        for x in range(-1 * grid_size[0], grid_size[0] + 1):
            for y in range(-1 * grid_size[1], grid_size[1] + 1):
                if x == y == 0:
                    continue
                sink = "sink_%d_%d" % (x, y)
                hops.update({(x, y) : distances[sink] - 1})
                #-1 for src itself.

                if not check_only:
                    with_u_turns_hops.update({(x, y) : with_u_turns_distances[sink] - 1})
   
                    #List shortest paths for switch set indexing constraints in case we want a combined modeling approach.
                    self.shortest_paths.update({(x, y) : {}})
                    for spcnt, sp in enumerate(list(nx.all_shortest_paths(G, "src", sink))):
                        key = sp_var(spcnt, (x, y))
                        self.shortest_paths[(x, y)].update({key : []})
                        for u, v in zip(sp[1:-1], sp[2:-1]):
                            cst = key 
                            u = '_'.join(u.split('_')[2:])
                            v = '_'.join(v.split('_')[2:])
                            for lut_offset in range(-1 * self.max_lut_offset, self.max_lut_offset + 1):
                                switch = Switch(u, v, lut_offset)
                                cst += " - %s" % self.switch_var(switch)
                            cst += " <= 0"
                            self.shortest_paths[(x, y)][key].append(cst)

        self.offsets = hops

        if check_only:
            return

        max_counts = {}
        for wire in self.wires:
            max_counts.update({wire : {}})
            for offset, d in self.offsets.items():
                #We take the achievable minimum hop distance from the map without U-turns.
                success = 0
                for i in range(1, d + 1):
                    origin = self.get_offset(wire)
                    origin = (i * origin[0], i * origin[1])
                    rem = (offset[0] - origin[0], offset[1] - origin[1])
                    if rem == (0, 0):
                        new_d = i
                    else:
                        try:
                            #We take the lower bound on the remainder from the map with U-turns
                            #as otherwise the argument on irrelevance of wire order does not hold.
                            #For example, offset (-6, -7) can be implemented without U-turns in 4 hops
                            #by taking V4D->V4D->H6L->V1U, but with H6L chosen first, this cannot be done
                            #without making a U-turn anymore.
                            new_d = i + with_u_turns_hops[rem]
                        except:
                            break
                    if new_d > d:
                        break
                    success = i
                max_counts[wire].update({offset : success})

        self.max_counts = max_counts
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def force_same_fanin(self, within_direction_only = True):
        """Forces the same fanin on all wires.

        Parameters
        ----------
        within_direction_only : Optional[bool], default = True
            Specifies that enforcing should happen only among H and V wires,
            but that fanin can differ between H and V.

        Returns
        -------
        None
        """

        for wire in self.wires:
            cst = ""
            for switch in self.all_switches:
                if switch.target == wire:
                    cst += " + %s" % self.switch_var(switch)
            cst += " - fanin%s = 0" % (wire[0] if within_direction_only else '')
            self.csts.append(cst)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def force_concrete_fanins(self, fanin_dict):
        """Forces particular fanins onto (a subset of) wires.

        Parameters
        ----------
        fanin_dict : Dict[str, int]
            Desired fanins.

        Returns
        -------
        None
        """

        for wire, fanin in fanin_dict.items():
            cst = ""
            for switch in self.all_switches:
                if switch.target == wire:
                    cst += " + %s" % self.switch_var(switch)
            cst += " = %d" % fanin
            self.csts.append(cst)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def force_same_fanout(self, within_direction_only = True):
        """Forces the same fanout on all wires.

        Parameters
        ----------
        within_direction_only : Optional[bool], default = True
            Specifies that enforcing should happen only among H and V wires,
            but that fanout can differ between H and V.

        Returns
        -------
        None
        """

        for wire in self.wires:
            cst = ""
            for switch in self.all_switches:
                if switch.driver == wire:
                    cst += " + %s" % self.switch_var(switch)
            cst += " - fanout%s = 0" % (wire[0] if within_direction_only else '')
            self.csts.append(cst)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def force_concrete_fanouts(self, fanout_dict):
        """Forces particular fanouts onto (a subset of) wires.

        Parameters
        ----------
        fanout_dict : Dict[str, int]
            Desired fanouts.

        Returns
        -------
        None
        """

        for wire, fanout in fanout_dict.items():
            cst = ""
            for switch in self.all_switches:
                if switch.driver == wire:
                    cst += " + %s" % self.switch_var(switch)
            cst += " = %d" % fanout
            self.csts.append(cst)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def force_length_order(self, order, within_direction_only = True):
        """Imposes a nondecreasing or a nonincreasing order on the switches.

        Parameters
        ----------
        order : str
            Nondecreasing or increasing.
        within_direction_only : Optional[bool], default = True
            Specifies that enforcing should happen only among H and V wires,
            but not from H to V or V to H.

        Returns
        -------
        None
        """

        for switch in self.all_switches:
            if switch.driver[0] != switch.target[0]:
                continue
            if order == "nonincr":
                if self.get_len(switch.target) > self.get_len(switch.driver):
                    self.csts.append("%s <= 0" % self.switch_var(switch))
            elif order == "nondecr":
                if self.get_len(switch.target) < self.get_len(switch.driver):
                    print switch
                    self.csts.append("%s <= 0" % self.switch_var(switch))
            else:
                print "Unknown order specification."
                raise ValueError
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def prohibit_opposite_switch_pairs(self):
        """Generates constraints that prevent ocurrence of opposing switch pairs.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        pairs = set()
        for switch in self.all_switches:
            driver, target, lut_offset = switch
            opposite = Switch(target, driver, lut_offset)
            if opposite == switch:
                continue
            pairs.add(tuple(sorted((switch, opposite))))

        for switch, opposite in sorted(pairs):
            self.csts.append("%s + %s <= 1" % (self.switch_var(switch), self.switch_var(opposite)))
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def add_symmetry_constraints(self, check_switches = None):
        """Adds the switch symmetry constraints. These dictate that L-R wires
        should have symmetric switches, as should the U-D wires.

        Parameters
        ----------
        check_switches : Optional[List[Switch]], default = None
            Specifies that the routine should check if the given set
            of switches has external fanout symmetry or not.
        
        Returns
        -------
        None
        """

        pairs = set()
        for switch in self.all_switches:
            driver, target, lut_offset = switch
            sym_driver = driver
            sym_target = target
            if "_R_" in driver:
                sym_driver = sym_driver.replace("_R_", "_L_")
                if "_R_" in target:
                    sym_target = sym_target.replace("_R_", "_L_")
            elif "_L_" in driver:
                sym_driver = sym_driver.replace("_L_", "_R_")
                if "_L_" in target:
                    sym_target = sym_target.replace("_L_", "_R_")
            elif "_U_" in driver:
                sym_driver = sym_driver.replace("_U_", "_D_")
                if "_U_" in target:
                    sym_target = sym_target.replace("_U_", "_D_")
            elif "_D_" in driver:
                sym_driver = sym_driver.replace("_D_", "_U_")
                if "_D_" in target:
                    sym_target = sym_target.replace("_D_", "_U_")

            sym = Switch(sym_driver, sym_target, lut_offset)
            pairs.add(tuple(sorted((switch, sym))))

        if check_switches is not None:
            for s1, s2 in pairs:
                if (s1 in check_switches) != (s2 in check_switches):
                    return False
            return True

        for switch, sym in sorted(pairs):
            if switch in self.all_switches and sym in self.all_switches:
                self.csts.append("%s - %s = 0" % (self.switch_var(switch), self.switch_var(sym)))
            elif not switch in self.all_switches:
                self.csts.append("%s = 0" % self.switch_var(sym))
            else:
                self.csts.append("%s = 0" % self.switch_var(switch))
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def add_within_fanout_symmetry_constraints(self, check_switches = None):
        """Adds constraints that enforce mirror symmetry within the fanout of each wire.

        Parameters
        ----------
        check_switches : Optional[List[Switch]], default = None
            Specifies that the routine should check if the given set
            of switches has internal fanout symmetry or not.

        Returns
        -------
        None
        """

        pairs = set()
        for switch in self.all_switches:
            driver, target, lut_offset = switch
            sym_driver = driver
            sym_target = target
            if "_R_" in driver or "_L_" in driver:
                if "_U_" in target:
                    sym_target = sym_target.replace("_U_", "_D_")
                elif "_D_" in target:
                    sym_target = sym_target.replace("_D_", "_U_")
            elif "_U_" in driver or "_D_" in driver:
                if "_R_" in target:
                    sym_target = sym_target.replace("_R_", "_L_")
                elif "_L_" in target:
                    sym_target = sym_target.replace("_L_", "_R_")

            sym = Switch(sym_driver, sym_target, lut_offset)
            if switch == sym:
                continue
            pairs.add(tuple(sorted((switch, sym))))

        if check_switches is not None:
            for s1, s2 in pairs:
                if (s1 in check_switches) != (s2 in check_switches):
                    return False
            return True

        for switch, sym in sorted(pairs):
            if switch in self.all_switches and sym in self.all_switches:
                self.csts.append("%s - %s = 0" % (self.switch_var(switch), self.switch_var(sym)))
            elif not switch in self.all_switches:
                self.csts.append("%s = 0" % self.switch_var(sym))
            else:
                self.csts.append("%s = 0" % self.switch_var(switch))
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def add_continuation_constraints(self, can_swap_lut = True, check_switches = None):
        """Adds a constraint specifying that each wire should continue to a replica of itself.

        Parameters.
        -----------
        can_swap_lut : Optional[bool], default = True
            Specifies that continuation can be at a different LUT offset.
        check_switches : Optional[List[Switch]], default = None
            Specifies that the routine should check if the given set
            of switches satisfies the continuation constraints or not.

        Returns
        -------
        None
        """

        for wire in self.wires:
            potential_switches = []
            switch = self.switch_var(Switch(wire, wire, 0))
            potential_switches.append(switch)
            cst = switch
            if can_swap_lut:
                for lut_offset in range(-1 * self.max_lut_offset, self.max_lut_offset + 1):
                    if lut_offset == 0:
                        continue
                    switch = Switch(wire, wire, lut_offset)
                    potential_switches.append(switch)
                    cst += " + %s" % self.switch_var(switch)
            cst += " >= 1"
            if check_switches is None:
                self.csts.append(cst)
            elif not any(switch in check_switches for switch in potential_switches):
                return False

        if check_switches is not None:
            return True
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def add_direction_continuation_constraints(self, check_switches = None):
        """Specifies that each wire should continue to at least one wire in the same direction.

        Parameters
        ----------
        check_switches : Optional[List[Switch]], default = None
            Specifies that the routine should check if the given set
            of switches satisfies the relaxed continuation constraints or not.

        Returns
        -------
        None
        """

        directed_wires = {'U' : [w for w in self.wires if "_U_" in w],\
                          'D' : [w for w in self.wires if "_D_" in w],\
                          'R' : [w for w in self.wires if "_R_" in w],\
                          'L' : [w for w in self.wires if "_L_" in w]}

        for d, dw in directed_wires.items():
            for wire in dw:
                potential_switches = []
                cst = ""
                for target in dw:
                    for lut_offset in range(-1 * self.max_lut_offset, self.max_lut_offset + 1):
                        switch = Switch(wire, target, lut_offset)
                        potential_switches.append(switch)
                        cst += " + %s" % self.switch_var(switch)
                cst += " >=1"
                if check_switches is None:
                    self.csts.append(cst)
                elif not any(switch in check_switches for switch in potential_switches):
                    return False

        if check_switches is not None:
            return True        
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def add_turn_forcing_constraints(self, turn_in_both_directions = True, check_switches = None):
        """Adds constraints that force each wire to turn at least once or twice.

        Parameters
        ----------
        turn_in_both_directions : Optinal[bool], default = True
            Specifies that each wire should turn in both remaining directions.
        check_switches : Optional[List[Switch]], default = None
            Specifies that the routine should check if the given set
            of switches satisfies the turning constraints or not.

        Returns
        -------
        None
        """

        directed_wires = {'U' : [w for w in self.wires if "_U_" in w],\
                          'D' : [w for w in self.wires if "_D_" in w],\
                          'R' : [w for w in self.wires if "_R_" in w],\
                          'L' : [w for w in self.wires if "_L_" in w]}

        pairs = {'U' : ('R', 'L'), 'D' : ('R', 'L'), 'R' : ('U', 'D'), 'L' : ('U', 'D')}

        for driver, fanout in pairs.items():
            for wire in directed_wires[driver]:
                potential_switches = []
                if turn_in_both_directions:
                    for fd in fanout:
                        cst = ""
                        for target in directed_wires[fd]:
                            for lut_offset in range(-1 * self.max_lut_offset, self.max_lut_offset + 1):
                                switch = Switch(wire, target, lut_offset)
                                potential_switches.append(switch)
                                cst += " + %s" % self.switch_var(switch)
                        cst += " >=1"
                        if check_switches is None:
                            self.csts.append(cst)
                        elif not any(switch in check_switches for switch in potential_switches):
                            return False
                else:
                    all_fanout = directed_wires[fanout[0]] + directed_wires[fanout[1]]
                    cst = ""
                    for target in all_fanout:
                        for lut_offset in range(-1 * self.max_lut_offset, self.max_lut_offset + 1):
                            switch = Switch(wire, target, lut_offset)
                            potential_switches.append(switch)
                            cst += " + %s" % self.switch_var(switch)
                    cst += " >=1"
                    if check_switches is None:
                        self.csts.append(cst)
                    elif not any(switch in check_switches for switch in potential_switches):
                        return False

        if check_switches is not None:
            return True
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def generate_all_offset_constraints(self):
        """Generates all offset constraints.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        for offset, hops in self.offsets.items():
            if ENFORCE_EXTERNAL_SYMMETRY and (offset[0] < 0 and offset[1] < 0):
                #NOTE: If symmetric, we can skip checking the 3rd quadrant.
                continue
            if len(self.shortest_paths[offset]) <= INDEX_THR:
                cst = ""
                for sp, sp_csts in self.shortest_paths[offset].items():
                    self.csts += sp_csts
                    self.bin_vars.append(sp)
                    cst += " + %s" % sp
                cst += " = 1"
                self.csts.append(cst)
            else:
                self.single_offset_csts(offset, hops)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def min_switch_objective(self):
        """Generates an objective that minimizes the switch count.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        objective = "Minimize\n"

        #Giving preference to some lut offsets can speed up the solution process.
        lut_offset_pondering = {0 : 1.0, 1 : 1.001, -1 : 1.002}
        
        for switch in self.all_switches:
            #objective += " + %.3f %s" % (lut_offset_pondering[switch.lut_offset], self.switch_var(switch))
            objective += " + %s" % self.switch_var(switch)

        self.objective = objective
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def max_util_objective(self, utilizations, bump_up = None, incorporate_wl = None, usage_norm = 1.0, wl_norm = 1.0,\
                           stacking = None, limit_cheby = 0):
        """Generates an objective that maximizes the switch count.

        Parameters
        ----------
        utilizations : Dict[Switch, Dict[str, int]]
            A dictionary of observed utilizations.
        bump_up : Optional[Dict[Switch, int]], default = None
            Optional bump-up dictionary used to motivate the solver to
            pick the same switches as before when they belong to the low-utilization tail.
        incorporate_wl : Optional[float], default = None
            Specifies that WL should be incorporated into the objective as well.
            If it is to be used, pass the trade-off threshold.
        usage_norm : Optional[float], default = 1.0
            Normalization factor for usage.
        wl_norm : Optional[float], default = 1.0
            Normalization factor for wirelength.
        stacking : Optional[Dict[str, Tuple[int]], default = None
            Specifies a (partial) mux location map. Can be useful for obtaining
            quick initial solutions.
        limit_cheby : Optional[int]
            Instead of locking muxes at the given positions only, it allows them to move to
            positions within Chenyshev distance limit_cheby of the initial location.

        Returns
        -------
        None
        """

        if incorporate_wl is not None:
            wl_var = self.wl_opt(lock_positions = stacking, limit_cheby = limit_cheby)
            #self.add_fanout_center_constraints()

        cst = ""
        for switch in self.all_switches:
            weight = utilizations.get(switch, {}).get("cur", 0)
            if bump_up is not None:
                weight += bump_up.get(switch, 0)
                if switch in bump_up:
                    print "bump", switch, bump_up.get(switch, 0)
            cst += " + %d %s" % (weight, self.switch_var(switch))
        cst += " - max_util = 0"
        self.csts.append(cst)

        objective = "Minimize\n"# multi-objectives\n"
        #objective += "OBJ1: Priority=2 Weight=1 AbsTol=0.0 RelTol=0.0\n"
        if incorporate_wl is not None:
            util_coeff = (1.0 - incorporate_wl) / usage_norm
            wl_coeff = float(incorporate_wl) / wl_norm
            objective += " - %g max_util + %g %s" % (util_coeff, wl_coeff, wl_var)
            #objective += "\nOBJ2: Priority=1 Weight=1 AbsTol=0.0 RelTol=0.0\n"
            #objective += self.secondary_objective
        else:
            objective = "Maximize\nmax_util"

        self.objective = objective
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def read_floorplan(self, filename):
        """Reads the mux placement from the ILP solution.

        Parameters
        ----------
        filename : str
            Solution file name.

        Returns
        -------
        Dict[str : Tuple[int]]
            Coordinates of all muxes.
        """

        pos_vars = {self.get_mux_pos_var(wire, x, y) : {wire : (x, y)}\
                    for wire in self.wires for x in range(0, MUX_COL_CNT) for y in range(0, MUX_COL_HEIGHT)}

        with open(filename, "r") as inf:
            lines = inf.readlines()

        selected = []
        rd = False
        pos_dict = {}
        for line in lines:
            if not line or line.isspace():
                continue
            if line.startswith("Variable Name"):
                rd = True
                continue
            if not rd:
                continue
            if "land" in line:
                continue
            val = line.split()[-1]
            if val.startswith("1.0") and all(c == '0' for c in val.split("1.0", 1)[-1].strip()):
                pos = pos_vars.get(line.split()[0], None)
                if pos is not None:
                    pos_dict.update(pos)

        return pos_dict
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def read_costs(self, filename):
        """Reads the usage and wirelength of the solution.

        Parameters
        ----------
        filename : str
            Solution file name.
        
        Returns
        -------
        float
            Usage.
        float
            Wirelength.
        """

        with open(filename, "r") as inf:
            lines = inf.readlines()

        for line in lines:
            if "max_util" in line:
                max_util = float(line.split()[-1])
            elif "total_wl" in line:
                total_wl = float(line.split()[-1])

        return max_util, total_wl
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def read_switches(self, filename):
        """Reads switches from a solution.

        Parameters
        ----------
        filename : str
            Solution file name.
        
        Returns
        -------
        List[Switch]
            Switch selection.
        """

        switch_vars = {self.switch_var(switch) : switch for switch in self.all_switches}

        with open(filename, "r") as inf:
            lines = inf.readlines()

        selected = []
        rd = False
        for line in lines:
            if not line or line.isspace():
                continue
            if line.startswith("Variable Name"):
                rd = True
                continue
            if not rd:
                continue
            if "land" in line:
                continue
            val = line.split()[-1]
            if val.startswith("1.0") and all(c == '0' for c in val.split("1.0", 1)[-1].strip()):
                switch = switch_vars.get(line.split()[0], None)
                if switch is not None:
                    selected.append(switch)

        return sorted(selected)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def read_stored_switches(self, filename):
        """Reads the switch pattern from a stored file.

        Parameters
        ----------
        filename : str
            Name of the file holding the stored pattern.

        Returns
        -------
        List[Switch]
            Switches.
        """

        with open(filename, "r") as inf:
            lines = inf.readlines()

        
        switches = []
        for line in lines:
            prefix, driver, target = line.split()[0].split("__")
            driver = driver.split("_tap", 1)[0]
            target = target.split("_tap", 1)[0]
            lut_offset, target = target.split('_', 1)
            lut_offset = lut_offset.split("lut", 1)[1]
            sign = 1 if lut_offset[0] == 'p' else -1
            magnitude = int(lut_offset[1:])
            lut_offset = sign * magnitude
            switches.append(Switch(driver, target, lut_offset))

        return switches
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def quench_floorplan(self, switches, floorplan):
        """Performs a quick quench of the floorplan obtained from solving an ILP.

        Parameters
        ----------
        switches : List[Switch]
            List of switches in the pattern.
        floorplan : Dict[str, Tuple[int]]
            Coordinates of all multiplexers in the solution.

        Returns
        -------
        Dict[str, Tuple[int]]
            Quenched coordinates.
        """

        #........................................................................#
        def eval_floorplan(flp):
            """Evaluates the wirelength of the floorplan.

            Parameters
            ----------
            flp : Dict[str, Tuple[int]]
                Floorplan to be evaluated.

            Returns
            -------
            float
                Wirelength.
            """

            switch_len = lambda switch : abs(flp[switch.target][0] - flp[switch.driver][0]) * MUX_WIDTH\
                       + abs(flp[switch.target][1] - flp[switch.driver][1] + switch.lut_offset * MUX_COL_HEIGHT) * MUX_HEIGHT

            return sum([switch_len(switch) for switch in switches])
        #........................................................................#

        init_wl = eval_floorplan(floorplan)
        coords = sorted(floorplan)

        random.seed(FLOORPLAN_SEED)

        init_temp_comp_moves = 1000
        deltas = []
        for i in range(0, init_temp_comp_moves):
            swap_a = random.choice(coords)
            swap_b = swap_a
            while swap_b == swap_a:
                swap_b = random.choice(coords)
            orig_a = floorplan[swap_a]
            orig_b = floorplan[swap_b]
            floorplan[swap_a] = orig_b
            floorplan[swap_b] = orig_a
            new_wl = eval_floorplan(floorplan)
            deltas.append(new_wl - init_wl)
            floorplan[swap_a] = orig_a
            floorplan[swap_b] = orig_b

        temperature = 2 * statistics.stdev(deltas)
        print temperature, init_wl

        best_wl = init_wl
        best_floorplan = copy.deepcopy(floorplan)

        move_limit = int(math.ceil(10 * len(self.wires) ** (4.0 / 3)))
        wl = init_wl
        while temperature > (0.005 * wl) / len(self.wires):
            proposed = 0
            accepted = 0
            for i in range(0, move_limit):
                swap_a = random.choice(coords)
                swap_b = swap_a
                while swap_b == swap_a:
                    swap_b = random.choice(coords)
                proposed += 1
                orig_a = floorplan[swap_a]
                orig_b = floorplan[swap_b]
                floorplan[swap_a] = orig_b
                floorplan[swap_b] = orig_a
                new_wl = eval_floorplan(floorplan)
                if new_wl < wl:
                    wl = new_wl
                    accepted += 1
                    if wl <= best_wl:
                        best_wl = wl
                        best_floorplan = copy.deepcopy(floorplan)            
                else:
                    energy = math.exp(-1 * float(new_wl - wl) / temperature)
                    toss = random.random()
                    if toss < energy:
                        wl = new_wl
                        accepted += 1
                        continue
                    floorplan[swap_a] = orig_a
                    floorplan[swap_b] = orig_b

            alpha = float(accepted) / proposed
            temp_scale_fac = 1.0
            if alpha > 0.96:
                temp_scale_fac = 0.5
            elif alpha > 0.8:
                temp_scale_fac = 0.9
            elif alpha > 0.15:
                temp_scale_fac = 0.95
            else:
                temp_scale_fac = 0.8
            temperature *= temp_scale_fac

            print temperature, wl

        print "Quenched", best_wl

        return best_floorplan
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def approximate_utilizations(self, utilizations, desired_distance):
        """Generates a random utilization assignment such that it is at a desired
        distance (or at least close to it) from the original observed utilization.
        Distance is computed as the Euclidean distance between two vectors formed
        from switch-name-sorted utilizations.

        Parameters
        ----------
        utilizations : Dict[str, Dict[str, int]]
            Switch usage dictionary.
        desired_distance : float
            Desired distance of the final vector as a fraction of the distance to all 0.

        Returns
        -------
        Dict[str, Dict[str, int]]
            Requested approximate utilizations.
        """ 

        switches = sorted(utilizations)
        orig_vec = [utilizations[sw]["cur"] for sw in switches]

        base_distance = euclidean(orig_vec, [0 for s in orig_vec])
        target_distance = desired_distance * base_distance
        print "Target distance: ", target_distance

        vec = copy.deepcopy(orig_vec)
    
        random.seed(USAGE_SEED)
        #........................................................................#
        def swap(vec):
            """Swaps a fraction of the usage between two positions in the vector.

            Parameters
            ----------
            vec : List[int]
                Vector in which the swap is to be made.

            Returns
            -------
            List[int]
                New vector.
            Dict[int, int]
                State prior to swap.
            """

            valid = False
            max_ind = len(vec) - 1
            while not valid:
                source = random.randint(0, max_ind)
                if vec[source] == 0:
                    continue
                valid = True
            sink = random.choice([i for i in range(0, len(vec)) if i != source])
            quantity = random.randint(1, vec[source])

            start_state = {source : vec[source], sink : vec[sink]}

            vec[source] -= quantity
            vec[sink] += quantity
        
            return vec, start_state
        #........................................................................#

        #........................................................................#
        def undo_move(vec, start_state):
            """Undoes a move.
    
            Parameters
            ----------
            vec : List[int]
                Vector in which the move is to be undone.
            start_state : Dict[int, int]
                State before the move.
    
            Returns
            -------
            List[int]
                Reverted vector.
            """
    
            for ind, val in start_state.items():
                vec[ind] = val
    
            return vec
        #........................................................................#

        evaluate = lambda vec : abs(euclidean(orig_vec, vec) - target_distance)

        init_distance = target_distance
        cur_distance = init_distance
        best_distance = cur_distance
        best_vec = copy.deepcopy(vec)

        init_temp_comp_moves = 1000
        deltas = []
        for i in range(0, init_temp_comp_moves):
            new_vector, restore_state = swap(vec)
            deltas.append(abs(evaluate(new_vector) - init_distance))
            undo_move(vec, restore_state)
            
        temperature = 20 * statistics.stdev(deltas)
        
        move_limit = int(math.ceil(10 * len(vec) ** (4.0 / 3)))
        while temperature > (0.005 * cur_distance) / len(vec) and best_distance > 1:
            proposed = 0
            accepted = 0
            for i in range(0, move_limit):
                new_vector, restore_state = swap(vec)
                new_distance = evaluate(new_vector)
                proposed += 1
                if new_distance < cur_distance:
                    cur_distance = new_distance
                    accepted += 1
                    if new_distance <= best_distance:
                        best_distance = new_distance
                        best_vec = copy.deepcopy(new_vector)
                else:
                    energy = math.exp(-1 * float(new_distance - cur_distance) / temperature)
                    toss = random.random()
                    if toss < energy:
                        cur_distance = new_distance
                        accepted += 1
                        continue
                    undo_move(vec, restore_state)

            alpha = float(accepted) / proposed
            temp_scale_fac = 1.0
            if alpha > 0.96:
                temp_scale_fac = 0.5
            elif alpha > 0.8:
                temp_scale_fac = 0.9
            elif alpha > 0.15:
                temp_scale_fac = 0.95
            else:
                temp_scale_fac = 0.8
            temperature *= temp_scale_fac

            print temperature, cur_distance, euclidean(orig_vec, vec) 

        print "Approximated", best_distance, euclidean(orig_vec, best_vec)

        approximate_dict = copy.deepcopy(utilizations)
        for s, switch in enumerate(switches):
            approximate_dict[switch]["cur"] = best_vec[s]

        return approximate_dict
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def parse_utilizations(self, filename):
        """Parses the postrouting utilization of switches.

        Parameters
        ----------
        filename : str
            Name of the router log.

        Returns
        -------
        Dict[Switch, int]
            Usage dictionary.
        """

        #........................................................................#
        def parse_switch(line):
            """Generates a switch from a log line.
    
            Parameters
            ----------
            line : str
                Line to be parsed.
            
            Returns
            -------
            Switch
                Parsed switch.
            """
    
            if not "potential_edge__" in line:
                return None
    
            name = line.split('(', 1)[1].split(')', 1)[0]
            prefix, driver, target = name.split("__")
            driver = driver.split("_tap", 1)[0]
            target = target.split("_tap", 1)[0]
            lut_offset, target = target.split('_', 1)
            lut_offset = lut_offset.split("lut", 1)[1]
            sign = 1 if lut_offset[0] == 'p' else -1
            magnitude = int(lut_offset[1:])
            lut_offset = sign * magnitude
    
            return Switch(driver, target, lut_offset)
        #........................................................................#
    
        #........................................................................#
        def parse_usage(line):
            """Parses usage from a log line.

            Parameters
            ----------
            line : str
                Line to be parsed.

            Returns
            -------
            Dict[str, int]
                Usage dictionary.
            """

            if not "potential_edge__" in line:
                return None
        
            usage = line.split('(')[2].split(')', 1)[0]
            cur, hist, prev = usage.split(", ")

            return {"cur" : int(cur), "hist" : int(hist), "prev" : int(prev)}
        #........................................................................#

        with open(filename, "r") as inf:
            lines = inf.readlines()

        for lcnt in range(len(lines) - 1, -1, -1):
            line = lines[lcnt]
            if line.startswith("Edge-splitter costs:"):
                break

        all_usage = {}
        for line in lines[lcnt + 1:]:
            switch = parse_switch(line)
            if not switch in self.all_switches:
                continue
            if switch is None:
                break
            usage = parse_usage(line)
            all_usage.update({switch : usage})

        return all_usage
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def fanin_greedy_preselect(self, usage, fanins, mult):
        """Greedily preselects a subset of fanin switches for each wire,
        by taking the top k * mult most used ones, where k comes from the
        fanins dictionary.

        Parameters
        ----------
        usage : Dict[Switch, Dict[str, int]]
            Postrouting usages.
        fanins : Dict[str, int]
            Desired fanin for each wire.
        mult : int
            Round-up factor for fanin switch preselection.
        
        Returns
        -------
        List[Switch]
            Preselected switches.
        """

        preselected = []
        usage = [switch for switch in sorted(usage, key = lambda s : usage[s]["cur"], reverse = True)]
        for wire, fanin in fanins.items():
            preselected_w = []
            for switch in usage:
                if len(preselected_w) >= fanin * mult:
                    break
                if switch.target == wire:
                    preselected_w.append(switch)
            preselected += preselected_w

        return preselected
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def prohibit_nonselected(self, selected_switches):
        """Prohibits all non-preselected switches.
        This is the easiest way to make sure that the remaining variables
        do not occur in any other constraints in a way that they could be 1.

        Parameters
        ----------
        selected_switches : List[Switch]
            A list of preselected switches.

        Returns
        -------
        None
        """

        for switch in self.all_switches:
            if not switch in selected_switches:
                self.csts.append("%s = 0" % self.switch_var(switch))
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def limit_lut_offset_options(self, limit):
        """Limits the LUT-offset replicas of the same base switch type.

        Parameters
        ----------
        limit : int
            Maximum number of replicas.

        Returns
        -------
        None
        """

        for switch in self.all_switches:
            if switch.lut_offset == 0:
                cst = ""
                for lut_offset in range(-1 * self.max_lut_offset, self.max_lut_offset + 1):
                    cst += " + %s" % self.switch_var(Switch(switch.driver, switch.target, lut_offset))
                cst += " <= %d" % limit
                self.csts.append(cst)
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def write_problem(self, filename):
        """Writes out the problem.

        Parameters
        ----------
        filename : str
            Name of the output file.

        Returns
        -------
        None
        """

        for ccnt, cst in enumerate(self.csts):
            self.csts[ccnt] = "C%d: %s" % (ccnt, cst) 
        with open(filename, "w") as outf:
            outf.write(self.objective)
            outf.write("\nSubject to\n")
        
            #import ast
            #with open("store", "r") as inf:
            #    lines  = inf.readlines()
            #    sws = []
            #    for line in lines:
            #        drvr = line.split("driver='", 1)[1].split("'", 1)[0]
            #        trgt = line.split("target='", 1)[1].split("'", 1)[0]
            #        offset = int(line.split("lut_offset=", 1)[1].split(")", 1)[0])
            #        sws.append(Switch(drvr, trgt, offset))

            #self.csts += ["%s = 1" % self.switch_var(sw) for sw in sws]
            #self.csts += ["%s = 0" % self.switch_var(sw) for sw in self.all_switches if not sw in sws]

            outf.write("\n".join(self.csts))
            if self.user_cuts:
                outf.write("\nUser Cuts\n")
                outf.write("\n".join(self.user_cuts))
            if self.lazy_csts:
                for ccnt, cst in enumerate(self.lazy_csts):
                    self.lazy_csts[ccnt] = "L%d: %s" % (ccnt, cst) 
                outf.write("\nLazy Constraints\n")
                outf.write("\n".join(self.lazy_csts))
            if self.bounds:
                outf.write("\nBounds\n")
                outf.write("\n".join(self.bounds))
            if not LP_RELAX:
                outf.write("\nBinary\n")
                outf.write("\n".join(self.bin_vars))
                if self.general_vars:
                    outf.write("\nGeneral\n")
                    outf.write("\n".join(self.general_vars))
            else:
                if not self.bounds:
                    outf.write("\nBounds\n")
                else:
                    outf.write("\n")
                outf.write("\n".join(["0 <= %s <= 1" % var for var in self.bin_vars]))
            outf.write("\nEnd")
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def set_adopted_switches(self, switches):
        """Sets adopted switches to one.

        Parameters
        ----------
        switches : List[Switch]
            Switches to be set.
        
        Returns
        -------
        None
        """

        for switch in switches:
            self.csts.append("%s = 1" % self.switch_var(switch))
    #------------------------------------------------------------------------#

    #------------------------------------------------------------------------#
    def bound_solution_overlap(self, solutions, min_overlap, max_overlap):
        """Sets constraints on the amount of overlap between the solution of the
        current problem and the previous solutions.

        Parameters
        ----------
        solutions : List[List[Switch]]
            List of previos solutions overlap with which needs to be bounded.
        min_overlap : int
            Minimum overlap.
        max_overlap : int
            Maximum overlap.

        Returns
        -------
        None
        """

        for solution in solutions:
            cst = ""
            for switch in solution:
                cst += "+ %s" % self.switch_var(switch)
            if min_overlap > 0:
                self.csts.append(cst + " >= %d" % min_overlap)
            if max_overlap > 0:
                self.csts.append(cst + " <= %d" % max_overlap)
    #------------------------------------------------------------------------#
##########################################################################

##########################################################################
def solve_log(filename, bump_up = None, solutions_to_ban = None, min_ban_difference = None):
    """Constructs a problem for one VPR log and solves it.

    Parameters
    ----------
    filename : str
        Name of the VPR log file.
    bump_up : Optional[Dict[Switch, int]], default = None
        Optional bump-up dictionary used to motivate the solver to
        pick the same switches as before when they belong to the low-utilization tail.
    solutions_to_ban : List[List[Switch]]
        List of solutions to ban.
    min_ban_difference : int
        Minimum number of switches in which the solution must differ from a banned one,
        to consider the ban successful.

    Returns
    -------
    List[Switch]
        Solution.
    Dict[Switch, Dict[str, int]]
        Usages.
    """

    prob = OptimalDistances(wires, MAX_LUT_OFFSET)

    usage = prob.parse_utilizations(filename)

    if APPROXIMATE_USAGE:
        usage = prob.approximate_utilizations(usage, APPROXIMATE_USAGE)

    usage_norm, wl_norm, default_stacking = prob.assemble_greedy_solution(usage)
    norm_norm = float(max(usage_norm, wl_norm))
    usage_norm /= norm_norm
    wl_norm /= norm_norm

    prev_usage_norm = usage_norm
    prev_wl_norm = wl_norm

    stacking = default_stacking

    for quench in range(0, 5 if WL_TRADEOFF else 1):
        del prob
        prob = OptimalDistances(wires, MAX_LUT_OFFSET)
        if solutions_to_ban is not None:
            banned_solution_size = max([len(bsol) for bsol in solutions_to_ban])
            max_overlap = banned_solution_size - min_ban_difference
            prob.bound_solution_overlap(solutions_to_ban, -1, max_overlap)

        prob.max_util_objective(usage, bump_up = None, incorporate_wl = WL_TRADEOFF, usage_norm = usage_norm, wl_norm = wl_norm,\
                                stacking = stacking, limit_cheby = 0)

        if ENFORCE_HOP_OPTIMALITY:
            prob.get_optimal_hop_counts((12, 8))
            prob.generate_all_offset_constraints()
        if ENFORCE_FANIN: 
            prob.force_concrete_fanins({wire : DEFAULT_FANIN for wire in prob.wires})
        if ENFORCE_FANOUT:
            prob.force_concrete_fanouts({wire : DEFAULT_FANOUT for wire in prob.wires})
        if LIMIT_MUX_SIZE_NUMBER > 0:
            prob.generate_different_mux_size_bounding_constraints(ALLOWED_MUX_SIZES, LIMIT_MUX_SIZE_NUMBER) 
        if LIMIT_FANOUT_SIZE_NUMBER > 0:
            prob.generate_different_mux_size_bounding_constraints(ALLOWED_FANOUT_SIZES, LIMIT_MUX_SIZE_NUMBER, bound_fanout = True) 
        if ENFORCE_MUX_PAIR_INPUT_SHARE > 0:
            prob.force_mux_pair_input_sharing(ENFORCE_MUX_PAIR_INPUT_SHARE)
        if MAX_SWITCH_NUMBER > 0:
            prob.limit_pattern_size(MAX_SWITCH_NUMBER)
        if ENFORCE_EXTERNAL_SYMMETRY: 
            prob.add_symmetry_constraints()
        if ENFORCE_INTERNAL_SYMMETRY:
            prob.add_within_fanout_symmetry_constraints()
        if ENFORCE_CONTINUATION:
            prob.add_continuation_constraints()
        elif ENFORCE_RELAXED_CONTINUATION:
            prob.add_direction_continuation_constraints()
        if ENFORCE_TWO_TURNS:
            prob.add_turn_forcing_constraints()
        elif ENFORCE_ONE_TURN:
            prob.add_turn_forcing_constraints(turn_in_both_directions = False)

        ##prob.min_switch_objective()
        ##prob.force_same_fanin(within_direction_only = False)
        ##prob.force_same_fanout(within_direction_only = False)
    
    
        adopted = [switch for switch in prob.all_switches if not switch in usage]
        prob.set_adopted_switches(adopted)
        print "Adopted =", adopted
    
        prob.write_problem("prob.lp")
        sol_filename = "prob.log"
    
        timeout = 3600
        call = "cplex -c \"set timelimit %d\" " % timeout
        if SRV:
            call = "%s -c \"set timelimit %d\" " % (cplex_path, timeout)
    
        #Optional:
        #call += "\" set mip interval 1\" "
        #call += "\" set mip strategy search 1\" "
        #call += "\" set mip strategy heuristicfreq -1\" "
        #call += "\" set mip strategy variableselect 4\" "
        #call += "\" set mip strategy startalgorithm 4\" "
        #call += "\" set mip strategy subalgorithm 4\" "
        ###
    
        call += "\"read prob.lp\" "
        call += "\"read prob.mst\" "
        call += "\"optimize\" \"set logfile %s\" " % sol_filename
        call += "\"display solution variables *\" "
        call += "\"set output writelevel 4\" "
        call += "\"write prob.mst\" "
        call += "\"quit\" "

        try:
            repair_mst_indices("prob.lp", "prob.mst")
        except:
            pass

        os.system(call)
    
        sol_switches = prob.read_switches(sol_filename)
        floorplan = prob.read_floorplan(sol_filename)

        try:
            usage_norm, wl_norm = prob.read_costs(sol_filename)
        except:
            #No switches with non-zero usage chosen (CPLEX does not display 0 variables by default).
            #Converged. Exit.

            return None, None

        norm_norm = float(max(usage_norm, wl_norm))
        usage_norm /= norm_norm
        wl_norm /= norm_norm

        stacking = prob.quench_floorplan(sol_switches, floorplan)
    
        if ENFORCE_HOP_OPTIMALITY and not prob.check_optimality(sol_switches):
            print "Optimality check failed"
            raise ValueError
    
        os.system("rm -f prob.log prob.lp")
    
        #print "Pattern size:", len(sol_switches)
        #for switch in sorted(sol_switches, key = lambda s : usage.get(s, {}).get("cur", 1000)):
        #    print prob.switch_var(switch), switch, usage.get(switch, {}).get("cur", 1000)

        tol = 0.001
        if abs(usage_norm - prev_usage_norm) / float(prev_usage_norm) < tol\
           and abs(wl_norm - prev_wl_norm) / float(prev_wl_norm) < tol:
            return sol_switches, usage

        prev_usage_norm = usage_norm
        prev_wl_norm = wl_norm
    
    return sol_switches, usage
##########################################################################

##########################################################################
def generate_multiple_different_solutions(vpr_log_filename, solution_number, min_diff = 5):
    """Generates a desired number of different solutions by repeatedly calling the solver
    and prohibiting the previously encountered solutions.

    Parameters
    ----------
    vpr_log_filename : str
        Name of the VPR log file holding the original utilizations.
    solution_number : int
        Required number of solutions.
    min_diff : Optional[int], default = 5
        Minimum number of switches in which each new solution must differ from any other to
        be accepted.

    Returns
    -------
    List[List[Switch]]
        Obtained solutions.
    """

    solutions = []
    for i in range(0, solution_number):
        os.system("rm -f prob.mst")
        if solutions:
            switches, usage = solve_log(vpr_log_filename, solutions_to_ban = solutions, min_ban_difference = min_diff)
        else:
            switches, usage = solve_log(vpr_log_filename)
        print "Solution %d" % i
        solutions.append(switches)
    
    return solutions
##########################################################################

##########################################################################
def analyze_similarity(solutions):
    """Analyzes set-similarity of the solution list.

    Parameters
    ----------
    solutions : List[List[Switch]]
        Solution list. The original-utilization solution is assumed to be the
        first one in the list.

    Returns
    -------
    float
        Mean set difference (size-intersection) from the original-utilization solution.
    float
        Standard deviation of the set difference from the original-utilization solution.
    """

    set_differences = [len(solutions[0]) for solution in solutions]
    for s, solution in enumerate(solutions):
        set_differences[s] -= len(set(solutions[0]).intersection(set(solution)))

    return numpy.mean(set_differences), numpy.std(set_differences)
##########################################################################

##########################################################################
def repair_mst_indices(prob_file, mst_file):
    """Repairs the indices of the variables in the mst file, so that they conform
    to the new indices in the problem file.

    Parameters
    ----------
    prob_file : str
        Name of the new problem file.
    mst_file : str
        Name of the stored solution file.

    Returns
    -------
    None
    """

    with open(prob_file, "r") as inf:                                                                                                     
        txt = inf.read()
    
    variables = [v for v in txt.split() if v and not v.isspace()]
    
    seen = set()
    vcnt = 0
    clean = {}
    for v in txt.split():
        if not v or v.isspace():
            continue
        if v in ('+', '-', "to"):
            continue
        if "=" in v:
            continue
        try:
            v = float(v)
            continue
        except:
            pass
        if v[0] != v.lower()[0]:
            continue
        if v in seen:
            continue
        clean.update({v : vcnt})
        vcnt += 1
        seen.add(v)

    get_index = lambda line : line.split("index=\"", 1)[1].split('"', 1)[0]
    get_name = lambda line : line.split("name=\"", 1)[1].split('"', 1)[0]
    get_value = lambda line : line.split("value=\"", 1)[1].split('"', 1)[0]
    with open(mst_file, "r") as inf:
        lines = inf.readlines()
    txt = ""
    for line in lines:
        try:
            index = get_index(line)
        except:
            txt += line
            continue
        try:
            line = line.replace(" index=\"%s\" " % index, " index=\"%d\" " % clean[get_name(line)])
        except:
            continue
        line = line.replace(" value=\"%s\"" % get_value(line), " value=\"1\"")
        txt += line

    with open(mst_file, "w") as outf:
        outf.write(txt)
##########################################################################

##########################################################################
def check_features(stored_pattern_filename, log_filename = None, problem_obj = None):
    """Checks which features the given stored pattern possesses.

    Parameters
    ----------
    stored_pattern_filame : str
        Name of the file in which the pattern has been stored.
    log_filename : Optional[str], default = None
        Name of the file in which to store the features.
    problem_obj : Optional[OptimalDistances], default = None
        Pass a constructed object with optimal hop distances, which removes the need for
        computing them again.

    Returns
    -------
    Dicts[str, bool]
        Dictionary of features.

    Notes
    -----
    Currently supported features:
        1) Hop optimality
        2) Symmetric wires have mutually symmetric fanouts
        3) Each wire has a symmetric fanout
        4) Each wire continues onto a copy of itself
        5) Each wire continues to any wire in its direction
        6) Each wire turns to both remaining sides
        7) Each wire turns to at least one remaining side
    """

    if problem_obj is None:
        prob = OptimalDistances(wires, MAX_LUT_OFFSET)
        hop_optimality_test_distance = 50
        prob.get_optimal_hop_counts((hop_optimality_test_distance, hop_optimality_test_distance), check_only = True)
    else:
        prob = problem_obj

    switches = prob.read_stored_switches(stored_pattern_filename)

    features = {}
    features.update({"hop_optimality" : prob.check_optimality(switches)})
    features.update({"external_symmetry" : prob.add_symmetry_constraints(check_switches = switches)})
    features.update({"internal_symmetry" : prob.add_within_fanout_symmetry_constraints(check_switches = switches)})
    features.update({"continuation" : prob.add_continuation_constraints(check_switches = switches)})
    features.update({"relaxed_continuation" : prob.add_direction_continuation_constraints(check_switches = switches)})
    features.update({"two_turns" : prob.add_turn_forcing_constraints(turn_in_both_directions = True, check_switches = switches)})
    features.update({"one_turn" : prob.add_turn_forcing_constraints(turn_in_both_directions = False, check_switches = switches)})

    if log_filename is not None:
        with open(log_filename, "w") as outf:
            outf.write(str(features))

    return features
##########################################################################

if __name__ == "__main__":
    
    
    switch_out = lambda switch : "potential_edge__%s%s__lut%s%d_%s%s" % (switch.driver, "_tap_0" if 'V' in switch.driver else "",\
                                                                         'p' if switch.lut_offset >= 0 else 'm',\
                                                                         abs(switch.lut_offset), switch.target,\
                                                                         "_tap_0" if 'V' in switch.target else "")
       
    if args.vpr_log is not None:
        switches, usage = solve_log(args.vpr_log)
        txt = ""
        if usage is None:
            txt = "Converged "
        else:
            for switch in switches:
                txt += "%s %s\n" % (switch_out(switch), str(usage.get(switch, {}).get("cur", "adopted")))
        with open(args.vpr_log.replace("vpr", "ilp"), "w") as outf:
            outf.write(txt[:-1])
