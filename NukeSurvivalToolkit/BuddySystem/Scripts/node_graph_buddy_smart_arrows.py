#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script turns the arrow keys into contextual super hotkeys that does the following;
                 If 0-1 nodes are selected, left/right arrows preform frame navigation     
                 If 1 node is selected, up/down arrows preform jump to input/output
                 If 1 node is selected and Ctrl+arrow up/down is used, do native node swap (LeapFrog)
                 If 2+ nodes are selected, all arrows preform alignment operation                
                 If 2+ nodes are selected and are already aligned, all arrows preform a directional stack operation
                 If 2+ backdrops are selected, arrows preform alignment and then directional size matching, instead of stacking
                 If 2+ nodes and backdrops are selected, all arrows will align backdrops while keeping their nodes relative to it
                 In additon all arrows can preform basic or physics based move/scale operation with alternative hotkey binding. 
                 Scaling uses Shift+arrow for uniform scaling, and Shift+Ctrl+arrow for biased directional scaling. Both options use physics unless disabled in the config menu
                 Moving uses Ctrl+arrow for basic fast moving, and Ctrl+Alt+Meta+arrow for slower physics based moving
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
    VERSION:     01.01
    PUBLISHED:   2026-05-24
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
import nukescripts

# --- [ Import PySide based on nuke version ] --- 
if nuke.NUKE_VERSION_MAJOR < 11:
    from PySide import QtCore, QtGui
    QtWidgets = QtGui
elif nuke.NUKE_VERSION_MAJOR < 16:
    from PySide2 import QtWidgets, QtCore, QtGui
else:
    from PySide6 import QtWidgets, QtCore, QtGui
    

# ===============================================================================
#                            ---- Globals & Config ----
# ===============================================================================

# --- [ Smart Move Config ] ---
BULLDOZER_CONFIG = {
    'DEBUG_SWEEP': False,
    'DEBUG_BYSTANDERS': False,
    'VERBOSE_PRINTS': False,
    'USE_ZOOM': True,
    'ZOOM_MULTIPLIER': 10,
    'TREAT_AS_ONE': True,
    'SIM_MAX_ITERATIONS': 10,
    'SIM_MAX_STEP_SIZE': 15.0,
    'NODE_PAD': 10,
    'BD_PAD': 100,
    'SIM_SIDE_PAD': 0,
    'SIM_BACK_PAD': 0,
    'SIM_FORWARD_MULTIPLIER': 4.0,
    'SIM_FORWARD_BASE': 200,
    'SIM_FORWARD_MIN': 5000,
    'UNIFORM_SCALE_MIN_PAD': 1500,
    'CLUSTER_TOLERANCE': 15,
    'BD_CLUSTER_TOLERANCE': 15
}

# --- [ Scale Cache & Settings ] ---
ORIGINAL_SCALE_CACHE = {}

SCALE_BIAS_CONFIG = {
    'H_CENTER': 'left',
    'V_CENTER': 'top',
    'USE_BULLDOZER': True,
    'DONT_SCALE_NESTED': False
}

# --- [ Directions ] ---
DIRECTION_FLAGS = {
    'bdwidth':         (True,  False),
    'bdwidth_center':  (True,  False),
    'bdheight':        (False, True),
    'bdheight_center': (False, True),
    'bdboth_center':   (True,  True),
    'bdboth_top':      (True,  True),
    'bdboth_bottom':   (True,  True),
}

# ===============================================================================
#                            ---- Config Panel ----
# ===============================================================================

class NodeGraphBuddySmartArrowsConfigPanel(QtWidgets.QDialog):
    """Settings Panel For Bulldozer Physics, Smart Move & Scale"""
    
    def __init__(self, parent=None, default_tab='move'):
        super(NodeGraphBuddySmartArrowsConfigPanel, self).__init__(parent)
        self.setWindowTitle("NodeGraphBuddy: Smart Arrows - Settings")
        self.setMinimumSize(400, 520)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        
        # --- [ Smart Move & Bulldozer Physics Tab ] ---
        move_tab = QtWidgets.QWidget()
        move_layout = QtWidgets.QFormLayout(move_tab)
        
        # --- [ Helper to generate styled divider sections ] ---
        def add_section(title, color):
            if move_layout.rowCount() > 0:
                move_layout.addRow(QtWidgets.QLabel(""))  # Visual spacer
            
            lbl = QtWidgets.QLabel(
                "<span style='color:{}; font-size:12px; font-weight:bold;'>{}</span>".format(color, title)
            )
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Sunken)
            
            move_layout.addRow(lbl)
            move_layout.addRow(line)

        # --- [ All (Grey) ] ---
        add_section("Applies To All", "#AAAAAA")
        
        self.debug_cb = QtWidgets.QCheckBox("Enable Debug Mode (Slow)")
        self.debug_cb.setToolTip(
            'Draws temporary debug backdrops/bounding boxes showing:\n'
            '- The sweep collision area (Red)\n'
            '- Primary Movers (Green)\n'
            '- Secondary Movers aka Rigid groups (Yellow)'
        )
        self.debug_cb.setChecked(BULLDOZER_CONFIG['DEBUG_SWEEP'])
        move_layout.addRow("", self.debug_cb)

        self.debug_bystanders_cb = QtWidgets.QCheckBox("Purple BBox Bystanders (Slower)")
        self.debug_bystanders_cb.setToolTip(
            'Draws temporary bounding boxes around identified bystander nodes (Purple)\n'
            'Requires Debugging Mode'
        )
        self.debug_bystanders_cb.setChecked(BULLDOZER_CONFIG['DEBUG_BYSTANDERS'])
        move_layout.addRow("", self.debug_bystanders_cb)
        
        self.verbose_cb = QtWidgets.QCheckBox("Verbose Debug (Slowerer)")
        self.verbose_cb.setToolTip(
            'Prints very detailed data to the script editor. \n'
            'Requires Debugging Mode'
        )
        self.verbose_cb.setChecked(BULLDOZER_CONFIG['VERBOSE_PRINTS'])
        move_layout.addRow("", self.verbose_cb)

        self.cleanup_btn = QtWidgets.QPushButton("Clean Up Debug Nodes")
        self.cleanup_btn.setToolTip("Force deletes any stuck NGB_DEBUG_ nodes if the timer method fails")
        self.cleanup_btn.clicked.connect(self.cleanup_debug_nodes)
        move_layout.addRow("", self.cleanup_btn)
        
        self.zoom_cb = QtWidgets.QCheckBox("Use Zoom Level For Size")
        self.zoom_cb.setToolTip("When enabled, movement and scaling size dynamically adjusts based on the Node Graph zoom level")
        self.zoom_cb.setChecked(BULLDOZER_CONFIG['USE_ZOOM'])
        move_layout.addRow("", self.zoom_cb)

        self.zoom_mult_sp = QtWidgets.QSpinBox()
        self.zoom_mult_sp.setRange(1, 500)
        self.zoom_mult_sp.setValue(BULLDOZER_CONFIG['ZOOM_MULTIPLIER'])
        self.zoom_mult_sp.setToolTip("Base multiplier for the move/scale distance")
        move_layout.addRow("Zoom Multiplier:", self.zoom_mult_sp)
        
        self.max_iter_sp = QtWidgets.QSpinBox()
        self.max_iter_sp.setRange(1, 50)
        self.max_iter_sp.setValue(BULLDOZER_CONFIG['SIM_MAX_ITERATIONS'])
        self.max_iter_sp.setToolTip(
            "Maximum number of collision passes per sub step.\n"
            "Higher values resolve complex overlaps better but are slower.\n"
            "Since moving a node can cause other nodes to move this allows the sim "
            "to account for those cascading changes up to the limit set"
        )
        move_layout.addRow("Max Iterations:", self.max_iter_sp)
        
        self.max_step_sp = QtWidgets.QDoubleSpinBox()
        self.max_step_sp.setRange(1.0, 100.0)
        self.max_step_sp.setValue(BULLDOZER_CONFIG['SIM_MAX_STEP_SIZE'])
        self.max_step_sp.setToolTip(
            "The maximum distance nodes can move in a single sub step. "
            "Smaller values improve accuracy but are slower.\n"
            "When set to 15, if you move a node 150 pixels, the engine runs 10 sub steps"
        )
        move_layout.addRow("Max Step Size:", self.max_step_sp)
        
        # --- [ Primary Movers (Green) ] ---
        add_section("Primary Movers", "#00FF00")

        self.treat_as_one_cb = QtWidgets.QCheckBox("Treat Primary Movers As One")
        self.treat_as_one_cb.setToolTip(
            "Draws an imaginary bounding box around all selected nodes and treats them as a single\n"
            "primary mover (like selecting a backdrop with nodes on it.)\n"
            "This is much faster than calculating the physics for each node independantly"
        )
        self.treat_as_one_cb.setChecked(BULLDOZER_CONFIG['TREAT_AS_ONE'])
        move_layout.addRow("", self.treat_as_one_cb)

        self.node_pad_sp = QtWidgets.QSpinBox()
        self.node_pad_sp.setRange(0, 1000)
        self.node_pad_sp.setValue(BULLDOZER_CONFIG['NODE_PAD'])
        self.node_pad_sp.setToolTip("Padding added around standard nodes to push bystanders away")
        move_layout.addRow("Node Padding:", self.node_pad_sp)

        self.bd_pad_sp = QtWidgets.QSpinBox()
        self.bd_pad_sp.setRange(0, 1000)
        self.bd_pad_sp.setValue(BULLDOZER_CONFIG['BD_PAD'])
        self.bd_pad_sp.setToolTip("Padding added around backdrop nodes to push bystanders away")
        move_layout.addRow("Backdrop Padding:", self.bd_pad_sp)

        # --- [ Secondary Movers (Yellow) ] ---
        add_section("Secondary Movers", "#FFCC00")
        
        self.cluster_sp = QtWidgets.QSpinBox()
        self.cluster_sp.setRange(0, 1000)
        self.cluster_sp.setValue(BULLDOZER_CONFIG['CLUSTER_TOLERANCE'])
        self.cluster_sp.setToolTip(
            'Groups loose nodes together if they are within this distance to speed up physics calculations.\n'
            'Also prevents loose nodes from passing between each other'
        )
        move_layout.addRow("Group Loose Nodes:", self.cluster_sp)
        
        self.bd_cluster_sp = QtWidgets.QSpinBox()
        self.bd_cluster_sp.setRange(0, 1000)
        self.bd_cluster_sp.setValue(BULLDOZER_CONFIG['BD_CLUSTER_TOLERANCE'])
        self.bd_cluster_sp.setToolTip('Groups loose backdrops together if they are within this distance to speed up physics calculations')
        move_layout.addRow("Group Loose Backdrops:", self.bd_cluster_sp)
        
        # --- [ Sweep Area (Red) ] ---
        add_section("Sweep Area", "#FF6666")
        
        self.lat_pad_sp = QtWidgets.QSpinBox()
        self.lat_pad_sp.setRange(0, 1000)
        self.lat_pad_sp.setValue(BULLDOZER_CONFIG['SIM_SIDE_PAD'])
        self.lat_pad_sp.setToolTip(
            "Side padding added to the sweep area to catch adjacent bystanders.\n"
            "You generally want this at 0, but there are edge cases for increasing it"
        )
        move_layout.addRow("Side Padding:", self.lat_pad_sp)
        
        self.back_pad_sp = QtWidgets.QSpinBox()
        self.back_pad_sp.setRange(0, 1000)
        self.back_pad_sp.setValue(BULLDOZER_CONFIG['SIM_BACK_PAD'])
        self.back_pad_sp.setToolTip(
            "Rear padding added to the back of the sweep area.\n"
            "You generally want this at 0, but there might be edge cases for increasing it"
        )
        move_layout.addRow("Rear Padding:", self.back_pad_sp)
        
        self.fwd_mult_sp = QtWidgets.QDoubleSpinBox()
        self.fwd_mult_sp.setRange(0.0, 20.0)
        self.fwd_mult_sp.setValue(BULLDOZER_CONFIG['SIM_FORWARD_MULTIPLIER'])
        self.fwd_mult_sp.setToolTip(
            "Multiplier for the forward sweep area length based on the total movement direction.\n"
            "If the result of this is less than the Forward Min Pad it is ignored.\n"
            "This was the original logic, that made a dynamiclly sized sweep area based on movement/scale amount,\n"
            "but I found a fixed sweep area size to be more predictable for the user"
        )
        move_layout.addRow("Forward Multiplier:", self.fwd_mult_sp)
        
        self.fwd_base_sp = QtWidgets.QSpinBox()
        self.fwd_base_sp.setRange(0, 10000)
        self.fwd_base_sp.setValue(BULLDOZER_CONFIG['SIM_FORWARD_BASE'])
        self.fwd_base_sp.setToolTip("Base padding added to the front of the sweep area")
        move_layout.addRow("Forward Base Pad:", self.fwd_base_sp)
        
        self.fwd_min_sp = QtWidgets.QSpinBox()
        self.fwd_min_sp.setRange(0, 10000)
        self.fwd_min_sp.setValue(BULLDOZER_CONFIG['SIM_FORWARD_MIN'])
        self.fwd_min_sp.setToolTip("Absolute minimum length for the forward sweep area to prevent movement from ignoring bystanders")
        move_layout.addRow("Forward Min Pad:", self.fwd_min_sp)

        self.fwd_uniform_min_sp = QtWidgets.QSpinBox()
        self.fwd_uniform_min_sp.setRange(0, 10000)
        self.fwd_uniform_min_sp.setValue(BULLDOZER_CONFIG['UNIFORM_SCALE_MIN_PAD'])
        self.fwd_uniform_min_sp.setToolTip(
            "Minimum length for the sweep area specifically during center scaling.\n"
            "Keeping this lower than the forward min pad prevents slowness"
        )
        move_layout.addRow("Center Scale Min Pad:", self.fwd_uniform_min_sp)
        
        self.tabs.addTab(move_tab, "Bulldozer Physics (Beta)")
        
        # --- [ Smart Scale Tab ] ---
        scale_tab = QtWidgets.QWidget()
        scale_layout = QtWidgets.QFormLayout(scale_tab)
        
        self.h_combo = QtWidgets.QComboBox()
        self.h_combo.addItems(["Left To Right", "Right To Left"])
        self.h_combo.setCurrentIndex(0 if SCALE_BIAS_CONFIG['H_CENTER'] == 'left' else 1)
        self.h_combo.setToolTip("Horizontal pivot direction when scaling nodes in biased mode")
        scale_layout.addRow("Horizontal Bias:", self.h_combo)
        
        self.v_combo = QtWidgets.QComboBox()
        self.v_combo.addItems(["Top To Bottom", "Bottom To Top"])
        self.v_combo.setCurrentIndex(0 if SCALE_BIAS_CONFIG['V_CENTER'] == 'top' else 1)
        self.v_combo.setToolTip("Vertical pivot direction when scaling nodes in biased mode")
        scale_layout.addRow("Vertical Bias:", self.v_combo)
        
        self.use_bulldozer_cb = QtWidgets.QCheckBox("Enable Bulldozer Physics (Slow)")
        self.use_bulldozer_cb.setToolTip(
            "Uncheck this to use faster basic scaling.\n"
            "Basic scaling doesn't push neighbors out of the way, or expand unselected parent backdrops"
        )
        self.use_bulldozer_cb.setChecked(SCALE_BIAS_CONFIG['USE_BULLDOZER'])
        scale_layout.addRow("", self.use_bulldozer_cb)

        self.dont_scale_nested_cb = QtWidgets.QCheckBox("Don't Change Nested Backdrops Scale")
        self.dont_scale_nested_cb.setToolTip(
            "When true, scaling a large backdrop containing smaller nested backdrops,\n"
            "will only reposition the nested backdrops without changing their size"
        )
        self.dont_scale_nested_cb.setChecked(SCALE_BIAS_CONFIG.get('DONT_SCALE_NESTED', False))
        scale_layout.addRow("", self.dont_scale_nested_cb)
        
        self.tabs.addTab(scale_tab, "Smart Scale")
        main_layout.addWidget(self.tabs)
        
        if default_tab == 'scale':
            self.tabs.setCurrentIndex(1)
        
        # --- [ Buttons ] ---
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

    def cleanup_debug_nodes(self):
        """Force deletes any leftover debug nodes"""
        selection = nuke.selectedNodes()
        nuke.Undo().disable()
        try:
            for node in nuke.allNodes():
                if node.name().startswith('NGB_DEBUG_'):
                    nuke.delete(node)
        except Exception:
            pass
        finally:
            nuke.Undo().enable()
            for node in selection:
                try: 
                    node.setSelected(True)
                except Exception: 
                    pass

    def apply_settings(self):
        """Saves values from the panel back into global memory"""
        BULLDOZER_CONFIG['DEBUG_SWEEP'] = self.debug_cb.isChecked()
        BULLDOZER_CONFIG['DEBUG_BYSTANDERS'] = self.debug_bystanders_cb.isChecked()
        BULLDOZER_CONFIG['VERBOSE_PRINTS'] = self.verbose_cb.isChecked()
        BULLDOZER_CONFIG['USE_ZOOM'] = self.zoom_cb.isChecked()
        BULLDOZER_CONFIG['ZOOM_MULTIPLIER'] = self.zoom_mult_sp.value()
        BULLDOZER_CONFIG['TREAT_AS_ONE'] = self.treat_as_one_cb.isChecked()
        BULLDOZER_CONFIG['SIM_MAX_ITERATIONS'] = self.max_iter_sp.value()
        BULLDOZER_CONFIG['SIM_MAX_STEP_SIZE'] = self.max_step_sp.value()
        BULLDOZER_CONFIG['NODE_PAD'] = self.node_pad_sp.value()
        BULLDOZER_CONFIG['BD_PAD'] = self.bd_pad_sp.value()
        BULLDOZER_CONFIG['CLUSTER_TOLERANCE'] = self.cluster_sp.value()
        BULLDOZER_CONFIG['BD_CLUSTER_TOLERANCE'] = self.bd_cluster_sp.value()
        BULLDOZER_CONFIG['SIM_SIDE_PAD'] = self.lat_pad_sp.value()
        BULLDOZER_CONFIG['SIM_BACK_PAD'] = self.back_pad_sp.value()
        BULLDOZER_CONFIG['SIM_FORWARD_MULTIPLIER'] = self.fwd_mult_sp.value()
        BULLDOZER_CONFIG['SIM_FORWARD_BASE'] = self.fwd_base_sp.value()
        BULLDOZER_CONFIG['SIM_FORWARD_MIN'] = self.fwd_min_sp.value()
        BULLDOZER_CONFIG['UNIFORM_SCALE_MIN_PAD'] = self.fwd_uniform_min_sp.value()
        
        SCALE_BIAS_CONFIG['H_CENTER'] = 'left' if self.h_combo.currentText() == 'Left To Right' else 'right'
        SCALE_BIAS_CONFIG['V_CENTER'] = 'top' if self.v_combo.currentText() == 'Top To Bottom' else 'bottom'
        SCALE_BIAS_CONFIG['USE_BULLDOZER'] = self.use_bulldozer_cb.isChecked()
        SCALE_BIAS_CONFIG['DONT_SCALE_NESTED'] = self.dont_scale_nested_cb.isChecked()

