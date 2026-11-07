#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: These functions allow you to mirror selected nodes horizontally or vertically
                 The last node you select will be used as the center point
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

def get_center(node):
    """Returns the center of a node"""
    x = node.xpos()
    y = node.ypos()
    w = node.screenWidth()
    h = node.screenHeight()
    return x + w/2.0, y + h/2.0

def set_center(node, cx, cy):
    """Move a node by its center point"""
    w = node.screenWidth()
    h = node.screenHeight()
    node.setXpos(int(cx - w/2.0))
    node.setYpos(int(cy - h/2.0))

def mirror_nodes(direction='horizontal'):
    """Mirror selected nodes"""
    with nuke.Undo("Mirror Nodes"):
        sel = nuke.selectedNodes()
        if len(sel) < 2:
            return

        pivot = nuke.selectedNode()
        pcx, pcy = get_center(pivot)

        # --- [ Mirror all nonbackdrop nodes ] ---
        for n in sel:
            if n == pivot or n.Class() == 'BackdropNode':
                continue
            cx, cy = get_center(n)
            if direction == 'horizontal':
                set_center(n, 2*pcx - cx, cy)
            else:
                set_center(n, cx, 2*pcy - cy)

        #  --- [ Mirror backdrops ] ---
        for bd in [n for n in sel if n.Class() == 'BackdropNode']:
            x = bd.xpos()
            y = bd.ypos()
            w = bd['bdwidth'].value()
            h = bd['bdheight'].value()
            cx = x + w/2.0
            cy = y + h/2.0

            if direction == 'horizontal':
                new_cx = 2*pcx - cx
                bd.setXpos(int(new_cx - w/2.0))
            else:
                new_cy = 2*pcy - cy
                bd.setYpos(int(new_cy - h/2.0))
