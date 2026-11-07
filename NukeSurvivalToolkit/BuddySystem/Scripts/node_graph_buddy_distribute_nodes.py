#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script can distribute nodes individually, or by clusters 
                 Additionally if the nodes are already distributed, it will align them
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
    VERSION:     01.01
    PUBLISHED:   2025-07-12
    DOCS:        https://www.hiramgifford.com/buddy-system/node-graph-buddy

"""
#==============================================================================
#                       ---- How To Install ----
#==============================================================================
"""
    Step #0:     See installation instructions for BuddySystem
"""
#===============================================================================
#                          ---- Imports ----
#===============================================================================

import nuke
import math 

#===============================================================================
#                       ---- Scripts ----
#===============================================================================

# --- [ Helper Class ] ---
class NodeCluster(object):
    """A helper class to treat a group of connected nodes as a single entity"""
    def __init__(self, nodes):
        self.nodes = nodes if nodes else []
        self._x = 0; self._y = 0; self._width = 0; self._height = 0
        self.rel_positions = {}
        self.calculate_bounds()

    def calculate_bounds(self):
        if not self.nodes: return
        all_x = [n.xpos() for n in self.nodes]
        all_y = [n.ypos() for n in self.nodes]
        min_x = min(all_x)
        max_x = max([n.xpos() + n.screenWidth() for n in self.nodes])
        min_y = min(all_y)
        max_y = max([n.ypos() + n.screenHeight() for n in self.nodes])

        self._x, self._y = min_x, min_y
        self._width, self._height = max_x - min_x, max_y - min_y

        for n in self.nodes:
            self.rel_positions[n] = (n.xpos() - self._x, n.ypos() - self._y)

    def xpos(self): return self._x
    def ypos(self): return self._y
    def screenWidth(self): return self._width
    def screenHeight(self): return self._height
    def name(self): return "NodeCluster"
    def Class(self): return "NodeCluster"

    def setXpos(self, new_x):
        self._x = int(round(new_x))
        for node, rel_pos in self.rel_positions.items():
            node.setXpos(self._x + rel_pos[0])

    def setYpos(self, new_y):
        self._y = int(round(new_y))
        for node, rel_pos in self.rel_positions.items():
            node.setYpos(self._y + rel_pos[1])

# --- [ Helper Functions ] ---
def find_node_clusters(nodes):
    """Uses BFS to find groups of visually connected nodes within a given list of nodes"""
    clusters, nodes_set, visited = [], set(nodes), set()
    for node in nodes:
        if node in visited: continue
        current_cluster, q, head = set(), [node], 0
        visited.add(node)
        while head < len(q):
            current_node = q[head]; head += 1
            current_cluster.add(current_node)
            dependencies = current_node.dependencies(nuke.INPUTS) or []
            dependents = current_node.dependent(nuke.INPUTS, False) or []
            for neighbor in dependencies + dependents:
                if neighbor in nodes_set and neighbor not in visited:
                    visited.add(neighbor); q.append(neighbor)
        clusters.append(list(current_cluster))
    return clusters

def move_children(backdrop_node, child_map):
    """Ensure all the nodes inside the Backdrops move along with them"""
    if backdrop_node in child_map:
        for child_info in child_map[backdrop_node]:
            child_node, rel_x, rel_y = child_info['node'], child_info['rel_x'], child_info['rel_y']
            child_node.setXpos(int(backdrop_node.xpos() + rel_x))
            child_node.setYpos(int(backdrop_node.ypos() + rel_y))

def check_if_gaps_are_even(sorted_nodes, is_horizontal, tolerance=2.0):
    """Checks if the gaps between a sorted list of nodes are all equal"""
    if len(sorted_nodes) < 3:
        return True

    gaps = []
    try:
        if is_horizontal:
            for i in range(len(sorted_nodes) - 1):
                prev_node = sorted_nodes[i]
                curr_node = sorted_nodes[i+1]
                gap = curr_node.xpos() - (prev_node.xpos() + prev_node.screenWidth())
                gaps.append(gap)
        else: 
            for i in range(len(sorted_nodes) - 1):
                prev_node = sorted_nodes[i]
                curr_node = sorted_nodes[i+1]
                gap = curr_node.ypos() - (prev_node.ypos() + prev_node.screenHeight())
                gaps.append(gap)
    except (AttributeError, TypeError):
        return False

    if not gaps:
        return True

    first_gap = gaps[0]
    for gap in gaps[1:]:
        if math.fabs(gap - first_gap) > tolerance:
            return False
            
    return True

# --- [ Main Function ] ---
def auto_distribute_nodes(align=False, process_clusters=False):
    """
    Checks what type of nodes you are selecting and preforms the appropriate function
    Backdrops: Will treat each Backdrop as a single item, keeping the relative position of all the nodes inside each
    Node Clusters: Finds clusters of connected nodes. Then treats each of these as a single object to be adjusted
    Individual Nodes: If neither of the above conditions is met, it will adjust every selected node as an individual
    Direction: If selection is wider than tall, adjust horizontally. Taller than wide adjust vertically 
    """
    all_raw_nodes = nuke.selectedNodes()
    if not all_raw_nodes: 
        nuke.message("No nodes selected.\nPlease select some to auto distribute")
        return
    
    child_map, nodes_to_process, process_mode = {}, [], 'nodes'

    selected_backdrops = [n for n in all_raw_nodes if n.Class() == 'BackdropNode']

    if selected_backdrops:
        process_mode = 'backdrops'
        nodes_to_process = selected_backdrops
        for bd in selected_backdrops:
            child_map[bd] = [{'node': child, 'rel_x': child.xpos() - bd.xpos(), 'rel_y': child.ypos() - bd.ypos()} for child in bd.getNodes()]
    else:
        if process_clusters:
            clusters = find_node_clusters(all_raw_nodes)
            if len(clusters) > 1:
                process_mode = 'clusters'
                nodes_to_process = [NodeCluster(c) for c in clusters]
            else: 
                process_mode = 'nodes'
                nodes_to_process = all_raw_nodes
        else:
            process_mode = 'nodes'
            nodes_to_process = all_raw_nodes

    if len(nodes_to_process) < 2:
        nuke.message("Please select at least 2 nodes to auto distribute")
        return

    valid_nodes = []
    for node in nodes_to_process:
        try: _ = node.xpos(); _ = node.ypos(); _ = node.screenWidth(); _ = node.screenHeight(); valid_nodes.append(node)
        except AttributeError: 
            continue
    if len(valid_nodes) < 2: 
        return
    selected_nodes = valid_nodes

    l_node = min(selected_nodes, key=lambda n: (n.xpos(), n.ypos()))
    r_node = max(selected_nodes, key=lambda n: (n.xpos(), n.ypos()))
    t_node = min(selected_nodes, key=lambda n: (n.ypos(), n.xpos()))
    b_node = max(selected_nodes, key=lambda n: (n.ypos(), n.xpos()))
    
    sel_w = (r_node.xpos() + r_node.screenWidth()) - l_node.xpos()
    sel_h = (b_node.ypos() + b_node.screenHeight()) - t_node.ypos()

    dist_h = sel_w >= sel_h
    action_type = "distribute_only"
    if align:
        sorted_nodes = sorted(selected_nodes, key=lambda n: n.xpos()) if dist_h else sorted(selected_nodes, key=lambda n: n.ypos())
        is_dist = check_if_gaps_are_even(sorted_nodes, is_horizontal=dist_h)
        if is_dist and len(selected_nodes) > 1:
            action_type = "align_only"
            
    # --- [ Horizontal ] ---
    if dist_h: 
        nodes_dist = sorted([n for n in selected_nodes if n != l_node and n != r_node], key=lambda n: n.xpos())
        if action_type == "distribute_only":
            if l_node == r_node and len(selected_nodes) > 1: 
                return
            nuke.Undo().begin("Distribute Horizontally")
            try:
                if nodes_dist:
                    l_b, r_b = l_node.xpos() + l_node.screenWidth(), r_node.xpos()
                    avail_w, tot_inter_w = r_b - l_b, sum([n.screenWidth() for n in nodes_dist])
                    gap_space, num_gaps = avail_w - tot_inter_w, len(nodes_dist) + 1
                    gap_size = float(gap_space) / num_gaps if num_gaps > 0 else 0
                    curr_x = float(l_b) + gap_size
                    for node in nodes_dist:
                        node.setXpos(int(round(curr_x))); node.setYpos(node.ypos())
                        if process_mode == 'backdrops': move_children(node, child_map)
                        curr_x += node.screenWidth() + gap_size
            except Exception as e: nuke.error("Error: {}".format(e))
            finally: nuke.Undo().end()
        elif action_type == "align_only":
            nuke.Undo().begin("Align Horizontally")
            try:
                align_y = l_node.ypos() + (l_node.screenHeight() / 2.0)
                for node in selected_nodes:
                    node.setYpos(int(round(align_y - (node.screenHeight() / 2.0))))
                    if process_mode == 'backdrops': move_children(node, child_map)
            except Exception as e: nuke.error("Error: {}".format(e))
            finally: nuke.Undo().end()
            
    # --- [ Vertical ] ---        
    else: 
        nodes_dist = sorted([n for n in selected_nodes if n != t_node and n != b_node], key=lambda n: n.ypos())
        if action_type == "distribute_only":
            if t_node == b_node and len(selected_nodes) > 1:
                return
            nuke.Undo().begin("Distribute Vertically")
            try:
                if nodes_dist:
                    t_b, b_b = t_node.ypos() + t_node.screenHeight(), b_node.ypos()
                    avail_h, tot_inter_h = b_b - t_b, sum([n.screenHeight() for n in nodes_dist])
                    gap_space, num_gaps = avail_h - tot_inter_h, len(nodes_dist) + 1
                    gap_size = float(gap_space) / num_gaps if num_gaps > 0 else 0
                    curr_y = float(t_b) + gap_size
                    for node in nodes_dist:
                        node.setYpos(int(round(curr_y))); node.setXpos(node.xpos())
                        if process_mode == 'backdrops': move_children(node, child_map)
                        curr_y += node.screenHeight() + gap_size
            except Exception as e: nuke.error("Error: {}".format(e))
            finally: nuke.Undo().end()
        elif action_type == "align_only":
            nuke.Undo().begin("Align Vertically")
            try:
                align_x = t_node.xpos() + (t_node.screenWidth() / 2.0)
                for node in selected_nodes:
                    node.setXpos(int(round(align_x - (node.screenWidth() / 2.0))))
                    if process_mode == 'backdrops': move_children(node, child_map)
            except Exception as e: nuke.error("Error: {}".format(e))
            finally: nuke.Undo().end()