def show_smart_arrows_config(default_tab='move'):
    """Launches the Config panel"""
    parent = nuke.mainWindow() if hasattr(nuke, 'mainWindow') else None
    dialog = NodeGraphBuddySmartArrowsConfigPanel(parent, default_tab)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        dialog.apply_settings()
        

# ===============================================================================
#                            ---- Helpers ----
# ===============================================================================

def _get_node_width(node):
    """This is setup for older versions of Nuke where screenWidth() wasn't as reliable with backdrops"""
    if node.Class() == 'BackdropNode':
        return node.knob('bdwidth').value()
    return node.screenWidth()

def _get_node_height(node):
    """This is setup for older versions of Nuke where screenHeight() wasn't as reliable with backdrops"""
    if node.Class() == 'BackdropNode':
        return node.knob('bdheight').value()
    return node.screenHeight()

def _get_outputs_fast(target_node):
    """Optimized output gathering using proximity. Used in leapfrog logic"""
    valid_outputs = []
    search_padding = 10000 
    left = target_node.xpos() - search_padding
    top = target_node.ypos() - search_padding
    right = target_node.xpos() + search_padding
    bottom = target_node.ypos() + search_padding
    
    for node in sorted(nuke.allNodes(), key=lambda x: x.name()):
        node_x = node.xpos()
        node_y = node.ypos()
        if left < node_x < right and top < node_y < bottom:
            for i in range(node.inputs()):
                if node.input(i) == target_node:
                    if node.Class() != "Viewer":
                        valid_outputs.append(node)
                    break
    return valid_outputs

def _get_nodes_in_backdrops(backdrops):
    """Gets node info for backdrops"""
    backdrop_map = {bd: set() for bd in backdrops}
    if not backdrops: 
        return backdrop_map
        
    for backdrop in backdrops:
        nodes_inside = backdrop.getNodes()
        backdrop_map[backdrop] = set(
            node for node in nodes_inside if not node.name().startswith('NGB_DEBUG_')
        )
                
    return backdrop_map

def _merge_primary_colliders(primary_colliders, selected_nodes, all_nodes, master_bd_map):
    """Reduces multiple primary movers into a single imaginary bounding box"""
    if not BULLDOZER_CONFIG.get('TREAT_AS_ONE', False) or len(primary_colliders) <= 1:
        return primary_colliders, None

    # --- [ Calculate virtual bounding box limits ] ---
    start_x = min(collider['start_x'] for collider in primary_colliders)
    start_y = min(collider['start_y'] for collider in primary_colliders)
    start_right = max(collider['start_right'] for collider in primary_colliders)
    start_bottom = max(collider['start_bottom'] for collider in primary_colliders)
    
    end_x = min(collider['end_x'] for collider in primary_colliders)
    end_y = min(collider['end_y'] for collider in primary_colliders)
    end_right = max(collider['end_right'] for collider in primary_colliders)
    end_bottom = max(collider['end_bottom'] for collider in primary_colliders)
    
    # --- [ Calculate common container backdrops for the virtual mover ] ---
    node_to_backdrops = {}
    for backdrop, nodes in master_bd_map.items():
        for node in nodes:
            node_to_backdrops.setdefault(node, set()).add(backdrop)
            
    common_backdrops = None
    for node in selected_nodes:
        if common_backdrops is None:
            common_backdrops = set(node_to_backdrops.get(node, set()))
        else:
            common_backdrops.intersection_update(node_to_backdrops.get(node, set()))
            
    if common_backdrops is None:
        common_backdrops = set()
        
    virtual_ignore_set = set()
    for node in all_nodes:
        if node.name().startswith('NGB_DEBUG_'): 
            continue
            
        node_x = node.xpos()
        node_y = node.ypos()
        
        # --- Fast spatial rejection before using expensive python calls
        if node_x < start_right and node_y < start_bottom:
            node_right = node_x + _get_node_width(node)
            if node_right > start_x:
                node_bottom = node_y + _get_node_height(node)
                if node_bottom > start_y:
                    center_x = (node_x + node_right) / 2.0
                    center_y = (node_y + node_bottom) / 2.0
                    
                    # --- Like a real backdrop, ignore any nodes naturally found inside it
                    if start_x <= center_x <= start_right and start_y <= center_y <= start_bottom:
                        virtual_ignore_set.add(node)
            
    for collider in primary_colliders:
        virtual_ignore_set.update(collider['ignore_set'])
        virtual_ignore_set.add(collider['node'])
        
    virtual_collider = {
        'node': "VIRTUAL_MOVER",
        'start_x': start_x, 
        'start_y': start_y, 
        'start_right': start_right, 
        'start_bottom': start_bottom,
        'end_x': end_x, 
        'end_y': end_y, 
        'end_right': end_right, 
        'end_bottom': end_bottom,
        'padding': BULLDOZER_CONFIG.get('BD_PAD', 100),
        'ignore_set': virtual_ignore_set,
        'is_selected': True,
        'containers': common_backdrops
    }
    
    # --- [ Preserve the original primary colliders map for expanding parent backdrop interpolation ] ---
    interpolation_map = {collider['node']: collider for collider in primary_colliders}
    
    return [virtual_collider], interpolation_map
    
# ===============================================================================
#                     ---- Bulldozer Physics Engine ----
# ===============================================================================

