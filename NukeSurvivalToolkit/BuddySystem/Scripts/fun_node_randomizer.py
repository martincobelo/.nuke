#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This is a silly script that randomizes selected nodes
                 You can use it to make a mess of your immaculate comps
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
import nukescripts
import random
import struct

#===============================================================================
#                       ---- Scripts ----
#===============================================================================

# --- [ Global variable of panel to prevent doubled up instances ] ---
active_panel = None

class RandomizeNodesPanel(nukescripts.PythonPanel):
    """
    The main Panel UI for Node Randomizer
    Allows user to randomize positions, knobs and colours
    """

    # --- [ Set up knobs for Randomizer here. Requires node and knob class ] ---
    KNOB_PRESETS = {
        'Gain': ['blackpoint', 'whitepoint', 'black', 'white', 'multiply', 'add', 'gamma'],
        'Blur': ['size'],
        'ColorCorrect': ['saturation', 'contrast', 'gamma', 'gain', 'offset']
    }

    def __init__(self):
        """Panel Layout"""
        super(RandomizeNodesPanel, self).__init__("Node Randomizer")

        self.original_states = {}
        self.cached_node_names = set()

        self.warning_text = nuke.Text_Knob("warning_text", "<b>&nbsp;Warning!</b>", "This will make a mess. Use undo to revert.")
        self.mode_knob = nuke.Enumeration_Knob("mode", "Mode", ["All", "Split"])
        self.xy_range_knob = nuke.Range_Knob("xy_range", "XY Position")
        self.x_range_knob = nuke.Range_Knob("x_range", "X Position")
        self.y_range_knob = nuke.Range_Knob("y_range", "Y Position")
        self.divider = nuke.Text_Knob("divider", "")
        self.color_seed_knob = nuke.Int_Knob("color_seed", "Colour")
        
        self.knob_rand_divider = nuke.Text_Knob("knob_rand_divider", "")
        self.enable_knob_rand_knob = nuke.Boolean_Knob("enable_knob_rand", "Randomize Knobs")
        self.knob_seed_knob = nuke.Int_Knob("knob_seed", "Seed")
        self.knob_names_knob = nuke.String_Knob("knob_classes", "Knob Classes")
        self.knob_min_knob = nuke.Double_Knob("knob_min", "Min")
        self.knob_max_knob = nuke.Double_Knob("knob_max", "Max")

        self.x_range_knob.setVisible(False)
        self.y_range_knob.setVisible(False)

        self.enable_knob_rand_knob.setTooltip("Enable randomization of other knobs on the selected nodes.")
        self.knob_names_knob.setTooltip("Comma separated list of knob classes to randomize (e.g. 'Color_Knob, Boolean_Knob')")
        
        default_classes = "AColor_Knob, Color_Knob, Double_Knob, WH_Knob, XY_Knob"
        self.knob_names_knob.setValue(default_classes)
        
        self.knob_max_knob.setValue(1.0)
        
        self.xy_range_knob.setRange(0, 1000)
        self.x_range_knob.setRange(0, 1000)
        self.y_range_knob.setRange(0, 1000)
        self.color_seed_knob.setRange(0, 1000)
        self.knob_seed_knob.setRange(0, 1000)
        
        self.addKnob(self.warning_text)
        self.addKnob(self.mode_knob)
        self.addKnob(self.xy_range_knob)
        self.addKnob(self.x_range_knob)
        self.addKnob(self.y_range_knob)
        self.addKnob(self.divider)
        self.addKnob(self.color_seed_knob)
        self.addKnob(self.knob_rand_divider)
        self.addKnob(self.enable_knob_rand_knob)
        self.addKnob(self.knob_seed_knob)
        self.addKnob(self.knob_names_knob)
        self.addKnob(self.knob_min_knob)
        self.addKnob(self.knob_max_knob)
        
        self.knobChanged(None)
            
    def _update_selection_cache(self):
        """Stores nodes state"""
        current_selection_names = {n.name() for n in nuke.selectedNodes()}
        
        if current_selection_names != self.cached_node_names:
            current_knobs_str = self.knob_names_knob.value()
            existing_knobs_set = {k.strip() for k in current_knobs_str.split(',') if k.strip()}
            
            suggested_knobs = set()
            selected_nodes = nuke.selectedNodes()
            for node in selected_nodes:
                node_class = node.Class()
                
                if node_class in self.KNOB_PRESETS:
                    suggested_knobs.update(self.KNOB_PRESETS[node_class])
            
            final_knobs_set = existing_knobs_set.union(suggested_knobs)

            if final_knobs_set:
                preset_string = ", ".join(sorted(list(final_knobs_set)))
                self.knob_names_knob.setValue(preset_string)

            self.original_states = {}
            for node in selected_nodes:
                self.original_states[node.name()] = {
                    'pos': (node.xpos(), node.ypos()),
                    'color': node['tile_color'].value()
                }
            self.cached_node_names = current_selection_names

    def _apply_randomization(self):
        """Updates nodes state"""
        with nuke.Undo("Randomize Properties"):
            self._update_selection_cache()

            mode = self.mode_knob.value()
            color_seed = int(self.color_seed_knob.value())
            knob_rand_seed = int(self.knob_seed_knob.value())
            
            if mode == "All":
                range_val = self.xy_range_knob.value()
                range_x, range_y = range_val, range_val
            else:
                range_x = self.x_range_knob.value()
                range_y = self.y_range_knob.value()

            for i, node_name in enumerate(self.cached_node_names):
                node = nuke.toNode(node_name)
                if not node: continue

                original_x, original_y = self.original_states[node.name()]['pos']
                
                random.seed(i)
                rand_x_direction = random.uniform(-1.0, 1.0)
                rand_y_direction = random.uniform(-1.0, 1.0)
                
                x_offset = range_x * rand_x_direction
                y_offset = range_y * rand_y_direction
                
                node.setXpos(int(original_x + x_offset))
                node.setYpos(int(original_y + y_offset))

                if color_seed != 0:
                    random.seed(color_seed + i)
                    unsigned_color = random.randint(0, 0xFFFFFF) | 0xFF000000
                    signed_color = struct.unpack('i', struct.pack('I', unsigned_color))[0]
                    node['tile_color'].setValue(signed_color)
                else:
                    original_color = self.original_states[node.name()]['color']
                    node['tile_color'].setValue(original_color)

                if self.enable_knob_rand_knob.value():
                    self._randomize_other_knobs(node, i, knob_rand_seed)

    def _randomize_other_knobs(self, node, index, seed):
        """Randomizes knobs based on their knob class"""
        knob_classes_str = self.knob_names_knob.value()
        target_classes = {c.strip() for c in knob_classes_str.split(',') if c.strip()}
        
        if not target_classes: return

        min_val = self.knob_min_knob.value()
        max_val = self.knob_max_knob.value()
        
        if min_val > max_val: min_val, max_val = max_val, min_val
        
        for knob in node.knobs().values():
            if knob.Class() in target_classes:
                random.seed(seed + index + hash(knob.name()))
                
                try:
                    if isinstance(knob, nuke.Boolean_Knob):
                        knob.setValue(random.choice([True, False]))
                    elif isinstance(knob, (nuke.Double_Knob, nuke.Int_Knob, nuke.WH_Knob, nuke.UV_Knob)):
                        rand_val = random.uniform(min_val, max_val)
                        knob.setValue(int(rand_val) if isinstance(knob, nuke.Int_Knob) else rand_val)
                    elif isinstance(knob, nuke.XY_Knob):
                        knob.setValue(random.uniform(min_val, max_val), 0)
                        knob.setValue(random.uniform(min_val, max_val), 1)
                    elif isinstance(knob, (nuke.Color_Knob, nuke.AColor_Knob)):
                        for i in range(knob.arraySize()):
                            knob.setValue(random.uniform(min_val, max_val), i)
                except (TypeError, ValueError):
                    pass


    def knobChanged(self, knob):
        """Updates panel with knob changes"""
        is_rand_enabled = self.enable_knob_rand_knob.value()
        self.knob_seed_knob.setEnabled(is_rand_enabled)
        self.knob_names_knob.setEnabled(is_rand_enabled)
        self.knob_min_knob.setEnabled(is_rand_enabled)
        self.knob_max_knob.setEnabled(is_rand_enabled)
        
        if hasattr(self, 'mode_knob'):
            mode = self.mode_knob.value()
            self.xy_range_knob.setVisible(mode == "All")
            self.x_range_knob.setVisible(mode == "Split")
            self.y_range_knob.setVisible(mode == "Split")
            self._apply_randomization()
    
    def hide(self):
        """Clear the global variable if closed"""
        global active_panel
        active_panel = None


def show_randomize_panel():
    """Launches Node Randomizer in a floating panel"""
    global active_panel
    if active_panel:
        try:
            active_panel.show()
            return
        except RuntimeError:
            active_panel = None

    active_panel = RandomizeNodesPanel()
    return active_panel.show()