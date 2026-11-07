#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script allows you to modify backdrops,
                 and generally organize them via hotkeys
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
#                          ---- Sort Backdrops By Size ----
#===============================================================================    

def sort_backdrops_by_size_and_zorder():
    """
    Sorts the selected backdrops by size and z order
    Smaller backdrops will have higher z_orders than the larger ones, so they don't get lost
    """
    bds = [n for n in nuke.selectedNodes() if n.Class()=='BackdropNode']
    if not bds:
        nuke.message("No backdrops selected.\nPlease select some to sort z_order by size")
        return

    bds_sorted = sorted(bds, key=lambda bd: bd['bdwidth'].value() * bd['bdheight'].value())
    bds_desc = list(reversed(bds_sorted))

    try:
        base_z = int(bds_desc[0]['z_order'].value())
    except Exception:
        base_z = 0

    for idx, bd in enumerate(bds_desc):
        bd['z_order'].setValue(base_z + idx)

#===============================================================================
#                          ---- Adjust Font Size ----
#===============================================================================	

def adjust_font_size(mode):
    """Allows you to change the label font size"""
    increment = 10 if mode == "Increase" else -10
    for bd in nuke.selectedNodes():
        if bd.Class() == "BackdropNode":
            current_value = bd['note_font_size'].value()
            new_value = max(11, current_value + increment)
            bd['note_font_size'].setValue(new_value)

#===============================================================================
#                          ---- Adjust Z Order ----
#===============================================================================
			
def adjust_z_order(mode):
    """Allows you to adjust the z order"""
    increment = 1 if mode == "Increase" else -1
    for bd in nuke.selectedNodes():
        if bd.Class() == "BackdropNode":
            current_value = bd['z_order'].value()
            new_value = current_value + increment
            bd['z_order'].setValue(new_value)

#===============================================================================
#                          ---- Resize Backdrop To Selected Nodes ----
#===============================================================================            

def resize_backdrop(padding):
    """
    Resizes the last selected backdrop to fit around selected nodes
    Also checks for other selected backdrops and sets the z_order one lower
    """
    all_selected_nodes = nuke.selectedNodes()

    # --- [ Get the nodes ] ---
    selected_backdrops = [node for node in all_selected_nodes if isinstance(node, nuke.BackdropNode)]
    selected_other_nodes = [node for node in all_selected_nodes if not isinstance(node, nuke.BackdropNode)]

    if not selected_backdrops:
        nuke.message("No Backdrop node selected.")
        return

    if not selected_other_nodes:
        nuke.message("No nodes selected to resize the backdrop around.")
        return

    # --- [ Z-Order Logic ] ---
    backdrop_to_resize = selected_backdrops[0]
    other_backdrops = selected_backdrops[1:]

    if other_backdrops:
        try:
            z_orders = [bd['z_order'].value() for bd in other_backdrops]
            
            min_z_order = min(z_orders)
            
            backdrop_to_resize['z_order'].setValue(min_z_order - 1)

        except:
            pass

    # --- [ Bounding Box and Resize Logic ] ---
    nodes_to_bound = selected_other_nodes + other_backdrops
    
    min_x = min(n.xpos() for n in nodes_to_bound)
    min_y = min(n.ypos() for n in nodes_to_bound)
    max_x = max(n.xpos() + n.screenWidth() for n in nodes_to_bound)
    max_y = max(n.ypos() + n.screenHeight() for n in nodes_to_bound)    

    backdrop_to_resize.setXpos(min_x - padding)
    backdrop_to_resize.setYpos(min_y - padding)
    backdrop_to_resize["bdwidth"].setValue((max_x - min_x) + (2 * padding))
    backdrop_to_resize["bdheight"].setValue((max_y - min_y) + (2 * padding))