def bulldozer_physics_engine(
    primary_colliders, 
    affected_bds, 
    safe_nodes, 
    min_bounds_x, 
    min_bounds_y, 
    max_bounds_right, 
    max_bounds_bottom, 
    mode_direction=None, 
    axis_w=False, 
    axis_h=False, 
    px_abs=0, 
    py_abs=0, 
    interpolation_map=None
):
    """
    Sub steps the movement/scale of primary colliders, checks bounds, groups loose
    bystanders, and resolves overlaps
    """
    DEBUG_SWEEP = BULLDOZER_CONFIG['DEBUG_SWEEP']
    DEBUG_BYSTANDERS = BULLDOZER_CONFIG.get('DEBUG_BYSTANDERS', False)
    VERBOSE_PRINTS = BULLDOZER_CONFIG.get('VERBOSE_PRINTS', False) and DEBUG_SWEEP
    SIM_MAX_ITERATIONS = BULLDOZER_CONFIG['SIM_MAX_ITERATIONS']
    SIM_MAX_STEP_SIZE = BULLDOZER_CONFIG['SIM_MAX_STEP_SIZE']
    CLUSTER_TOLERANCE = BULLDOZER_CONFIG['CLUSTER_TOLERANCE']
    BD_CLUSTER_TOLERANCE = BULLDOZER_CONFIG.get('BD_CLUSTER_TOLERANCE', 100)
    
    debug_nodes_to_delete = []

    def remove_debug_nodes():
        """Clean up debug nodes after a period of time"""
        selection = nuke.selectedNodes()
        nuke.Undo().disable()
        try:
            for node in nuke.allNodes():
                if node.name().startswith('NGB_DEBUG_'):
                    nuke.delete(node)
        except Exception:
            pass
        finally:
            nuke.Undo().enable()
            for node in selection:
                try: 
                    node.setSelected(True)
                except Exception: 
                    pass

    # --- [ Determine allowed direction of movement ] ---
    allow_dx = False
    allow_dy = False
    if mode_direction in ('left', 'right'):
        allow_dx = True
    elif mode_direction in ('up', 'down'):
        allow_dy = True
    else:
        allow_dx = axis_w
        allow_dy = axis_h

    all_nodes = nuke.allNodes()
    local_bystanders = set()
    
    # --- [ Spatial Rejection Filter ] ---
    for node in all_nodes:
        if node not in safe_nodes and not node.name().startswith('NGB_DEBUG_'):
            node_x = node.xpos()
            node_y = node.ypos()
            # --- Fast math based check to discard nodes far away before doing heavy calls
            if node_x < max_bounds_right and node_y < max_bounds_bottom:
                node_right = node_x + _get_node_width(node)
                if node_right > min_bounds_x:
                    node_bottom = node_y + _get_node_height(node)
                    if node_bottom > min_bounds_y:
                        local_bystanders.add(node)

    # --- [ No Bystander Early Exit Check ] ---
    if not local_bystanders:
        if VERBOSE_PRINTS:
            print("\n>>> [VERBOSE] NO BYSTANDERS FOUND. SKIPPING PHYSICS ENGINE.")
        if DEBUG_SWEEP or DEBUG_BYSTANDERS:
            QtCore.QTimer.singleShot(100, remove_debug_nodes)
        return

    if VERBOSE_PRINTS:
        print("\n>>> [VERBOSE] BYSTANDERS IDENTIFIED: {}".format(len(local_bystanders)))
        for bystander_node in sorted(list(local_bystanders), key=lambda x: x.name()):
            print("  Bystander: {} (Class: {})".format(bystander_node.name(), bystander_node.Class()))

    groups = {}
    bystander_backdrops = [node for node in local_bystanders if node.Class() == 'BackdropNode']
    for backdrop in bystander_backdrops:
        for node in backdrop.getNodes():
            if node not in safe_nodes and not node.name().startswith('NGB_DEBUG_'):
                local_bystanders.add(node)

    all_bds_eval = [b for b in nuke.allNodes('BackdropNode') if not b.name().startswith('NGB_DEBUG_')]

    # --- [ Check backdrops that overlap the simulation sweep area ] ---
    relevant_backdrops = []
    for backdrop in all_bds_eval:
        backdrop_x = backdrop.xpos()
        backdrop_y = backdrop.ypos()
        backdrop_right = backdrop_x + backdrop.knob('bdwidth').value()
        backdrop_bottom = backdrop_y + backdrop.knob('bdheight').value()
        
        if (backdrop_right >= min_bounds_x and 
            backdrop_x <= max_bounds_right and 
            backdrop_bottom >= min_bounds_y and 
            backdrop_y <= max_bounds_bottom):
            relevant_backdrops.append(backdrop)
            
    # --- [ Build Hierarchical Containment ] ---
    backdrop_map = _get_nodes_in_backdrops(relevant_backdrops)
    node_containers = {}
    for backdrop, nodes in backdrop_map.items():
        for node in nodes:
            node_containers.setdefault(node, set()).add(backdrop)
                
    # --- [ Add virtual movers to containment ] ---
    for collider in primary_colliders:
        if isinstance(collider['node'], str) and 'containers' in collider:
            node_containers[collider['node']] = collider['containers']

    if VERBOSE_PRINTS:
        print("\n>>> [VERBOSE] HIERARCHICAL CONTAINMENT MAP ({} Backdrops Analyzed):".format(len(relevant_backdrops)))
        for node in sorted(node_containers.keys(), key=lambda x: x if isinstance(x, str) else x.name()):
            contained_bds = node_containers[node]
            backdrop_names = sorted([b.name() for b in contained_bds]) if contained_bds else []
            node_name = node if isinstance(node, str) else node.name()
            print("  Node: {} | Containers: {}".format(node_name, backdrop_names))

    if local_bystanders:
        bystander_backdrops.sort(
            key=lambda b: b.knob('bdwidth').value() * b.knob('bdheight').value(), 
            reverse=True
        )
        node_to_root = {}
        for backdrop in bystander_backdrops:
            for node in backdrop.getNodes():
                if node in local_bystanders and node != backdrop:
                    if node not in node_to_root: 
                        node_to_root[node] = backdrop
            if backdrop not in node_to_root: 
                node_to_root[backdrop] = backdrop
                
        # --- [ Add Into Groups ] ---
        for node in sorted(list(local_bystanders), key=lambda x: x.name()):
            root = node_to_root.get(node, node)
            groups.setdefault(root, []).append(node)
            
        # --- [ Loose Node Grouping Optimization ] ---
        if CLUSTER_TOLERANCE > 0 or BD_CLUSTER_TOLERANCE > 0:
            loose_roots = sorted(groups.keys(), key=lambda x: x.name())
            clusters = []
            
            for root in loose_roots:
                root_x = root.xpos()
                root_y = root.ypos()
                root_right = root_x + _get_node_width(root)
                root_bottom = root_y + _get_node_height(root)
                
                is_root_backdrop = root.Class() == 'BackdropNode'
                root_pad = BULLDOZER_CONFIG.get('BD_PAD', 100) if is_root_backdrop else BULLDOZER_CONFIG.get('NODE_PAD', 10)
                root_tolerance = BD_CLUSTER_TOLERANCE if is_root_backdrop else CLUSTER_TOLERANCE
                
                matched = []
                for i, cluster in enumerate(clusters):
                    for cluster_root in cluster:
                        cluster_x = cluster_root.xpos()
                        cluster_y = cluster_root.ypos()
                        cluster_right = cluster_x + _get_node_width(cluster_root)
                        cluster_bottom = cluster_y + _get_node_height(cluster_root)
                        
                        is_cluster_backdrop = cluster_root.Class() == 'BackdropNode'
                        cluster_pad = BULLDOZER_CONFIG.get('BD_PAD', 100) if is_cluster_backdrop else BULLDOZER_CONFIG.get('NODE_PAD', 10)
                        cluster_tolerance = BD_CLUSTER_TOLERANCE if is_cluster_backdrop else CLUSTER_TOLERANCE
                        
                        # --- Tolerance accounts for the padding they push each other by
                        base_tolerance = max(root_tolerance, cluster_tolerance)
                        effective_tolerance = base_tolerance + max(root_pad, cluster_pad)
                        
                        if (root_right + effective_tolerance > cluster_x and 
                            root_x - effective_tolerance < cluster_right and 
                            root_bottom + effective_tolerance > cluster_y and 
                            root_y - effective_tolerance < cluster_bottom):
                            
                            if node_containers.get(root, set()) == node_containers.get(cluster_root, set()):
                                matched.append(i)
                                break
                                
                if not matched:
                    clusters.append([root])
                else:
                    base_idx = matched[0]
                    clusters[base_idx].append(root)
                    for i in reversed(matched[1:]):
                        clusters[base_idx].extend(clusters[i])
                        del clusters[i]
                        
            for cluster in clusters:
                if len(cluster) > 1:
                    new_root = cluster[0]
                    for root in cluster[1:]:
                        groups[new_root].extend(groups.pop(root))
            
        group_bounds = {}
        group_cumulative_push = {}
        final_node_to_root = {}
        
        # --- [ Sort iteration to guarantee consistent math each run ] ---
        # If you don't do this the simulation can be a little different each time you run, 
        # and make you very confused, and sad, and waste a lot of time debugging :(
        for root in sorted(groups.keys(), key=lambda n: n.name()):
            group_nodes = groups[root]
            # --- [ Build a master map of all clustered nodes ] ---
            for node in group_nodes:
                final_node_to_root[node] = root
                
            group_min_x = min(n.xpos() for n in group_nodes)
            group_max_x = max(n.xpos() + _get_node_width(n) for n in group_nodes)
            group_min_y = min(n.ypos() for n in group_nodes)
            group_max_y = max(n.ypos() + _get_node_height(n) for n in group_nodes)
            
            group_bounds[root] = [group_min_x, group_min_y, group_max_x, group_max_y]
            group_cumulative_push[root] = [0, 0]
            
        if VERBOSE_PRINTS:
            print("\n>>> [VERBOSE] RIGID GROUPS (Loose Node Optimization):")
            for root in sorted(groups.keys(), key=lambda n: n.name()):
                group_nodes = groups[root]
                group_names = [gn.name() for gn in group_nodes]
                bounds = group_bounds[root]
                print("  Root: {} | Nodes: {} | Bounds: {}".format(root.name(), group_names, bounds))

    if DEBUG_SWEEP:
        original_selection = nuke.selectedNodes()
        nuke.Undo().disable()
        try:
            # --- [ Draw Sweep Area ] ---
            debug_backdrop = nuke.nodes.BackdropNode(
                xpos=int(min_bounds_x), 
                ypos=int(min_bounds_y),
                bdwidth=int(max_bounds_right - min_bounds_x), 
                bdheight=int(max_bounds_bottom - min_bounds_y),
                tile_color=0xff0000ff, 
                label="DEBUG SWEEP AREA", 
                note_font_size=50, 
                appearance="Border", 
                z_order=999
            )
            try: 
                debug_backdrop.setName("NGB_DEBUG_SWEEP_AREA", uncollide=False)
            except Exception: 
                pass
                
            debug_nodes_to_delete.append(debug_backdrop.name())
            
            # --- [ Draw Primary Movers (Green) ] ---
            for collider in primary_colliders:
                if collider.get('is_selected', False):
                    primary_min_x = min(collider['start_x'], collider['end_x'])
                    primary_min_y = min(collider['start_y'], collider['end_y'])
                    primary_max_x = max(collider['start_right'], collider['end_right'])
                    primary_max_y = max(collider['start_bottom'], collider['end_bottom'])
                    
                    primary_backdrop = nuke.nodes.BackdropNode(
                        xpos=int(primary_min_x), 
                        ypos=int(primary_min_y),
                        bdwidth=int(max(20, primary_max_x - primary_min_x)), 
                        bdheight=int(max(20, primary_max_y - primary_min_y)),
                        tile_color=0x00ff00ff, 
                        label="PRIMARY MOVER", 
                        note_font_size=30, 
                        appearance="Border", 
                        z_order=999
                    )
                    try: 
                        primary_backdrop.setName("NGB_DEBUG_PRIMARY_MOVER", uncollide=False)
                    except Exception: 
                        pass
                        
                    debug_nodes_to_delete.append(primary_backdrop.name())
                    
            # --- [ Draw Bystanders (Purple) ] ---
            if DEBUG_BYSTANDERS and local_bystanders:
                for root in sorted(groups.keys(), key=lambda n: n.name()):
                    bounds = group_bounds[root]
                    group_x1, group_y1, group_x2, group_y2 = bounds
                    bystander_pad = BULLDOZER_CONFIG.get('BD_PAD', 100) if root.Class() == 'BackdropNode' else BULLDOZER_CONFIG.get('NODE_PAD', 10)
                    
                    bystander_backdrop = nuke.nodes.BackdropNode(
                        xpos=int(group_x1 - bystander_pad), 
                        ypos=int(group_y1 - bystander_pad),
                        bdwidth=int(max(20, (group_x2 - group_x1) + bystander_pad * 2)), 
                        bdheight=int(max(20, (group_y2 - group_y1) + bystander_pad * 2)),
                        tile_color=0xd020ffff, 
                        label="BYSTANDER GROUP", 
                        note_font_size=20, 
                        appearance="Border", 
                        z_order=999
                    )
                    try: 
                        bystander_backdrop.setName("NGB_DEBUG_BYSTANDER", uncollide=False)
                    except Exception: 
                        pass
                        
                    debug_nodes_to_delete.append(bystander_backdrop.name())
                    
        finally:
            nuke.Undo().enable()
            # --- [ Prevent debug nodes from hijacking the users selection ] ---
            for node in nuke.allNodes():
                if node.name().startswith('NGB_DEBUG_'):
                    node.setSelected(False)
            for node in original_selection:
                try: 
                    node.setSelected(True)
                except Exception: 
                    pass

    max_dist = 0
    for collider in primary_colliders:
        dist_x = abs(collider['end_x'] - collider['start_x']) + abs(collider['end_right'] - collider['start_right'])
        dist_y = abs(collider['end_y'] - collider['start_y']) + abs(collider['end_bottom'] - collider['start_bottom'])
        max_dist = max(max_dist, dist_x, dist_y)
        
    num_steps = max(1, int(max_dist / SIM_MAX_STEP_SIZE) + 1)
    
    if DEBUG_SWEEP:
        print("\n--- [ BULLDOZER PHYSICS ENGINE DIAGNOSTICS ] ---")
        print("Max Move Dist   : {}".format(max_dist))
        print("Primary Movers  : {}".format(len(primary_colliders)))
        print("Bystanders Found: {}".format(len(local_bystanders)))
        print("Rigid Groups    : {}".format(len(groups)))
        print("Sim Steps Needed: {}".format(num_steps))
    
    debug_overlap_checks = 0
    max_iteration_hit = False
    max_iteration_reached = 0
    
    # --- [ Determine primary colliders fallback or override logic ] ---
    collider_map = interpolation_map if interpolation_map is not None else {collider['node']: collider for collider in primary_colliders}
    
    # --- [ Process backdrops from smallest to largest to compute nested expanding bounds ] ---
    sorted_backdrops = sorted(affected_bds.keys(), key=lambda b: b.knob('bdwidth').value() * b.knob('bdheight').value())
    
    # --- [ DYNAMIC CHAIN RESOLUTION ] ---
    # --- Automatically scales up if there are many unclustered nodes in a long chain
    active_iterations = max(SIM_MAX_ITERATIONS, len(groups) + 2)
    
    step_start_bd_bounds = {}
    
    for backdrop in sorted_backdrops:
        data = affected_bds[backdrop]
        step_start_bd_bounds[backdrop] = (data['orig_x'], data['orig_y'], data['orig_r'], data['orig_b'])
        
    # --- [ Sort roots to evaluate physics consistently ] ---
    sorted_group_roots = sorted(group_bounds.keys(), key=lambda x: x.name())

    for step in range(1, num_steps + 1):
        time_prev = float(step - 1) / num_steps
        time_current = float(step) / num_steps
        current_colliders = []
        
        for collider in primary_colliders:
            start_x = collider['start_x']
            end_x = collider['end_x']
            start_y = collider['start_y']
            end_y = collider['end_y']
            start_right = collider['start_right']
            end_right = collider['end_right']
            start_bottom = collider['start_bottom']
            end_bottom = collider['end_bottom']

            prev_left = start_x + (end_x - start_x) * time_prev
            curr_left = start_x + (end_x - start_x) * time_current
            
            prev_top = start_y + (end_y - start_y) * time_prev
            curr_top = start_y + (end_y - start_y) * time_current
            
            prev_right = start_right + (end_right - start_right) * time_prev
            curr_right = start_right + (end_right - start_right) * time_current
            
            prev_bottom = start_bottom + (end_bottom - start_bottom) * time_prev
            curr_bottom = start_bottom + (end_bottom - start_bottom) * time_current
            
            velocity_left = curr_left - prev_left
            velocity_right = curr_right - prev_right
            velocity_top = curr_top - prev_top
            velocity_bottom = curr_bottom - prev_bottom
            
            current_colliders.append((
                min(prev_left, curr_left), 
                min(prev_top, curr_top), 
                max(prev_right, curr_right), 
                max(prev_bottom, curr_bottom), 
                collider['padding'], 
                collider['node'], 
                collider['ignore_set'], 
                velocity_left, 
                velocity_right, 
                velocity_top, 
                velocity_bottom, 
                False
            ))
            
        for iteration in range(active_iterations):
            moved_in_pass = False
            
            # --- [ Calculate Expansion Velocity for Collisions ] ---
            dynamic_backdrop_bounds = {}
            dynamic_expanding_colliders = []
            
            for backdrop in sorted_backdrops:
                data = affected_bds[backdrop]
                current_min_x = float('inf')
                current_min_y = float('inf')
                current_max_x = float('-inf')
                current_max_y = float('-inf')
                
                for node in data['nodes']:
                    if node in collider_map:
                        mapped_collider = collider_map[node]
                        current_node_x = mapped_collider['start_x'] + (mapped_collider['end_x'] - mapped_collider['start_x']) * time_current
                        current_node_y = mapped_collider['start_y'] + (mapped_collider['end_y'] - mapped_collider['start_y']) * time_current
                        current_node_right = mapped_collider['start_right'] + (mapped_collider['end_right'] - mapped_collider['start_right']) * time_current
                        current_node_bottom = mapped_collider['start_bottom'] + (mapped_collider['end_bottom'] - mapped_collider['start_bottom']) * time_current
                    else:
                        # --- Send the push to the root 
                        root_node = final_node_to_root.get(node, node)
                        push_x, push_y = group_cumulative_push.get(root_node, [0, 0])
                        
                        if node in dynamic_backdrop_bounds:
                            current_node_x, current_node_y, current_node_right, current_node_bottom = dynamic_backdrop_bounds[node]['padded']
                        else:
                            current_node_x = node.xpos() + push_x
                            current_node_y = node.ypos() + push_y
                            current_node_right = current_node_x + _get_node_width(node)
                            current_node_bottom = current_node_y + _get_node_height(node)
                            
                    current_min_x = min(current_min_x, current_node_x)
                    current_min_y = min(current_min_y, current_node_y)
                    current_max_x = max(current_max_x, current_node_right)
                    current_max_y = max(current_max_y, current_node_bottom)

                current_x = current_min_x - data['pad_l']
                current_y = current_min_y - data['pad_t']
                current_right = current_max_x + data['pad_r']
                current_bottom = current_max_y + data['pad_b']
                
                dynamic_backdrop_bounds[backdrop] = {
                    'raw': (current_min_x, current_min_y, current_max_x, current_max_y),
                    'padded': (current_x, current_y, current_right, current_bottom)
                }
                
                prev_x, prev_y, prev_right, prev_bottom = step_start_bd_bounds[backdrop]
                
                velocity_left = current_x - prev_x
                velocity_right = current_right - prev_right
                velocity_top = current_y - prev_y
                velocity_bottom = current_bottom - prev_bottom
                
                is_expanding = False
                TOLERANCE = 0.01
                if velocity_right > TOLERANCE or velocity_left < -TOLERANCE or velocity_bottom > TOLERANCE or velocity_top < -TOLERANCE:
                    is_expanding = True
                    
                if is_expanding:
                    # --- [ Calculate boundary velocity for the solver ] --- 
                    velocity_left = current_x - prev_x
                    velocity_right = current_right - prev_right
                    velocity_top = current_y - prev_y
                    velocity_bottom = current_bottom - prev_bottom
                    
                    # --- If these are not zero, the backdrop expansion is effectively a "push"
                    # --- Even if the bd xpos is static, the bounds should displace neighbors
                    dynamic_expanding_colliders.append((
                        min(prev_x, current_x), 
                        min(prev_y, current_y), 
                        max(prev_right, current_right), 
                        max(prev_bottom, current_bottom), 
                        BULLDOZER_CONFIG.get('BD_PAD', 100), 
                        backdrop, 
                        set(data['nodes']), 
                        velocity_left, 
                        velocity_right, 
                        velocity_top, 
                        velocity_bottom, 
                        True
                    ))

            active_colliders = current_colliders + dynamic_expanding_colliders

            # --- [ Iterate using the sorted list of roots ] ---
            for root in sorted_group_roots:
                bounds = group_bounds[root]
                group_nodes_set = set(groups[root])
                group_x1, group_y1, group_x2, group_y2 = bounds
                needed = [0, 0]
                
                def check_overlap(obs_start_x, obs_start_y, obs_end_x, obs_end_y, obs_pad, vel_left, vel_right, vel_top, vel_bottom):
                    raw_overlap_left = group_x2 - obs_start_x
                    raw_overlap_right = obs_end_x - group_x1
                    raw_overlap_top = group_y2 - obs_start_y
                    raw_overlap_bottom = obs_end_y - group_y1
                    
                    overlap_left = raw_overlap_left
                    overlap_right = raw_overlap_right
                    overlap_top = raw_overlap_top
                    overlap_bottom = raw_overlap_bottom
                    
                    # --- [ Apply padding to the "front" and "sides" of the movement ] ---
                    # ---- but strip padding from the "rear" to prevent dragging nodes backwards
                    if vel_left <= 0.01: 
                        overlap_left += obs_pad
                    if vel_right >= -0.01: 
                        overlap_right += obs_pad
                    if vel_top <= 0.01: 
                        overlap_top += obs_pad
                    if vel_bottom >= -0.01: 
                        overlap_bottom += obs_pad
                    
                    if overlap_left <= 0 or overlap_right <= 0 or overlap_top <= 0 or overlap_bottom <= 0:
                        return
                        
                    # --- [ Ignore Side grazing ] ---
                    if not allow_dx and (raw_overlap_left <= 0 or raw_overlap_right <= 0):
                        return
                    if not allow_dy and (raw_overlap_top <= 0 or raw_overlap_bottom <= 0):
                        return
                        
                    push_x = 0
                    push_y = 0
                    center_x = (group_x1 + group_x2) / 2.0
                    center_y = (group_y1 + group_y2) / 2.0
                    
                    # --- [ Routing direction for minimum translation vector ] ---
                    if mode_direction in ('left', 'right', 'up', 'down'):
                        if mode_direction == 'right': 
                            push_x = overlap_right
                        elif mode_direction == 'left': 
                            push_x = -overlap_left
                        elif mode_direction == 'down': 
                            push_y = overlap_bottom
                        elif mode_direction == 'up': 
                            push_y = -overlap_top
                    else:
                        # --- Omnidirectional check for Scale
                        if axis_w:
                            if center_x >= px_abs: 
                                push_x = overlap_right
                            else:                  
                                push_x = -overlap_left
                        if axis_h:
                            if center_y >= py_abs: 
                                push_y = overlap_bottom
                            else:                  
                                push_y = -overlap_top
                            
                        if axis_w and axis_h:
                            if abs(push_x) < abs(push_y): 
                                push_y = 0
                            else:                     
                                push_x = 0
                            
                    if push_x > 0: 
                        needed[0] = max(needed[0], push_x)
                    elif push_x < 0: 
                        needed[0] = min(needed[0], push_x)
                    
                    if push_y > 0: 
                        needed[1] = max(needed[1], push_y)
                    elif push_y < 0: 
                        needed[1] = min(needed[1], push_y)

                for obs_start_x, obs_start_y, obs_end_x, obs_end_y, obs_pad, obstacle_node, ignore_set, vel_left, vel_right, vel_top, vel_bottom, is_exp_bd in active_colliders:
                    ignore_collision = False
                    if root == obstacle_node or root in ignore_set or not ignore_set.isdisjoint(group_nodes_set):
                        ignore_collision = True
                    
                    if not ignore_collision:
                        root_containers = node_containers.get(root, set())
                        if is_exp_bd:
                            # --- Expanding backdrops bypass containment checks, they push everything not inside them
                            if obstacle_node in root_containers:
                                ignore_collision = True
                        else:
                            obs_containers = node_containers.get(obstacle_node, set())
                            if not obs_containers.issubset(root_containers):
                                ignore_collision = True
                                
                    if not ignore_collision:
                        debug_overlap_checks += 1
                        check_overlap(obs_start_x, obs_start_y, obs_end_x, obs_end_y, obs_pad, vel_left, vel_right, vel_top, vel_bottom)
                        
                # --- [ Iterate other checking using the sorted roots ] ---
                for other_root in sorted_group_roots:
                    if root != other_root:
                        other_bounds = group_bounds[other_root]
                        other_dx_total, other_dy_total = group_cumulative_push[other_root]
                        
                        if other_dx_total != 0 or other_dy_total != 0:
                            ignore_collision = False
                            obs_containers = node_containers.get(other_root, set())
                            root_containers = node_containers.get(root, set())
                            
                            if not obs_containers.issubset(root_containers):
                                ignore_collision = True
                                
                            if not ignore_collision:
                                debug_overlap_checks += 1
                                other_pad = BULLDOZER_CONFIG.get('BD_PAD', 100) if other_root.Class() == 'BackdropNode' else BULLDOZER_CONFIG.get('NODE_PAD', 10)
                                check_overlap(
                                    other_bounds[0], 
                                    other_bounds[1], 
                                    other_bounds[2], 
                                    other_bounds[3], 
                                    other_pad, 
                                    other_dx_total, 
                                    other_dx_total, 
                                    other_dy_total, 
                                    other_dy_total
                                )
                                
                if needed[0] != 0 or needed[1] != 0:
                    if VERBOSE_PRINTS:
                        print("  [VERBOSE] Step {}/{} | Iter {} | Pushing Group Root '{}' by dx:{:.2f}, dy:{:.2f}".format(
                            step, num_steps, iteration + 1, root.name(), needed[0], needed[1]))

                    bounds[0] += needed[0]
                    bounds[2] += needed[0]
                    bounds[1] += needed[1]
                    bounds[3] += needed[1]
                    
                    group_cumulative_push[root][0] += needed[0]
                    group_cumulative_push[root][1] += needed[1]
                    moved_in_pass = True
                    
            if not moved_in_pass:
                break
                
        max_iteration_reached = max(max_iteration_reached, iteration + 1)
        if iteration == active_iterations - 1 and moved_in_pass:
            max_iteration_hit = True
            
        # --- [ Update the bounds for backdrops so the next sub step calculates velocity correctly ] ---
        for backdrop in sorted_backdrops:
            if backdrop in dynamic_backdrop_bounds:
                step_start_bd_bounds[backdrop] = dynamic_backdrop_bounds[backdrop]['padded']

    for root in sorted_group_roots:
        group_nodes = groups[root]
        total_dx, total_dy = group_cumulative_push[root]
        if total_dx != 0 or total_dy != 0:
            for node in group_nodes:
                node.setXYpos(int(node.xpos() + total_dx), int(node.ypos() + total_dy))
                
            if DEBUG_SWEEP:
                original_selection = nuke.selectedNodes()
                nuke.Undo().disable()
                try:
                    group_x1, group_y1, group_x2, group_y2 = group_bounds[root]
                    debug_pad = BULLDOZER_CONFIG.get('NODE_PAD', 10)
                    
                    group_backdrop = nuke.nodes.BackdropNode(
                        xpos=int(group_x1 - debug_pad), 
                        ypos=int(group_y1 - debug_pad),
                        bdwidth=int(max(20, (group_x2 - group_x1) + debug_pad * 2)), 
                        bdheight=int(max(20, (group_y2 - group_y1) + debug_pad * 2)),
                        tile_color=0xffff00ff, 
                        label="SECONDARY MOVER", 
                        note_font_size=30, 
                        appearance="Border", 
                        z_order=999
                    )
                    try: 
                        group_backdrop.setName("NGB_DEBUG_SECONDARY_MOVER", uncollide=False)
                    except Exception: 
                        pass
                        
                    debug_nodes_to_delete.append(group_backdrop.name())
                finally:
                    nuke.Undo().enable()
                    for node in nuke.allNodes():
                        if node.name().startswith('NGB_DEBUG_'):
                            node.setSelected(False)
                    for node in original_selection:
                        try: 
                            node.setSelected(True)
                        except Exception: 
                            pass
                
    if max_iteration_hit and DEBUG_SWEEP:
        original_selection = nuke.selectedNodes()
        nuke.Undo().disable()
        try:
            sticky_note = nuke.nodes.StickyNote(
                xpos=int(min_bounds_x),
                ypos=int(min_bounds_y - 150),
                label="MAX ITERATIONS HIT!\nNodes may overlap.\nIncrease max iterations in Panel.",
                note_font_size=999,
                tile_color=0xff0000ff
            )
            try: 
                sticky_note.setName("NGB_DEBUG_MAX_ITER_WARN", uncollide=False)
            except Exception: 
                pass
                
            debug_nodes_to_delete.append(sticky_note.name())
        finally:
            nuke.Undo().enable()
            for node in nuke.allNodes():
                if node.name().startswith('NGB_DEBUG_'):
                    node.setSelected(False)
            for node in original_selection:
                try: 
                    node.setSelected(True)
                except Exception: 
                    pass

    if DEBUG_SWEEP or DEBUG_BYSTANDERS:
        # --- this can be adjusted to change the duration the debug backdrops hang around
        QtCore.QTimer.singleShot(2500, remove_debug_nodes)
        

