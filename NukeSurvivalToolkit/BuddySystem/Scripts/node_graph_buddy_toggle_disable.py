#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script toggles the disabled state of selected nodes
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
#                       ---- Imports ----
#===============================================================================

import nuke

#===============================================================================
#                       ---- Scripts ----
#===============================================================================

def toggle_disable():
    """Toggle disable knobs"""
    selected_nodes = nuke.selectedNodes()

    if not selected_nodes:
        return
    else:
        for node in selected_nodes:
          if 'disable' in node.knobs():
            is_disabled = node['disable'].value()          
            # --- [ Set knob to its opposite value ] ---
            node['disable'].setValue(not is_disabled)