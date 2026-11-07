#==============================================================================
#                             ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script copies nodes and reconnects them after pasting using hidden metadata in the clipboard
                 It also lets you paste to multiple nodes using the default Ctrl+V hotkey. 
                 The metadata is used in favour of userknobs to prevent slowdown when using paste or paste multiple
                 Inspired by Sebastian Schutt's version https://youtu.be/jpdbNuVCOjg?si=ksk5yydlFIDgN3cV
                 But with some additional logic to make copying from one script to another more stable 
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
    VERSION:     01.01
    PUBLISHED:   2026-05-17
    DOCS:        https://www.hiramgifford.com/buddy-system/node-graph-buddy

"""
#==============================================================================
#                        ---- How To Install ----
#==============================================================================
"""
    Step #0:     See installation instructions for BuddySystem
"""
#===============================================================================
#                          ---- Imports ----
#===============================================================================

import nuke
import re
import json

# --- [  Import PySide based on nuke version ] ---
if nuke.NUKE_VERSION_MAJOR < 11:
    from PySide import QtCore, QtGui
    QtWidgets = QtGui
elif nuke.NUKE_VERSION_MAJOR < 16:
    from PySide2 import QtWidgets, QtCore, QtGui
else:
    from PySide6 import QtWidgets, QtCore, QtGui

#===============================================================================
#                        ---- Helpers & Globals ----
#===============================================================================

# --- [ Globals ] ---
TEMP_TAB_NAME = '_temp_data_tab'
CONNECTIONS_KNOB_NAME = '_temp_input_connections'
METADATA_MARKER = '# NODE_GRAPH_BUDDY_SMART_PASTE_DATA: '
MAX_PASTE_WARNING_THRESHOLD = 250

def _cleanup_node(node):
    """Helper to remove tracking knobs from node when using reconnect feature"""
    try:
        conn_knob = node.knob(CONNECTIONS_KNOB_NAME)
        if conn_knob:
            node.removeKnob(conn_knob)
            
        tab_knob = node.knob(TEMP_TAB_NAME)
        if tab_knob:
            node.removeKnob(tab_knob)
    except:
        pass

def _clipboard():
    """Clipboard"""
    return QtWidgets.QApplication.clipboard()

def _get_clipboard_text():
    """Gets text from the clipboard"""
    return _clipboard().text()

def _set_clipboard_text(text):
    """Sets text to the clipboard"""
    _clipboard().setText(text)

def _count_nodes_in_clipboard():
    """Counts the number of nodes in the current clipboard text"""
    cb_text = _get_clipboard_text()
    node_count = 0
    # --- A basic counter that look for lines starting with node classes or names
    # --- This might need refinement but seems to work well so far
    for line in cb_text.splitlines():
        if re.match(r"^[A-Z][a-zA-Z0-9_]*\s*\{", line):
            node_count += 1
    return node_count

def _check_paste_limit(num_selected_nodes):
    """
    Checks if the paste operation will result in too many nodes and warns the user
    Returns True if it's safe to proceed, False if the user cancelled
    """
    if num_selected_nodes <= 1:
        return True # - Native paste, usually safe

    nodes_in_clipboard = _count_nodes_in_clipboard()
    if nodes_in_clipboard == 0:
        return True # - Nothing to paste

    total_nodes_to_paste = nodes_in_clipboard * num_selected_nodes

    if total_nodes_to_paste > MAX_PASTE_WARNING_THRESHOLD:
        msg = (
            "<span style='color:#FFCC00; font-weight:bold;'>NodeGraphBuddy: Smart Paste Warning!</span>"
            "\n\nYou have {} nodes selected and are about to paste "
            "{} nodes to each, resulting in {} "
            "new nodes.\n\nThis could lock up Nuke.\n\nAre you sure you want to proceed?"
        ).format(num_selected_nodes, nodes_in_clipboard, total_nodes_to_paste)
        if not nuke.ask(msg):
            return False
            
    return True

def _execute_contextual_paste(initial_selection):
    """
    Core paste logic
    If 0-1 nodes are selected, performs a native paste
    If 2+ nodes are selected, performs multipaste with downstream insertion
    Returns a list of the newly pasted nodes
    """
    newly_pasted_nodes = []
    
    if len(initial_selection) <= 1:
        try:
            nuke.nodePaste('%clipboard%')
            newly_pasted_nodes.extend(nuke.selectedNodes())
        except RuntimeError:
            pass
    else:
        for n in initial_selection:
            n.setSelected(False)
            
        for target_node in initial_selection:
            # --- Track dependents before paste to allow insertion 
            dep_info = []
            deps = target_node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, False)
            for dep in deps:
                if dep not in initial_selection:  # - Prevent cyclic connection loops
                    for i in range(dep.inputs()):
                        if dep.input(i) == target_node:
                            dep_info.append((dep, i))

            # --- Paste the nodes
            target_node.setSelected(True)
            try:
                nuke.nodePaste('%clipboard%')
            except RuntimeError:
                target_node.setSelected(False)
                break
            
            pasted_this_round = nuke.selectedNodes()
            pasted_valid = []
            
            for p_node in pasted_this_round:
                if p_node != target_node:
                    newly_pasted_nodes.append(p_node)
                    pasted_valid.append(p_node)
                p_node.setSelected(False)
                
            target_node.setSelected(False)

            # --- Insert pasted nodes into the downstream pipe
            if pasted_valid and dep_info:
                bottom_nodes = []
                for p in pasted_valid:
                    has_internal_dep = False
                    for d in p.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, False):
                        if d in pasted_valid:
                            has_internal_dep = True
                            break
                    if not has_internal_dep:
                        bottom_nodes.append(p)
                        
                if bottom_nodes:
                    bottom_node = bottom_nodes[0]
                    for dep, idx in dep_info:
                        dep.setInput(idx, bottom_node)
                        
    return newly_pasted_nodes

#===============================================================================
#                        ---- Scripts ----
#===============================================================================

def copy():
    """
    Copy operation (Ctrl+C)
    Maps external inputs, performs Nuke's standard copy, and appends a hidden metadata for use in paste operations
    The metadata is used to speed up the standard paste and paste to multi operation, 
    as I found creating/removing custom user knobs to store the connection data too slow in large files
    Custom user knobs are still used for reconnect feature, which is bound to a seperate hotkey
    """
    nodes = nuke.selectedNodes()
    if not nodes:
        return

    # --- [ Map out the connections  ] ---
    selected_names = set(n.name() for n in nodes)
    input_map = {}

    for node in nodes:
        connections = []
        for i in range(node.inputs()):
            input_node = node.input(i)
            if input_node and input_node.name() not in selected_names:
                connections.append("{}:{}".format(i, input_node.name()))

        if connections:
            input_map[node.name()] = ";".join(connections)

    # --- [ Perform Nuke's standard copy ] ---
    nuke.nodeCopy('%clipboard%')

    if not input_map:
        return 

    # --- [ Intercept clipboard text and append hidden metadata at the end ] ---
    cb_text = _get_clipboard_text()
    if not cb_text.strip():
        return

    serialized_data = json.dumps(input_map)
    cb_text += '\n{}{}'.format(METADATA_MARKER, serialized_data)
    
    # --- [ Push the modified string back to the clipboard ] ---
    _set_clipboard_text(cb_text)


def smart_multipaste():
    """
    Paste operation (Ctrl+V)
    Contextual: Native paste if 0-1 nodes selected. Multipaste if 2+ selected
    Ignores the hidden clipboard metadata entirely for speed
    """
    initial_selection = nuke.selectedNodes()
    
    # --- [ Check limit  ] ---
    if not _check_paste_limit(len(initial_selection)):
        return

    nuke.Undo.begin("Smart Paste")
    try:
        pasted_nodes = _execute_contextual_paste(initial_selection)
        
        for n in nuke.selectedNodes():
            n.setSelected(False)
        for n in pasted_nodes:
            n.setSelected(True)
    finally:
        nuke.Undo.end()


def paste_reconnect():
    """
    Paste & Reconnect operation (Shift+V)
    Reads the hidden metadata, injects temporary knobs, performs contextual paste,
    reconnects upstream inputs, then cleans up
    """
    initial_selection = nuke.selectedNodes()
    
    # --- [ Check limit ] ---
    if not _check_paste_limit(len(initial_selection)):
        return

    cb_text = _get_clipboard_text()
    original_cb_text = cb_text
    input_map = {}

    # --- [ Find hidden metadata at the end of the clipboard ] ---
    lines = cb_text.splitlines()
    if lines and lines[-1].startswith(METADATA_MARKER):
        json_str = lines[-1][len(METADATA_MARKER):]
        try:
            input_map = json.loads(json_str)
        except:
            pass

    use_modified_clipboard = False
    
    # --- [ If metadata exists, temporarily inject tracking knobs ] ---
    if input_map:
        out_lines = []
        current_node_name = None
        for line in lines:
            if line.startswith(METADATA_MARKER):
                continue 

            match = re.match(r"^\s*name\s+(\S+)", line)
            if match:
                current_node_name = match.group(1)

            if line.strip() == "}" and current_node_name in input_map:
                inputs_text = input_map[current_node_name]
                out_lines.append(" addUserKnob {{20 {}}}".format(TEMP_TAB_NAME))
                out_lines.append(' addUserKnob {{26 {} -STARTLINE T "{}"}}'.format(CONNECTIONS_KNOB_NAME, inputs_text))
                current_node_name = None

            out_lines.append(line)

        modified_cb_text = "\n".join(out_lines)
        _set_clipboard_text(modified_cb_text)
        use_modified_clipboard = True

    nuke.Undo.begin("Paste and Reconnect")
    try:
        # --- [ Perform contextual paste ] ---
        newly_pasted_nodes = _execute_contextual_paste(initial_selection)

        node_cache = {}

        # --- [ Iterate through all pasted nodes, read the data, reconnect, select ] ---
        for n in nuke.selectedNodes():
            n.setSelected(False)
            
        for node in newly_pasted_nodes:
            node.setSelected(True) 
            
            conn_knob = node.knob(CONNECTIONS_KNOB_NAME)
            if conn_knob:
                data_string = conn_knob.value().strip()
                
                if data_string:
                    for conn in data_string.split(';'):
                        try:
                            index_str, node_name = conn.split(':', 1)
                            input_index = int(index_str)
                            
                            target_node = node_cache.get(node_name)
                            if target_node is None:
                                target_node = nuke.toNode(node_name)
                                node_cache[node_name] = target_node

                            if target_node and not node.input(input_index):
                                node.setInput(input_index, target_node)
                        except:
                            pass

            # --- [ Clean up temp knobs ] ---
            _cleanup_node(node)
    finally:
        nuke.Undo.end()
         # --- [ Restore clipboard to the original text so native Ctrl+V remains garbage free ] ---
        if use_modified_clipboard:
            _set_clipboard_text(original_cb_text)