# ===============================================================================
#                            ---- Smart Scale ----
# ===============================================================================

def scale_nodes_advanced(mode='increase', direction='bdwidth'):
    """Scales selected nodes and pushes bystanders away using bulldozer physics"""
    global ORIGINAL_SCALE_CACHE

    if direction not in DIRECTION_FLAGS:
        raise ValueError("Unknown direction: %s" % direction)

    # --- [ Sort selection to ensure stable logic loops ] ---
    selection = sorted(nuke.selectedNodes(), key=lambda n: n.name())
    if not selection:
        return
        
    # --- [ Get node graph data here to avoid looping bottlenecks downstream ] ---
    all_nodes = nuke.allNodes()
    all_bds_eval = [b for b in nuke.allNodes('BackdropNode') if not b.name().startswith('NGB_DEBUG_')]
    
    # --- [ Find potential parent backdrops before building the slow containment cache ] ---
    bds_to_check = set()
    if SCALE_BIAS_CONFIG['USE_BULLDOZER']:
        all_backdrops = [node for node in all_bds_eval if node not in selection]
        for node in selection:
            node_x = node.xpos() + _get_node_width(node) / 2.0
            node_y = node.ypos() + _get_node_height(node) / 2.0
            for backdrop in all_backdrops:
                backdrop_x = backdrop.xpos()
                backdrop_y = backdrop.ypos()
                backdrop_width = backdrop.knob('bdwidth').value()
                backdrop_height = backdrop.knob('bdheight').value()
                
                if backdrop_x < node_x < backdrop_x + backdrop_width and backdrop_y < node_y < backdrop_y + backdrop_height:
                    bds_to_check.add(backdrop)
                    
    # --- [ Build fast backdrop containment cache for relevant backdrops ] ---
    master_bd_list = list(bds_to_check.union([b for b in selection if b.Class() == 'BackdropNode']))
    master_bd_map = _get_nodes_in_backdrops(master_bd_list)
    
    base_multiplier = float(BULLDOZER_CONFIG.get('ZOOM_MULTIPLIER', 10))
    if BULLDOZER_CONFIG.get('USE_ZOOM', True):
        zoom_level = nuke.zoom()
        if zoom_level <= 0: 
            zoom_level = 1.0
        delta = int(base_multiplier / zoom_level)
    else:
        delta = int(base_multiplier)
        
    delta *= (-1 if mode == 'decrease' else 1)
    
    axis_w, axis_h = DIRECTION_FLAGS[direction]
    
    horizontal_center = SCALE_BIAS_CONFIG['H_CENTER']
    vertical_center = SCALE_BIAS_CONFIG['V_CENTER']

    if axis_w and direction.startswith('bdwidth') and horizontal_center == 'right':
        delta = -delta
    if axis_h and direction == 'bdheight' and vertical_center == 'bottom':
        delta = -delta

    if direction == 'bdwidth':
        px = 0.0 if horizontal_center == 'left' else 1.0
        py = 0.0
    elif direction == 'bdwidth_center':
        px, py = 0.5, 0.0
    elif direction == 'bdheight':
        px = 0.0
        py = 0.0 if vertical_center == 'top' else 1.0
    elif direction == 'bdheight_center':
        px, py = 0.0, 0.5
    elif direction == 'bdboth_center':
        px, py = 0.5, 0.5
    elif direction in ('bdboth_top', 'bdboth_bottom'):
        px = 0.0 if horizontal_center == 'left' else 1.0
        py = 0.0 if vertical_center == 'top' else 1.0

    current_pos = (selection[0].xpos(), selection[0].ypos())
    key = (tuple(selection), direction, horizontal_center, vertical_center, SCALE_BIAS_CONFIG.get('DONT_SCALE_NESTED', False))
    
    if ORIGINAL_SCALE_CACHE.get('key') != key or ORIGINAL_SCALE_CACHE.get('expected_pos') != current_pos:
        ORIGINAL_SCALE_CACHE.clear()
        ORIGINAL_SCALE_CACHE['key'] = key
        
        backdrop_selection = [node for node in selection if node.Class() == 'BackdropNode']
        node_selection = [node for node in selection if node.Class() != 'BackdropNode']
        
        # --- [ Identify nested backdrops if requested ] ---
        if SCALE_BIAS_CONFIG.get('DONT_SCALE_NESTED', False):
            nested_backdrops = set()
            for bd1 in backdrop_selection:
                bd1_x = bd1.xpos()
                bd1_y = bd1.ypos()
                bd1_right = bd1_x + bd1['bdwidth'].value()
                bd1_bottom = bd1_y + bd1['bdheight'].value()
                
                for bd2 in backdrop_selection:
                    if bd1.name() == bd2.name(): 
                        continue
                        
                    bd2_x = bd2.xpos()
                    bd2_y = bd2.ypos()
                    bd2_right = bd2_x + bd2['bdwidth'].value()
                    bd2_bottom = bd2_y + bd2['bdheight'].value()
                    
                    # --- Check if bd1 is completely inside bd2
                    if bd1_x >= bd2_x and bd1_y >= bd2_y and bd1_right <= bd2_right and bd1_bottom <= bd2_bottom:
                        # --- Tiebreaker for perfectly overlapping backdrops
                        if bd1_x == bd2_x and bd1_y == bd2_y and bd1_right == bd2_right and bd1_bottom == bd2_bottom:
                            if bd1.name() > bd2.name():
                                nested_backdrops.add(bd1)
                                break
                        else:
                            nested_backdrops.add(bd1)
                            break
                            
            root_backdrop_selection = [b for b in backdrop_selection if b not in nested_backdrops]
            
            # --- [ Find rigid group roots (nested backdrops not inside other nested backdrops) ] ---
            rigid_roots = []
            for bd1 in nested_backdrops:
                bd1_x = bd1.xpos()
                bd1_y = bd1.ypos()
                bd1_right = bd1_x + bd1['bdwidth'].value()
                bd1_bottom = bd1_y + bd1['bdheight'].value()
                is_deeply_nested = False
                
                for bd2 in nested_backdrops:
                    if bd1.name() == bd2.name(): 
                        continue
                        
                    bd2_x = bd2.xpos()
                    bd2_y = bd2.ypos()
                    bd2_right = bd2_x + bd2['bdwidth'].value()
                    bd2_bottom = bd2_y + bd2['bdheight'].value()
                    
                    if bd1_x >= bd2_x and bd1_y >= bd2_y and bd1_right <= bd2_right and bd1_bottom <= bd2_bottom:
                        if bd1_x == bd2_x and bd1_y == bd2_y and bd1_right == bd2_right and bd1_bottom == bd2_bottom:
                            if bd1.name() > bd2.name():
                                is_deeply_nested = True
                                break
                        else:
                            is_deeply_nested = True
                            break
                            
                if not is_deeply_nested:
                    rigid_roots.append(bd1)

            # --- [ Collect all selected nodes that fall inside the rigid roots ] ---
            rigid_children_map = {}
            all_rigid_children = set()
            for r_root in rigid_roots:
                rigid_children_map[r_root] = []
                for node in r_root.getNodes():
                    if node in selection and node != r_root:
                        rigid_children_map[r_root].append(node)
                        all_rigid_children.add(node)
            
            node_selection = [node for node in node_selection if node not in all_rigid_children]
            
            ORIGINAL_SCALE_CACHE['orig_rigid_roots'] = [
                (
                    backdrop, 
                    backdrop.xpos() + backdrop['bdwidth'].value() / 2.0, 
                    backdrop.ypos() + backdrop['bdheight'].value() / 2.0, 
                    backdrop['bdwidth'].value(), 
                    backdrop['bdheight'].value()
                )
                for backdrop in rigid_roots
            ]
            
            ORIGINAL_SCALE_CACHE['orig_rigid_children'] = []
            for r_root in rigid_roots:
                for child in rigid_children_map[r_root]:
                    is_backdrop = child.Class() == 'BackdropNode'
                    child_width = child['bdwidth'].value() if is_backdrop else child.screenWidth()
                    child_height = child['bdheight'].value() if is_backdrop else child.screenHeight()
                    
                    ORIGINAL_SCALE_CACHE['orig_rigid_children'].append(
                        (child, child.xpos(), child.ypos(), child_width, child_height, is_backdrop, r_root)
                    )

        else:
            root_backdrop_selection = backdrop_selection
            ORIGINAL_SCALE_CACHE['orig_rigid_roots'] = []
            ORIGINAL_SCALE_CACHE['orig_rigid_children'] = []
            
        ORIGINAL_SCALE_CACHE['orig_bd'] = [
            (
                backdrop, 
                backdrop.xpos(), 
                backdrop.ypos(), 
                backdrop['bdwidth'].value(), 
                backdrop['bdheight'].value(), 
                backdrop['bdwidth'], 
                backdrop['bdheight']
            )
            for backdrop in root_backdrop_selection
        ]
        
        ORIGINAL_SCALE_CACHE['orig_ctr'] = [
            (
                node, 
                node.xpos() + node.screenWidth() / 2.0, 
                node.ypos() + node.screenHeight() / 2.0, 
                node.screenWidth(), 
                node.screenHeight()
            )
            for node in node_selection
        ]
        
        all_xs, all_ys, all_x_widths, all_y_heights = [], [], [], []
        for backdrop, x, y, width, height, kw, kh in ORIGINAL_SCALE_CACHE['orig_bd']:
            all_xs.append(x)
            all_ys.append(y)
            all_x_widths.append(x + width)
            all_y_heights.append(y + height)
            
        for node, center_x, center_y, width, height in ORIGINAL_SCALE_CACHE['orig_ctr']:
            all_xs.append(center_x)
            all_ys.append(center_y)
            all_x_widths.append(center_x)
            all_y_heights.append(center_y)
            
        for backdrop, center_x, center_y, width, height in ORIGINAL_SCALE_CACHE.get('orig_rigid_roots', []):
            all_xs.append(center_x)
            all_ys.append(center_y)
            all_x_widths.append(center_x)
            all_y_heights.append(center_y)
            
        box_x0 = min(all_xs)
        box_y0 = min(all_ys)
        original_width = max(all_x_widths) - box_x0
        original_height = max(all_y_heights) - box_y0
        
        ORIGINAL_SCALE_CACHE['orig_bbox'] = (box_x0, box_y0, original_width, original_height)
        ORIGINAL_SCALE_CACHE['curr_w'] = original_width
        ORIGINAL_SCALE_CACHE['curr_h'] = original_height

    orig_bd = ORIGINAL_SCALE_CACHE['orig_bd']
    orig_ctr = ORIGINAL_SCALE_CACHE['orig_ctr']
    box_x0, box_y0, original_width, original_height = ORIGINAL_SCALE_CACHE['orig_bbox']
    current_width, current_height = ORIGINAL_SCALE_CACHE['curr_w'], ORIGINAL_SCALE_CACHE['curr_h']

    new_width = current_width + delta if axis_w else current_width
    new_height = current_height + delta if axis_h else current_height
    
    if axis_w: 
        new_width = max(25, new_width)
    if axis_h: 
        new_height = max(25, new_height)

    scale_w = new_width / original_width if original_width else 1.0
    scale_h = new_height / original_height if original_height else 1.0

    px_abs = box_x0 + px * original_width
    py_abs = box_y0 + py * original_height

    run_physics = SCALE_BIAS_CONFIG['USE_BULLDOZER'] and (mode == 'increase')
    
    affected_bds = {}
    if SCALE_BIAS_CONFIG['USE_BULLDOZER']:
        for backdrop in bds_to_check:
            contained_content = master_bd_map.get(backdrop, set())
            if any(node in selection for node in contained_content):
                if not contained_content: 
                    continue
                    
                min_x = min(node.xpos() for node in contained_content)
                min_y = min(node.ypos() for node in contained_content)
                max_x = max(node.xpos() + _get_node_width(node) for node in contained_content)
                max_y = max(node.ypos() + _get_node_height(node) for node in contained_content)
                
                affected_bds[backdrop] = {
                    'pad_l': min_x - backdrop.xpos(), 
                    'pad_t': min_y - backdrop.ypos(), 
                    'pad_r': (backdrop.xpos() + backdrop.knob('bdwidth').value()) - max_x, 
                    'pad_b': (backdrop.ypos() + backdrop.knob('bdheight').value()) - max_y, 
                    'nodes': contained_content,
                    'orig_x': backdrop.xpos(), 
                    'orig_y': backdrop.ypos(),
                    'orig_r': backdrop.xpos() + backdrop.knob('bdwidth').value(),
                    'orig_b': backdrop.ypos() + backdrop.knob('bdheight').value()
                }

    primary_colliders = []
    
    nuke.Undo().begin("NodeGraphBuddy Scale")
    try:
        for backdrop, ox, oy, ow, oh, knob_w, knob_h in orig_bd:
            new_bd_width = ow * scale_w if axis_w else ow
            new_bd_height = oh * scale_h if axis_h else oh
            new_bd_x = px_abs + (ox - px_abs) * scale_w
            new_bd_y = py_abs + (oy - py_abs) * scale_h
            
            if run_physics:
                start_x = backdrop.xpos()
                start_y = backdrop.ypos()
                start_right = start_x + backdrop['bdwidth'].value()
                start_bottom = start_y + backdrop['bdheight'].value()
                
                end_x = new_bd_x
                end_y = new_bd_y
                end_right = new_bd_x + new_bd_width
                end_bottom = new_bd_y + new_bd_height
                
                primary_colliders.append({
                    'node': backdrop, 
                    'start_x': start_x, 
                    'start_y': start_y, 
                    'start_right': start_right, 
                    'start_bottom': start_bottom, 
                    'end_x': end_x, 
                    'end_y': end_y, 
                    'end_right': end_right, 
                    'end_bottom': end_bottom, 
                    'padding': BULLDOZER_CONFIG.get('BD_PAD', 100), 
                    'ignore_set': set(backdrop.getNodes()), 
                    'is_selected': True
                })
            
            if axis_w: 
                knob_w.setValue(new_bd_width)
            if axis_h: 
                knob_h.setValue(new_bd_height)
                
            backdrop.setXYpos(int(round(new_bd_x)), int(round(new_bd_y)))

        for node, center_x, center_y, node_width, node_height in orig_ctr:
            new_center_x = px_abs + (center_x - px_abs) * scale_w
            new_center_y = py_abs + (center_y - py_abs) * scale_h
            new_node_x = new_center_x - node_width / 2.0
            new_node_y = new_center_y - node_height / 2.0
            
            if run_physics:
                start_x = node.xpos()
                start_y = node.ypos()
                start_right = start_x + node_width
                start_bottom = start_y + node_height
                
                end_x = new_node_x
                end_y = new_node_y
                end_right = new_node_x + node_width
                end_bottom = new_node_y + node_height
                
                is_backdrop = node.Class() == 'BackdropNode'
                pad = BULLDOZER_CONFIG.get('BD_PAD', 100) if is_backdrop else BULLDOZER_CONFIG.get('NODE_PAD', 10)
                ignore_set = set(node.getNodes()) if is_backdrop else set()
                
                primary_colliders.append({
                    'node': node, 
                    'start_x': start_x, 
                    'start_y': start_y, 
                    'start_right': start_right, 
                    'start_bottom': start_bottom, 
                    'end_x': end_x, 
                    'end_y': end_y, 
                    'end_right': end_right, 
                    'end_bottom': end_bottom, 
                    'padding': pad, 
                    'ignore_set': ignore_set, 
                    'is_selected': True
                })
                
            node.setXYpos(int(round(new_node_x)), int(round(new_node_y)))

        # --- [ Process rigid roots ] ---
        rigid_root_deltas = {}
        for r_root, center_x, center_y, width, height in ORIGINAL_SCALE_CACHE.get('orig_rigid_roots', []):
            new_center_x = px_abs + (center_x - px_abs) * scale_w
            new_center_y = py_abs + (center_y - py_abs) * scale_h
            new_node_x = new_center_x - width / 2.0
            new_node_y = new_center_y - height / 2.0
            
            original_x = center_x - width / 2.0
            original_y = center_y - height / 2.0
            delta_x = new_node_x - original_x
            delta_y = new_node_y - original_y
            
            rigid_root_deltas[r_root] = (delta_x, delta_y)
            
            if run_physics:
                start_x = r_root.xpos()
                start_y = r_root.ypos()
                start_right = start_x + width
                start_bottom = start_y + height
                
                end_x = new_node_x
                end_y = new_node_y
                end_right = new_node_x + width
                end_bottom = new_node_y + height
                
                pad = BULLDOZER_CONFIG.get('BD_PAD', 100)
                
                primary_colliders.append({
                    'node': r_root, 
                    'start_x': start_x, 
                    'start_y': start_y, 
                    'start_right': start_right, 
                    'start_bottom': start_bottom, 
                    'end_x': end_x, 
                    'end_y': end_y, 
                    'end_right': end_right, 
                    'end_bottom': end_bottom, 
                    'padding': pad, 
                    'ignore_set': set(r_root.getNodes()), 
                    'is_selected': True
                })
                
            r_root.setXYpos(int(round(new_node_x)), int(round(new_node_y)))
            
        # --- [ Process rigid children ] ---
        for child, original_x, original_y, width, height, is_backdrop, r_root in ORIGINAL_SCALE_CACHE.get('orig_rigid_children', []):
            delta_x, delta_y = rigid_root_deltas[r_root]
            new_node_x = original_x + delta_x
            new_node_y = original_y + delta_y
            
            if run_physics:
                start_x = child.xpos()
                start_y = child.ypos()
                start_right = start_x + width
                start_bottom = start_y + height
                
                end_x = new_node_x
                end_y = new_node_y
                end_right = new_node_x + width
                end_bottom = new_node_y + height
                
                pad = BULLDOZER_CONFIG.get('BD_PAD', 100) if is_backdrop else BULLDOZER_CONFIG.get('NODE_PAD', 10)
                ignore_set = set(child.getNodes()) if is_backdrop else set()
                
                primary_colliders.append({
                    'node': child, 
                    'start_x': start_x, 
                    'start_y': start_y, 
                    'start_right': start_right, 
                    'start_bottom': start_bottom, 
                    'end_x': end_x, 
                    'end_y': end_y, 
                    'end_right': end_right, 
                    'end_bottom': end_bottom, 
                    'padding': pad, 
                    'ignore_set': ignore_set, 
                    'is_selected': True
                })
                
            child.setXYpos(int(round(new_node_x)), int(round(new_node_y)))
            
        sorted_backdrops = sorted(affected_bds.keys(), key=lambda b: b.knob('bdwidth').value() * b.knob('bdheight').value())
        for backdrop in sorted_backdrops:
            data = affected_bds[backdrop]
            contained_content = data['nodes']
            
            new_min_x = min(node.xpos() for node in contained_content)
            new_min_y = min(node.ypos() for node in contained_content)
            new_max_x = max(node.xpos() + _get_node_width(node) for node in contained_content)
            new_max_y = max(node.ypos() + _get_node_height(node) for node in contained_content)
            
            proposed_x = new_min_x - data['pad_l']
            proposed_y = new_min_y - data['pad_t']
            proposed_right = new_max_x + data['pad_r']
            proposed_bottom = new_max_y + data['pad_b']
            
            backdrop.setXYpos(proposed_x, proposed_y)
            backdrop.knob('bdwidth').setValue(max(20.0, proposed_right - proposed_x))
            backdrop.knob('bdheight').setValue(max(20.0, proposed_bottom - proposed_y))

        if run_physics and primary_colliders:
            # --- [ Merge Colliders if "TREAT_AS_ONE" is True ] ---
            merged_colliders, interpolation_map = _merge_primary_colliders(primary_colliders, selection, all_nodes, master_bd_map)
            
            min_bounds_x = min(min(collider['start_x'], collider['end_x']) for collider in merged_colliders)
            min_bounds_y = min(min(collider['start_y'], collider['end_y']) for collider in merged_colliders)
            max_bounds_right = max(max(collider['start_right'], collider['end_right']) for collider in merged_colliders)
            max_bounds_bottom = max(max(collider['start_bottom'], collider['end_bottom']) for collider in merged_colliders)
            
            if affected_bds:
                ab_min_bounds_x = min(data['orig_x'] for data in affected_bds.values())
                ab_min_bounds_y = min(data['orig_y'] for data in affected_bds.values())
                ab_max_bounds_right = max(data['orig_r'] for data in affected_bds.values())
                ab_max_bounds_bottom = max(data['orig_b'] for data in affected_bds.values())
                
                min_bounds_x = min(min_bounds_x, ab_min_bounds_x)
                min_bounds_y = min(min_bounds_y, ab_min_bounds_y)
                max_bounds_right = max(max_bounds_right, ab_max_bounds_right)
                max_bounds_bottom = max(max_bounds_bottom, ab_max_bounds_bottom)
            
            is_omni_scale = (axis_w and 0.0 < px < 1.0) or (axis_h and 0.0 < py < 1.0) or (axis_w and axis_h)
            
            if is_omni_scale:
                forward_pad = max(
                    BULLDOZER_CONFIG.get('UNIFORM_SCALE_MIN_PAD', 500), 
                    abs(delta) * BULLDOZER_CONFIG['SIM_FORWARD_MULTIPLIER'] + BULLDOZER_CONFIG['SIM_FORWARD_BASE']
                )
            else:
                forward_pad = max(
                    BULLDOZER_CONFIG['SIM_FORWARD_MIN'], 
                    abs(delta) * BULLDOZER_CONFIG['SIM_FORWARD_MULTIPLIER'] + BULLDOZER_CONFIG['SIM_FORWARD_BASE']
                )

            lateral_pad = BULLDOZER_CONFIG['SIM_SIDE_PAD']
            
            if axis_w:
                if px < 1.0: 
                    max_bounds_right += forward_pad
                if px > 0.0: 
                    min_bounds_x -= forward_pad
                min_bounds_y -= lateral_pad
                max_bounds_bottom += lateral_pad
                
            if axis_h:
                if py < 1.0: 
                    max_bounds_bottom += forward_pad
                if py > 0.0: 
                    min_bounds_y -= forward_pad
                min_bounds_x -= lateral_pad
                max_bounds_right += lateral_pad
                
            safe_nodes = set(selection)
            for backdrop in affected_bds.keys():
                safe_nodes.add(backdrop)
                
            bulldozer_physics_engine(
                merged_colliders, 
                affected_bds, 
                safe_nodes, 
                min_bounds_x, 
                min_bounds_y, 
                max_bounds_right, 
                max_bounds_bottom, 
                mode_direction=None, 
                axis_w=axis_w, 
                axis_h=axis_h, 
                px_abs=px_abs, 
                py_abs=py_abs, 
                interpolation_map=interpolation_map
            )

        for backdrop in sorted_backdrops:
            data = affected_bds[backdrop]
            contained_content = data['nodes']
            
            new_min_x = min(node.xpos() for node in contained_content)
            new_min_y = min(node.ypos() for node in contained_content)
            new_max_x = max(node.xpos() + _get_node_width(node) for node in contained_content)
            new_max_y = max(node.ypos() + _get_node_height(node) for node in contained_content)
            
            proposed_x = new_min_x - data['pad_l']
            proposed_y = new_min_y - data['pad_t']
            proposed_right = new_max_x + data['pad_r']
            proposed_bottom = new_max_y + data['pad_b']
            
            backdrop.setXYpos(proposed_x, proposed_y)
            backdrop.knob('bdwidth').setValue(max(20.0, proposed_right - proposed_x))
            backdrop.knob('bdheight').setValue(max(20.0, proposed_bottom - proposed_y))

    finally:
        nuke.Undo().end()


