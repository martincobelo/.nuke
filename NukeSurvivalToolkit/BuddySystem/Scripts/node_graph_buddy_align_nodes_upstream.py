#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script aligns nodes based on the top most node in the tree
                 The top most is either the last node up a pipe, 
                 or the first node with a right angled input 0, or is a stamp
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

#===============================================================================
#                       ---- Scripts ----
#===============================================================================

def align_upstream_nodes():
    """
    Smart align that travels up stream of the selected node and aligns
    If it hits a stamp or 90 angle it will stop and align to that node
    """
    
    # --- [ The minimum vertical space to leave between each node ] ---
    VERTICAL_PADDING = 5 

    try:
        selected_node = nuke.selectedNode()
    except ValueError:
        nuke.message("Please select a node to preform upstream alignment.")
        return

    # --- [ Gather all nodes to be aligned ] ---
    nodes_to_align = []
    current_node = selected_node
    while current_node:
        if current_node != selected_node:
            previous_node = nodes_to_align[-1]
            prev_center_y = previous_node.ypos() + (previous_node.screenHeight() / 2)
            curr_center_y = current_node.ypos() + (current_node.screenHeight() / 2)
            
            # --- [ Break if right angle ] ---
            if int(prev_center_y) == int(curr_center_y):
                break

        nodes_to_align.append(current_node)

        node_class = current_node.Class()
        is_stamp_node = current_node.name().lower().startswith('stamp')
        
        # --- [ Break if stamp ] ---
        if is_stamp_node and node_class in ('NoOp', 'PostageStamp', 'DeepExpression'):
            break
        
        current_node = current_node.input(0)

    if not nodes_to_align:
        return
        
    # --- [ Get the top most node ] ---
    top_most_node = nodes_to_align[-1]
    target_center_x = top_most_node.xpos() + (top_most_node.screenWidth() / 2)


    # --- [ Automatically fix node overlaps ] ---
    if len(nodes_to_align) > 1:
        nodes_to_align.reverse()
        for i in range(1, len(nodes_to_align)):
            upper_node = nodes_to_align[i-1]
            lower_node = nodes_to_align[i]
            target_y = upper_node.ypos() + upper_node.screenHeight() + VERTICAL_PADDING
            if lower_node.ypos() < target_y:
                lower_node.setYpos(target_y)
        nodes_to_align.reverse()

    # --- [ Align horizontal ] ---
    for node in nuke.selectedNodes():
        node['selected'].setValue(False)

    for node in nodes_to_align:
        try:
            node_width = node.screenWidth()
            new_x_pos = target_center_x - (node_width / 2)
            node.setXpos(int(new_x_pos))
            node['selected'].setValue(True)
        except Exception as e:
            print("Could not align node for some silly reason. Please investigate at your leisure {}: {}".format(node.name(), e))