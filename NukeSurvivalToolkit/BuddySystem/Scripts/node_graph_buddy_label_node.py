#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script lets you quickly add/modify a node label via hotkey
                 The default hotkey is "A" but uses the nodegraph context, 
                 so using "A" in the viewer will still show alpha
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

# --- [  Import PySide based on nuke version ] --- 
if nuke.NUKE_VERSION_MAJOR < 11:
    from PySide import QtCore
elif nuke.NUKE_VERSION_MAJOR < 16:
    from PySide2 import QtCore
else:
    from PySide6 import QtCore
    
#===============================================================================
#                       ---- Scripts ----
#===============================================================================  

def label_and_recenter_nodes(auto_case=True):
    """
    Applies a user label to selected nodes and recenters them vertically
    Optional argument of 'auto_case' can be used to auto uppercase the first letter in the label
    """
    # --- [  Classes that don't need to be recentered ] ---
    EXCLUDED_CLASSES = ['BackdropNode', 'StickyNote', 'Camera2', 'Axis2', 'Read', 'Constant', 'CheckerBoard2', 'ColorBars', 'ColorWheel', 'Dot']

    nodes = nuke.selectedNodes()
    if not nodes:
        nuke.message("Please select at least one node to relabel.")
        return
        
    # --- [  Bit of logic to warn if many nodes are selected ] ---
    if len(nodes) > 5 and not nuke.ask(
            "You have many nodes selected.\n"
            "Do you want to add labels to all of them?"):
        return

    try:
        current_label = nodes[0]['label'].value()
    except (AttributeError, IndexError):
        current_label = ""
        
    # --- [  Panel Creation ] ---
    panel = nuke.Panel("Relabel Nodes")
    panel.addSingleLineInput("Label", current_label)
    panel.addBooleanCheckBox("Recenter Nodes", True)
    if not panel.show():
        return

    new_label = panel.value("Label")
    recenter = panel.value("Recenter Nodes")

    # --- [ Auto capitalize the first letter for lazy people like me ] ---
    if auto_case and new_label:
        new_label = new_label[0].upper() + new_label[1:]

    nodes_to_recenter_info = []
    
    undo = nuke.Undo()
    undo.begin("Relabel and Recenter Nodes")

    # --- [ Apply label and record original size ] ---
    for node in nodes:
        should_recenter_node = (recenter and
                                node.Class() not in EXCLUDED_CLASSES)

        if should_recenter_node:
            nodes_to_recenter_info.append({
                'node': node,
                'old_y': node.ypos(),
                'old_h': node.screenHeight()
            })

        node['label'].setValue(new_label)

    if not nodes_to_recenter_info:
        undo.end()
        return

    def calculate_difference_and_recenter():
        """
        This function performs the recenter 
        Due to nukes GUI not updating fast enough, it must be run after a forced delay
        The delay allows the label to be applied, and the node size to change, so the script can adjust correctly
        """
        for geo_info in nodes_to_recenter_info:
            node = geo_info['node']
            old_y = geo_info['old_y']
            old_h = geo_info['old_h']

            new_h = node.screenHeight()

            if old_h == new_h:
                continue

            delta = (old_h - new_h) / 2.0
            new_y_pos = int(round(old_y + delta))
            node.setYpos(new_y_pos)

        undo.end()

    # --- [ Delays the recenter here ] ---
    QtCore.QTimer.singleShot(50, calculate_difference_and_recenter)