# ===============================================================================
#                            ---- Smart Move ----
# ===============================================================================

def move_nodes_advanced(direction, use_physics=True):
    """
    Moves selected nodes and automatically resizes any parent backdrops
    If "use_physics" is False, bypasses bulldozer engine and uses fast move logic
    """
    # --- [ Sort selection to ensure consistent logic loops ] ---
    selected_nodes = sorted(nuke.selectedNodes(), key=lambda n: n.name())
    if not selected_nodes:
        return

    # --- [ Fast Move - Leapfrog Mode ] ---
    if not use_physics:
        try:
            nuke.Undo().begin('Move Nodes (Fast)')

            # --- [ Single Node Logic - Leapfrog ] ---
            if len(selected_nodes) == 1:
                node = selected_nodes[0]
                
                # --- [ Do not leapfrog Backdrops or StickyNotes ] ---
                if node.Class() not in ('BackdropNode', 'StickyNote'):
                    if direction == 'up':
                        input_node = node.input(0)
                        if input_node:
                            # --- [ Abort if the target node has no input (Read, Constant, ect...) ] ---
                            if input_node.inputs() == 0:
                                return
                                
                            node_center_x = node.xpos() + node.screenWidth() / 2.0
                            node_center_y = node.ypos() + node.screenHeight() / 2.0
                            
                            input_center_x = input_node.xpos() + input_node.screenWidth() / 2.0
                            input_center_y = input_node.ypos() + input_node.screenHeight() / 2.0
                            
                            input_parent = input_node.input(0)
                            node_outputs = _get_outputs_fast(node)
                            
                            node.setInput(0, input_parent)
                            input_node.setInput(0, node)
                            
                            for out in node_outputs:
                                for i in range(out.inputs()):
                                    if out.input(i) == node:
                                        out.setInput(i, input_node)
                                        
                            node.setXYpos(
                                int(round(input_center_x - node.screenWidth() / 2.0)), 
                                int(round(input_center_y - node.screenHeight() / 2.0))
                            )                            
                            input_node.setXYpos(
                                int(round(node_center_x - input_node.screenWidth() / 2.0)), 
                                int(round(node_center_y - input_node.screenHeight() / 2.0))
                            )
                            return
                            
                    elif direction == 'down':
                        # --- [ Abort if the target node has no input (Read, Constant, ect...) ] ---
                        if node.inputs() == 0:
                            return
                            
                        outputs = _get_outputs_fast(node)
                        if outputs:
                            output_node = outputs[0]
                            
                            node_center_x = node.xpos() + node.screenWidth() / 2.0
                            node_center_y = node.ypos() + node.screenHeight() / 2.0
                            
                            output_center_x = output_node.xpos() + output_node.screenWidth() / 2.0
                            output_center_y = output_node.ypos() + output_node.screenHeight() / 2.0
                            
                            node_parent = node.input(0)
                            output_outputs = _get_outputs_fast(output_node)
                            
                            out_input_idx = 0
                            for i in range(output_node.inputs()):
                                if output_node.input(i) == node:
                                    out_input_idx = i
                                    break
                                    
                            output_node.setInput(out_input_idx, node_parent)
                            node.setInput(0, output_node)
                            
                            for out in output_outputs:
                                for i in range(out.inputs()):
                                    if out.input(i) == output_node:
                                        out.setInput(i, node)
                                        
                            node.setXYpos(
                                int(round(output_center_x - node.screenWidth() / 2.0)), 
                                int(round(output_center_y - node.screenHeight() / 2.0))
                            )                            
                            output_node.setXYpos(
                                int(round(node_center_x - output_node.screenWidth() / 2.0)), 
                                int(round(node_center_y - output_node.screenHeight() / 2.0))
                            )
                            return

            # --- [ Zoom Relative Move ] ---
            base_multiplier = float(BULLDOZER_CONFIG.get('ZOOM_MULTIPLIER', 10))
            if BULLDOZER_CONFIG.get('USE_ZOOM', True):
                zoom_level = nuke.zoom()
                if zoom_level <= 0: 
                    zoom_level = 1.0 
                base_delta = int(base_multiplier / zoom_level)
            else:
                base_delta = int(base_multiplier)
            
            base_delta = max(1, base_delta) 

            delta_x, delta_y = 0, 0
            
            if direction == 'up': 
                delta_y = -base_delta
            elif direction == 'down': 
                delta_y = base_delta
            elif direction == 'left': 
                delta_x = -base_delta
            elif direction == 'right': 
                delta_x = base_delta

            for node in selected_nodes:
                node.setXYpos(node.xpos() + delta_x, node.ypos() + delta_y)

        finally:
            nuke.Undo().end()
        return

    # --- [ BULLDOZER PHYSICS MODE ENGAGE ] ---
    # --- Pre fetch node graph data to avoid looping bottlenecks downstream
    all_nodes = nuke.allNodes()
    all_bds_eval = [b for b in nuke.allNodes('BackdropNode') if not b.name().startswith('NGB_DEBUG_')]
    
    # --- [ Find potential parent backdrops before building the slow containment cache ] ---
    all_backdrops = [node for node in all_bds_eval if node not in selected_nodes]
    bds_to_check = set()
    
    for node in selected_nodes:
        node_x = node.xpos() + _get_node_width(node) / 2.0
        node_y = node.ypos() + _get_node_height(node) / 2.0
        
        for backdrop in all_backdrops:
            backdrop_x = backdrop.xpos()
            backdrop_y = backdrop.ypos()
            backdrop_width = backdrop.knob('bdwidth').value()
            backdrop_height = backdrop.knob('bdheight').value()
            
            if backdrop_x < node_x < backdrop_x + backdrop_width and backdrop_y < node_y < backdrop_y + backdrop_height:
                bds_to_check.add(backdrop)
                
    # --- [ Build fast backdrop containment cache for relevant backdrops ] ---
    master_bd_list = list(bds_to_check.union([b for b in selected_nodes if b.Class() == 'BackdropNode']))
    master_bd_map = _get_nodes_in_backdrops(master_bd_list)
    
    base_multiplier = float(BULLDOZER_CONFIG.get('ZOOM_MULTIPLIER', 10))
    if BULLDOZER_CONFIG.get('USE_ZOOM', True):
        zoom_level = nuke.zoom()
        if zoom_level <= 0: 
            zoom_level = 1.0 
        delta = max(1, int(base_multiplier / zoom_level))
    else:
        delta = max(1, int(base_multiplier))
    
    delta_x, delta_y = 0, 0
    if direction == 'up': 
        delta_y = -delta
    elif direction == 'down': 
        delta_y = delta
    elif direction == 'left': 
        delta_x = -delta
    elif direction == 'right': 
        delta_x = delta
    
    fwd_multiplier = BULLDOZER_CONFIG['SIM_FORWARD_MULTIPLIER']
    fwd_base = BULLDOZER_CONFIG['SIM_FORWARD_BASE']
    fwd_min = BULLDOZER_CONFIG['SIM_FORWARD_MIN']
    SIM_FORWARD_PAD = max(fwd_min, abs(delta_x) * fwd_multiplier + fwd_base, abs(delta_y) * fwd_multiplier + fwd_base)
    SIM_SIDE_PAD = BULLDOZER_CONFIG['SIM_SIDE_PAD']
    SIM_BACK_PAD = BULLDOZER_CONFIG['SIM_BACK_PAD']
    
    affected_bds = {}
    for backdrop in bds_to_check:
        contained_content = master_bd_map.get(backdrop, set())
                
        if any(node in selected_nodes for node in contained_content):
            if not contained_content:
                continue
                
            min_x = min(node.xpos() for node in contained_content)
            min_y = min(node.ypos() for node in contained_content)
            max_x = max(node.xpos() + _get_node_width(node) for node in contained_content)
            max_y = max(node.ypos() + _get_node_height(node) for node in contained_content)
            
            pad_left = min_x - backdrop.xpos()
            pad_top = min_y - backdrop.ypos()
            pad_right = (backdrop.xpos() + backdrop.knob('bdwidth').value()) - max_x
            pad_bottom = (backdrop.ypos() + backdrop.knob('bdheight').value()) - max_y
            
            affected_bds[backdrop] = {
                'pad_l': pad_left, 
                'pad_t': pad_top, 
                'pad_r': pad_right, 
                'pad_b': pad_bottom, 
                'nodes': contained_content,
                'orig_x': backdrop.xpos(), 
                'orig_y': backdrop.ypos(),
                'orig_r': backdrop.xpos() + backdrop.knob('bdwidth').value(),
                'orig_b': backdrop.ypos() + backdrop.knob('bdheight').value()
            }

    try:
        nuke.Undo().begin('Move Nodes & Auto-Adjust Backdrops')
        
        for node in selected_nodes:
            node.setXYpos(int(node.xpos() + delta_x), int(node.ypos() + delta_y))
            
        sorted_backdrops = sorted(affected_bds.keys(), key=lambda b: b.knob('bdwidth').value() * b.knob('bdheight').value())
            
        for backdrop in sorted_backdrops:
            data = affected_bds[backdrop]
            contained_content = data['nodes']
            
            new_min_x = min(node.xpos() for node in contained_content)
            new_min_y = min(node.ypos() for node in contained_content)
            new_max_x = max(node.xpos() + _get_node_width(node) for node in contained_content)
            new_max_y = max(node.ypos() + _get_node_height(node) for node in contained_content)
            
            proposed_x = new_min_x - data['pad_l']
            proposed_y = new_min_y - data['pad_t']
            proposed_right = new_max_x + data['pad_r']
            proposed_bottom = new_max_y + data['pad_b']
            
            backdrop.setXYpos(proposed_x, proposed_y)
            backdrop.knob('bdwidth').setValue(max(20.0, proposed_right - proposed_x))
            backdrop.knob('bdheight').setValue(max(20.0, proposed_bottom - proposed_y))

        primary_colliders = []
        
        for node in selected_nodes:
            if node.Class() == 'BackdropNode':
                node_x = node.xpos()
                node_y = node.ypos()
                node_right = node_x + node.knob('bdwidth').value()
                node_bottom = node_y + node.knob('bdheight').value()
                ignore_set = set(node.getNodes())
                pad = BULLDOZER_CONFIG.get('BD_PAD', 100)
            else:
                node_x = node.xpos()
                node_y = node.ypos()
                node_right = node_x + _get_node_width(node)
                node_bottom = node_y + _get_node_height(node)
                ignore_set = set()
                pad = BULLDOZER_CONFIG.get('NODE_PAD', 10)
                
            start_x = node_x - delta_x
            start_y = node_y - delta_y
            start_right = node_right - delta_x
            start_bottom = node_bottom - delta_y
            
            primary_colliders.append({
                'node': node, 
                'start_x': start_x, 
                'start_y': start_y, 
                'start_right': start_right, 
                'start_bottom': start_bottom, 
                'end_x': node_x, 
                'end_y': node_y, 
                'end_right': node_right, 
                'end_bottom': node_bottom, 
                'padding': pad, 
                'ignore_set': ignore_set, 
                'is_selected': True
            })

        if primary_colliders:
            safe_nodes = set(selected_nodes)
            for backdrop in affected_bds.keys():
                safe_nodes.add(backdrop)

            # --- [ Merge Colliders if "TREAT_AS_ONE is True ] ---
            merged_colliders, interpolation_map = _merge_primary_colliders(primary_colliders, selected_nodes, all_nodes, master_bd_map)

            selection_min_bounds_x = min(min(collider['start_x'], collider['end_x']) for collider in merged_colliders if collider['is_selected'])
            selection_min_bounds_y = min(min(collider['start_y'], collider['end_y']) for collider in merged_colliders if collider['is_selected'])
            selection_max_bounds_right = max(max(collider['start_right'], collider['end_right']) for collider in merged_colliders if collider['is_selected'])
            selection_max_bounds_bottom = max(max(collider['start_bottom'], collider['end_bottom']) for collider in merged_colliders if collider['is_selected'])

            min_bounds_x = selection_min_bounds_x
            min_bounds_y = selection_min_bounds_y
            max_bounds_right = selection_max_bounds_right
            max_bounds_bottom = selection_max_bounds_bottom

            internal_nodes = set()
            for data in affected_bds.values():
                internal_nodes.update(data['nodes'])
            internal_nodes.difference_update(selected_nodes)
            
            cascade_min_x = selection_min_bounds_x
            cascade_min_y = selection_min_bounds_y
            cascade_max_x = selection_max_bounds_right
            cascade_max_y = selection_max_bounds_bottom
            
            if direction == 'right': 
                cascade_max_x += delta_x
            elif direction == 'left': 
                cascade_min_x += delta_x
            elif direction == 'down': 
                cascade_max_y += delta_y
            elif direction == 'up': 
                cascade_min_y += delta_y
            
            added = True
            
            while added:
                added = False
                to_remove = []
                for node in internal_nodes:
                    current_x = node.xpos()
                    current_y = node.ypos()
                    current_right = current_x + _get_node_width(node)
                    current_bottom = current_y + _get_node_height(node)
                    
                    # --- Use maximum potential padding value (BD_PAD vs NODE_PAD) in cascade check
                    max_padding = max(BULLDOZER_CONFIG.get('BD_PAD', 100), BULLDOZER_CONFIG.get('NODE_PAD', 10))                    
                    overlap = False
                    
                    if direction == 'right':
                        if (current_x < cascade_max_x + max_padding and 
                            current_right > cascade_min_x and 
                            current_y < cascade_max_y + SIM_SIDE_PAD and 
                            current_bottom > cascade_min_y - SIM_SIDE_PAD):
                            overlap = True
                    elif direction == 'left':
                        if (current_right > cascade_min_x - max_padding and 
                            current_x < cascade_max_x and 
                            current_y < cascade_max_y + SIM_SIDE_PAD and 
                            current_bottom > cascade_min_y - SIM_SIDE_PAD):
                            overlap = True
                    elif direction == 'down':
                        if (current_y < cascade_max_y + max_padding and 
                            current_bottom > cascade_min_y and 
                            current_x < cascade_max_x + SIM_SIDE_PAD and 
                            current_right > cascade_min_x - SIM_SIDE_PAD):
                            overlap = True
                    elif direction == 'up':
                        if (current_bottom > cascade_min_y - max_padding and 
                            current_y < cascade_max_y and 
                            current_x < cascade_max_x + SIM_SIDE_PAD and 
                            current_right > cascade_min_x - SIM_SIDE_PAD):
                            overlap = True
                        
                    if overlap:
                        if direction == 'right': 
                            cascade_max_x = max(cascade_max_x, current_right + delta_x)
                        elif direction == 'left': 
                            cascade_min_x = min(cascade_min_x, current_x + delta_x)
                        elif direction == 'down': 
                            cascade_max_y = max(cascade_max_y, current_bottom + delta_y)
                        elif direction == 'up': 
                            cascade_min_y = min(cascade_min_y, current_y + delta_y)
                        
                        cascade_min_y = min(cascade_min_y, current_y)
                        cascade_max_y = max(cascade_max_y, current_bottom)
                        cascade_min_x = min(cascade_min_x, current_x)
                        cascade_max_x = max(cascade_max_x, current_right)
                        
                        to_remove.append(node)
                        added = True
                        
                for node in to_remove:
                    internal_nodes.remove(node)

            TOLERANCE = 1.0
            for backdrop, data in affected_bds.items():
                orig = data
                if direction == 'right':
                    if cascade_max_x > (orig['orig_r'] - orig['pad_r']) + TOLERANCE:
                        max_bounds_right = max(max_bounds_right, cascade_max_x + orig['pad_r'])
                        min_bounds_y = min(min_bounds_y, orig['orig_y'])
                        max_bounds_bottom = max(max_bounds_bottom, orig['orig_b'])
                elif direction == 'left':
                    if cascade_min_x < (orig['orig_x'] + orig['pad_l']) - TOLERANCE:
                        min_bounds_x = min(min_bounds_x, cascade_min_x - orig['pad_l'])
                        min_bounds_y = min(min_bounds_y, orig['orig_y'])
                        max_bounds_bottom = max(max_bounds_bottom, orig['orig_b'])
                elif direction == 'down':
                    if cascade_max_y > (orig['orig_b'] - orig['pad_b']) + TOLERANCE:
                        max_bounds_bottom = max(max_bounds_bottom, cascade_max_y + orig['pad_b'])
                        min_bounds_x = min(min_bounds_x, orig['orig_x'])
                        max_bounds_right = max(max_bounds_right, orig['orig_r'])
                elif direction == 'up':
                    if cascade_min_y < (orig['orig_y'] + orig['pad_t']) - TOLERANCE:
                        min_bounds_y = min(min_bounds_y, cascade_min_y - orig['pad_t'])
                        min_bounds_x = min(min_bounds_x, orig['orig_x'])
                        max_bounds_right = max(max_bounds_right, orig['orig_r'])

            if direction == 'right':
                min_bounds_x = selection_min_bounds_x - SIM_BACK_PAD
                max_bounds_right += SIM_FORWARD_PAD
                min_bounds_y -= SIM_SIDE_PAD
                max_bounds_bottom += SIM_SIDE_PAD
            elif direction == 'left':
                min_bounds_x -= SIM_FORWARD_PAD
                max_bounds_right = selection_max_bounds_right + SIM_BACK_PAD
                min_bounds_y -= SIM_SIDE_PAD
                max_bounds_bottom += SIM_SIDE_PAD
            elif direction == 'down':
                min_bounds_y = selection_min_bounds_y - SIM_BACK_PAD
                max_bounds_bottom += SIM_FORWARD_PAD
                min_bounds_x -= SIM_SIDE_PAD
                max_bounds_right += SIM_SIDE_PAD
            elif direction == 'up':
                min_bounds_y -= SIM_FORWARD_PAD
                max_bounds_bottom = selection_max_bounds_bottom + SIM_BACK_PAD
                min_bounds_x -= SIM_SIDE_PAD
                max_bounds_right += SIM_SIDE_PAD
                
            bulldozer_physics_engine(
                merged_colliders, 
                affected_bds, 
                safe_nodes, 
                min_bounds_x, 
                min_bounds_y, 
                max_bounds_right, 
                max_bounds_bottom, 
                mode_direction=direction, 
                interpolation_map=interpolation_map
            )
            
        for backdrop in sorted_backdrops:
            data = affected_bds[backdrop]
            contained_content = data['nodes']
            
            new_min_x = min(node.xpos() for node in contained_content)
            new_min_y = min(node.ypos() for node in contained_content)
            new_max_x = max(node.xpos() + _get_node_width(node) for node in contained_content)
            new_max_y = max(node.ypos() + _get_node_height(node) for node in contained_content)
            
            proposed_x = new_min_x - data['pad_l']
            proposed_y = new_min_y - data['pad_t']
            proposed_right = new_max_x + data['pad_r']
            proposed_bottom = new_max_y + data['pad_b']
            
            backdrop.setXYpos(proposed_x, proposed_y)
            backdrop.knob('bdwidth').setValue(max(20.0, proposed_right - proposed_x))
            backdrop.knob('bdheight').setValue(max(20.0, proposed_bottom - proposed_y))
            
    finally:
        nuke.Undo().end()
        
        
