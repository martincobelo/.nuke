#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script modifies "Select All" to be context aware. 
                 For example, if you try to select all over a backdrop,
                 it will select all nodes within that backdrop (including the backdrop)
                 If you run select all over nothing, it will select everything, as it would normally
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
    VERSION:     01.01
    PUBLISHED:   2025-09-01
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

#===============================================================================
#                       ---- Scripts ----
#===============================================================================

def _get_node_bounds(node):
    """Gets the bounding box of a node"""
    x1 = node.xpos()
    y1 = node.ypos()
    
    if node.Class() == 'BackdropNode':
        x2 = x1 + node.knob('bdwidth').value()
        y2 = y1 + node.knob('bdheight').value()
    else:
        x2 = x1 + node.screenWidth()
        y2 = y1 + node.screenHeight()
        
    return x1, y1, x2, y2

def _select_backdrop_and_contents(backdrop, select_contents=True, current_selection=None):
    """
    Selects the backdrop and handles contents based on arguments

    Args:
        backdrop: The backdrop node to select
        select_contents: If True also selects all nodes on the backdrop
        current_selection:  The list of nodes that were selected before this function was called
                            Used to preserve selection for iterative calls
    """
    if not backdrop:
        return
        
    for node in nuke.allNodes():
        node['selected'].setValue(False)
        
    backdrop['selected'].setValue(True)
    
    # --- [ Conditionally select the nodes on the backdrop ] ---
    if select_contents:
        backdrop.selectNodes(True)
    elif current_selection:
        # --- [ Reselect the previously selected backdrop for iterative selection ] ---
        for node in current_selection:
            if nuke.exists(node.name()):
                node['selected'].setValue(True)


def smart_select_all(select_contents=True):
    """
    Selects the most relevant backdrop and optionally its contents

    #1 If nothing is selected, check for backdrop under the mouse cursor. If none is found, select all nodes
    #2 If nodes are selected, find the smallest backdrop that fully contains them
    #3 If select_contents is False and no parent backdrop is found, selects all backdrops contained within the current selection

    select_contents (bool): If True selects the backdrop and all nodes on it 
                            If False, selects only the backdrop node
    """
    selection = nuke.selectedNodes()
    all_backdrops = nuke.allNodes('BackdropNode')
    candidate_backdrops = []

    if not selection:
        # --- [ Condition #1: Nothing is selected ] ---
        temp_dot = nuke.createNode('Dot', inpanel=False)
        dot_x = temp_dot.xpos() + temp_dot.screenWidth() / 2
        dot_y = temp_dot.ypos() + temp_dot.screenHeight() / 2
        nuke.delete(temp_dot)

        for bd in all_backdrops:
            bd_x1, bd_y1, bd_x2, bd_y2 = _get_node_bounds(bd)
            if bd_x1 < dot_x < bd_x2 and bd_y1 < dot_y < bd_y2:
                candidate_backdrops.append(bd)
    else:
        # --- [ Conditions #2 + #3: Nodes are selected ] ---
        for bd in all_backdrops:
            if bd in selection:
                continue

            bd_x1, bd_y1, bd_x2, bd_y2 = _get_node_bounds(bd)
            is_fully_contained = True
            for node in selection:
                node_x1, node_y1, node_x2, node_y2 = _get_node_bounds(node)
                if not (node_x1 >= bd_x1 and node_x2 <= bd_x2 and node_y1 >= bd_y1 and node_y2 <= bd_y2):
                    is_fully_contained = False
                    break
            
            if is_fully_contained:
                candidate_backdrops.append(bd)

    # --- [ Final Selection Logic ] ---
    if candidate_backdrops:
        candidate_backdrops.sort(key=lambda bd: bd.knob('bdwidth').value() * bd.knob('bdheight').value())
        smallest_backdrop = candidate_backdrops[0]
        _select_backdrop_and_contents(smallest_backdrop, select_contents, selection)
    else:
        if not select_contents and selection:
            contained_backdrops = []
            selected_parent_backdrops = [node for node in selection if node.Class() == 'BackdropNode']
            
            if selected_parent_backdrops:
                all_child_candidates = [bd for bd in nuke.allNodes('BackdropNode') if bd not in selected_parent_backdrops]

                for parent_bd in selected_parent_backdrops:
                    parent_x1, parent_y1, parent_x2, parent_y2 = _get_node_bounds(parent_bd)
                    for child_bd in all_child_candidates:
                        if child_bd in contained_backdrops:
                            continue

                        child_x1, child_y1, child_x2, child_y2 = _get_node_bounds(child_bd)
                        
                        if (child_x1 >= parent_x1 and child_x2 <= parent_x2 and
                            child_y1 >= parent_y1 and child_y2 <= parent_y2):
                            contained_backdrops.append(child_bd)
                
                if contained_backdrops:
                    for n in nuke.allNodes():
                        n['selected'].setValue(False)
                    
                    for n in selected_parent_backdrops + contained_backdrops:
                        n['selected'].setValue(True)
                    return

        nuke.selectAll()