#===============================================================================
#                          ---- Jump ----
#===============================================================================

# --- [ Global Variable to Store The Last Node Jumped From ] ---
JUMP_HISTORY = {"previous_node_name": None}

def jump_to_input():
    """Jumps view to the primary input of the selected node"""
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
        
    current_node = selected_nodes[0]
    input_node = current_node.input(0)
    
    if input_node:
        # --- [ Saves current node to history before jumping away  ] ---
        JUMP_HISTORY["previous_node_name"] = current_node.fullName()
        
        for node in selected_nodes:
            node.setSelected(False)
        input_node.setSelected(True)
        
        center_x = input_node.xpos() + input_node.screenWidth() / 2
        center_y = input_node.ypos() + input_node.screenHeight() / 2
        
        current_zoom = nuke.zoom() 
        nuke.zoom(current_zoom, [center_x, center_y])

def jump_to_output():
    """
    For speed this uses proximity to find connected nodes instead of dependency scan
    """
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
        
    current_node = selected_nodes[0]
    output_node = None
    
    # --- [ HISTORY CHECK (Fastest) ] ---
    # --- If just jumped from a valid output, go back to it 
    prev_name = JUMP_HISTORY.get("previous_node_name")
    if prev_name:
        prev_node = nuke.toNode(prev_name)
        if prev_node and prev_node.Class() != "Viewer":
            for i in range(prev_node.inputs()):
                if prev_node.input(i) == current_node:
                    output_node = prev_node
                    break
                    
    # --- [ PROXIMITY SEARCH (Fallback) ] ---
    # --- In large files checking dependency can take a few seconds, so this is the work around
    # --- It's faster to check if any nodes around it are connected to the current node via inputs
    # --- One downside is that it won't find things outside of the search_padding, so adjust that accodingly 
    if not output_node:
        search_padding = 10000 
        left = current_node.xpos() - search_padding
        top = current_node.ypos() - search_padding
        right = current_node.xpos() + search_padding
        bottom = current_node.ypos() + search_padding
        
        nearby_nodes = nuke.allNodes()
        valid_outputs = []
        
        for node in nearby_nodes:
            nx, ny = node.xpos(), node.ypos()
            if left < nx < right and top < ny < bottom:
                for i in range(node.inputs()):
                    if node.input(i) == current_node:
                        if node.Class() != "Viewer":
                            valid_outputs.append(node)
                        break
        
        if valid_outputs:
            output_node = valid_outputs[0]

    # --- [ EXECUTE JUMP ] ---
    if output_node:
        JUMP_HISTORY["previous_node_name"] = current_node.fullName()
        
        for node in selected_nodes:
            node.setSelected(False)
        output_node.setSelected(True)
        
        center_x = output_node.xpos() + output_node.screenWidth() / 2
        center_y = output_node.ypos() + output_node.screenHeight() / 2
        
        nuke.zoom(nuke.zoom(), [center_x, center_y])
        
        
#===============================================================================
#                          ---- Stack ----
#===============================================================================

def stack_nodes_vertically(nodes, direction='down'):
    """Stacks nodes vertically"""
    if len(nodes) < 2: return

    if direction == 'up':
        anchor_node = min(nodes, key=lambda n: n.ypos())
        other_nodes = sorted([n for n in nodes if n != anchor_node], key=lambda n: n.ypos())
    else:
        anchor_node = max(nodes, key=lambda n: n.ypos())
        other_nodes = sorted([n for n in nodes if n != anchor_node], key=lambda n: n.ypos(), reverse=True)

    PADDING = 6
    MIN_NODE_HEIGHT = 18
    ref_x_center = anchor_node.xpos() + (_get_node_width(anchor_node) / 2.0)

    if direction == 'up':
        current_y = anchor_node.ypos() + max(_get_node_height(anchor_node), MIN_NODE_HEIGHT) + PADDING
        for node in other_nodes:
            target_x = ref_x_center - (_get_node_width(node) / 2.0)
            node.setXYpos(int(round(target_x)), int(round(current_y)))
            current_y += max(_get_node_height(node), MIN_NODE_HEIGHT) + PADDING
    else:
        current_y = anchor_node.ypos() - PADDING
        for node in other_nodes:
            node_height = max(_get_node_height(node), MIN_NODE_HEIGHT)
            target_y = current_y - node_height
            target_x = ref_x_center - (_get_node_width(node) / 2.0)
            node.setXYpos(int(round(target_x)), int(round(target_y)))
            current_y = target_y - PADDING

def stack_nodes_horizontally(nodes, direction='right'):
    """Stacks nodes horizontally"""
    if len(nodes) < 2: return

    if direction == 'left':
        anchor_node = min(nodes, key=lambda n: n.xpos())
        other_nodes = sorted([n for n in nodes if n != anchor_node], key=lambda n: n.xpos())
    else:
        anchor_node = max(nodes, key=lambda n: n.xpos())
        other_nodes = sorted([n for n in nodes if n != anchor_node], key=lambda n: n.xpos(), reverse=True)

    PADDING = 15
    MIN_NODE_WIDTH = 20
    ref_y_center = anchor_node.ypos() + (_get_node_height(anchor_node) / 2.0)

    if direction == 'left':
        current_x = anchor_node.xpos() + max(_get_node_width(anchor_node), MIN_NODE_WIDTH) + PADDING
        for node in other_nodes:
            target_y = ref_y_center - (_get_node_height(node) / 2.0)
            node.setXYpos(int(round(current_x)), int(round(target_y)))
            current_x += max(_get_node_width(node), MIN_NODE_WIDTH) + PADDING
    else:
        current_x = anchor_node.xpos() - PADDING
        for node in other_nodes:
            node_width = max(_get_node_width(node), MIN_NODE_WIDTH)
            target_x = current_x - node_width
            target_y = ref_y_center - (_get_node_height(node) / 2.0)
            node.setXYpos(int(round(target_x)), int(round(target_y)))
            current_x = target_x - PADDING
            

#===============================================================================
#                          ---- Align ----
#===============================================================================

def align_nodes_advanced(align_direction='vertical', stack_direction=None, align_direction_bd='top'):
    """
    Main Logic: Aligns/Stacks if >1 node selected.
    If 1 node selected: Up/Down jumps to input/output, Left/Right changes frame.
    """
    all_selected = nuke.selectedNodes()
    
    # --- [ Single Node or No Node Case ] ---
    if len(all_selected) < 2:
        # --- Check for Jump condition (1 node is selected) 
        if len(all_selected) == 1:
            if align_direction == 'horizontal' and stack_direction == 'up':
                jump_to_input()
                return
            elif align_direction == 'horizontal' and stack_direction == 'down':
                jump_to_output()
                return

        # --- Fallback to Frame Navigation logic  
        v = nuke.activeViewer()
        if align_direction == 'vertical' and stack_direction == 'right':            
            if v != None:
                v.frameControl( 1 )
            else:
                nuke.frame( nuke.frame()+1 )                

        elif align_direction == 'vertical' and stack_direction == 'left':
            if v != None:
                v.frameControl( -1 )
            else:
                nuke.frame( nuke.frame()-1 )
            
        return

    try:
        nuke.Undo().begin('Align/Stack Nodes')

        all_are_backdrops = all(n.Class() == 'BackdropNode' for n in all_selected)

        if all_are_backdrops:
            reference_node = all_selected[0]
            other_nodes = all_selected[1:]

            if align_direction_bd == 'top':
                ref_y = reference_node.ypos()
                is_aligned = all(abs(n.ypos() - ref_y) < 1 for n in all_selected)
                if is_aligned:
                    ref_height = reference_node.knob('bdheight').value()
                    for node in other_nodes:
                        node.knob('bdheight').setValue(ref_height)
                else:
                    for node in other_nodes:
                        node.setYpos(int(round(ref_y)))

            elif align_direction_bd == 'left':
                ref_x = reference_node.xpos()
                is_aligned = all(abs(n.xpos() - ref_x) < 1 for n in all_selected)
                if is_aligned:
                    ref_width = reference_node.knob('bdwidth').value()
                    for node in other_nodes:
                        node.knob('bdwidth').setValue(ref_width)
                else:
                    for node in other_nodes:
                        node.setXpos(int(round(ref_x)))

            elif align_direction_bd == 'bottom':
                ref_bottom_y = reference_node.ypos() + _get_node_height(reference_node)
                is_aligned = all(abs((n.ypos() + _get_node_height(n)) - ref_bottom_y) < 1 for n in all_selected)
                if is_aligned:
                    ref_height = reference_node.knob('bdheight').value()
                    for node in other_nodes:
                        node.knob('bdheight').setValue(ref_height)
                        node.setYpos(int(round(ref_bottom_y - ref_height)))
                else:
                    for node in other_nodes:
                        node_height = _get_node_height(node)
                        node.setYpos(int(round(ref_bottom_y - node_height)))

            elif align_direction_bd == 'right':
                ref_right_x = reference_node.xpos() + _get_node_width(reference_node)
                is_aligned = all(abs((n.xpos() + _get_node_width(n)) - ref_right_x) < 1 for n in all_selected)
                if is_aligned:
                    ref_width = reference_node.knob('bdwidth').value()
                    for node in other_nodes:
                        node.knob('bdwidth').setValue(ref_width)
                        node.setXpos(int(round(ref_right_x - ref_width)))
                else:
                    for node in other_nodes:
                        node_width = _get_node_width(node)
                        node.setXpos(int(round(ref_right_x - node_width)))

            return

        if align_direction == 'horizontal':
            ref_center_x = all_selected[0].xpos() + (_get_node_width(all_selected[0]) / 2.0)
            is_aligned = all(abs((n.xpos() + (_get_node_width(n) / 2.0)) - ref_center_x) < 1 for n in all_selected)

            if is_aligned:
                final_stack_dir = stack_direction if stack_direction in ['up', 'down'] else 'down'
                stack_nodes_vertically(all_selected, direction=final_stack_dir)
                return

        elif align_direction == 'vertical':
            ref_center_y = all_selected[0].ypos() + (_get_node_height(all_selected[0]) / 2.0)
            is_aligned = all(abs((n.ypos() + (_get_node_height(n) / 2.0)) - ref_center_y) < 1 for n in all_selected)

            if is_aligned:
                final_stack_dir = stack_direction if stack_direction in ['left', 'right'] else 'right'
                stack_nodes_horizontally(all_selected, direction=final_stack_dir)
                return

        reference_node = all_selected[0]
        node_to_parent_map = {}
        selected_backdrops = [n for n in all_selected if n.Class() == 'BackdropNode']
        selected_backdrops.sort(key=lambda bd: bd.knob('bdwidth').value() * bd.knob('bdheight').value())
        selected_nodes_set = set(all_selected)

        for bd in selected_backdrops:
            nodes_inside = bd.getNodes()
            for node in nodes_inside:
                if node in selected_nodes_set and node not in node_to_parent_map and node != bd:
                    node_to_parent_map[node] = bd
 
        groups = {}
        for node in all_selected:
            queen_bd = node
            while node_to_parent_map.get(queen_bd):
                queen_bd = node_to_parent_map.get(queen_bd)
            groups.setdefault(queen_bd, []).append(node)

        reference_leader = reference_node
        while node_to_parent_map.get(reference_leader):
            reference_leader = node_to_parent_map.get(reference_leader)

        ref_x_center = reference_leader.xpos() + _get_node_width(reference_leader) / 2.0
        ref_y_center = reference_leader.ypos() + _get_node_height(reference_leader) / 2.0

        for queen_bd, members in groups.items():
            if queen_bd == reference_leader:
                continue

            delta_x, delta_y = 0.0, 0.0

            if align_direction == 'vertical':
                target_x = ref_x_center - (_get_node_width(queen_bd) / 2.0)
                delta_x = target_x - queen_bd.xpos()
            elif align_direction == 'horizontal':
                target_y = ref_y_center - (_get_node_height(queen_bd) / 2.0)
                delta_y = target_y - queen_bd.ypos()

            for node_to_move in members:
                node_to_move.setXYpos(int(round(node_to_move.xpos() + delta_x)), int(round(node_to_move.ypos() + delta_y)))
    finally:
        nuke.Undo().end()
        

