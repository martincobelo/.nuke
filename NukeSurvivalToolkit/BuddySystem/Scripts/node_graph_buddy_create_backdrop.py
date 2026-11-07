#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script creates a Blur node for 0-1 selected nodes, or a Backdrop for 2+
                 Backdrop panel can be accessed in advanced mode, includes a preset system
                 Extra padding is put around backdrop compared to default backdrop creation
                 This is meant to be used with the "B" hotkey, and preserve its blur node creation 
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

#===============================================================================
#                       ---- Scripts ----
#===============================================================================
"""
--- [ User-Editable Presets ] ---
Add or modify presets here. The key is the name that will appear in the dropdown
The color is a hexadecimal integer in RGBA format

To get a color value from an existing node:
1. Select the node in the Node Graph with the color you want
2. Run this in Nuke's Script Editor: print(int(nuke.selectedNode().knob('tile_color').value()))
3. Copy the integer that it prints and paste it as the 'color' value for your preset
"""
PRESETS = {
    'Lighting': {'color': 1633107455},
    'Matte Paint':  {'color': 741818623},
    'FX':  {'color': 1142827519},
    'Crowd':  {'color': 5190143},
    'Props':  {'color': 1664232191},
    'Environment':  {'color': 540020991},
    'Atmos':  {'color': 1248882175},
    'Water':  {'color': 624455935},
    'Sky':  {'color': 241333247},
    'Character':  {'color': 1714446847},
    'Roto':     {'color': 1197552127},
    'Plate':    {'color': 1361992191},
    'Key':    {'color': 811679999},
    'Renders':  {'color': 2139062271},
    'Precomp':  {'color': 2995271167},
    'Output':   {'color': 2996315135}
}


# --- [ Custom Backdrop Panel ] ---
class CreateBackdropPanel(nukescripts.PythonPanel):
    """
    Allows you to modify backdrop before creation
    Presets, labels and knob values can be applied
    """
    def __init__(self):
        nukescripts.PythonPanel.__init__(self, 'Create Backdrop')
        
        preset_names = ['None'] + sorted(PRESETS.keys())

        self.presetsKnob = nuke.Enumeration_Knob('presets', 'Preset', preset_names)
        self.labelKnob = nuke.String_Knob('label', 'Label')
        self.paddingKnob = nuke.Int_Knob('padding', 'Padding')
        self.fontSizeKnob = nuke.Int_Knob('fontSize', 'Font Size')
        self.zOrderKnob = nuke.Int_Knob('zOrder', 'Z Order')
        self.randomColorKnob = nuke.Boolean_Knob('randomColor', 'Random Colour')
        self.colorKnob = nuke.ColorChip_Knob('color', 'Color')
        self.appearanceKnob = nuke.Enumeration_Knob('appearance', 'Appearance', ['Fill', 'Border'])
        self.bookmarkKnob = nuke.Boolean_Knob('bookmark', 'Bookmark')

        self.addKnob(self.labelKnob)
        self.addKnob(self.presetsKnob)        
        self.addKnob(self.paddingKnob)
        self.addKnob(self.fontSizeKnob)
        self.addKnob(self.zOrderKnob)
        self.addKnob(self.randomColorKnob)
        self.addKnob(self.colorKnob)
        self.addKnob(self.appearanceKnob)
        self.addKnob(self.bookmarkKnob)

        for knob in [self.presetsKnob, self.labelKnob, self.paddingKnob, self.fontSizeKnob, self.zOrderKnob, self.randomColorKnob, self.colorKnob, self.appearanceKnob, self.bookmarkKnob]:
            knob.setFlag(nuke.STARTLINE)

        # --- [ Set panel defaults ] ---
        self.presetsKnob.setValue('None')
        self.labelKnob.setValue("")
        self.paddingKnob.setValue(100)
        self.fontSizeKnob.setValue(42)
        self.zOrderKnob.setValue(0)
        self.randomColorKnob.setValue(True) 
        self.colorKnob.setValue(0x888888FF)
        self.appearanceKnob.setValue('Fill')
        self.bookmarkKnob.setValue(False)
        self.knobChanged(self.randomColorKnob)
        
    def knobChanged(self, knob):
        """
        When a knobs value changes in the panel,
        This is used to update the state of the panel
        """
        if knob is self.presetsKnob:
            preset = self.presetsKnob.value()
            if preset == 'None':
                self.labelKnob.setEnabled(True)
                self.randomColorKnob.setEnabled(True)
                self.knobChanged(self.randomColorKnob)
            else:
                preset_data = PRESETS[preset]
                self.labelKnob.setValue(preset)
                
                self.randomColorKnob.setValue(False)
                self.randomColorKnob.setEnabled(False)
                
                self.colorKnob.setValue(preset_data['color'])
                self.colorKnob.setEnabled(False)

        elif knob is self.randomColorKnob:
            if self.presetsKnob.value() == 'None':
                is_random = self.randomColorKnob.value()
                self.colorKnob.setEnabled(not is_random)
                if is_random:
                    r, g, b = (random.randint(40, 100) for _ in range(3))
                    random_color_int = (r << 24) | (g << 16) | (b << 8) | 0xFF
                    self.colorKnob.setValue(random_color_int)


def _calculate_z_order(nodes, padding=100):
    """Calculates the ideal z_order based on context"""
    if not nodes:
        return 0

    new_x_min = min(node.xpos() for node in nodes) - padding
    new_y_min = min(node.ypos() for node in nodes) - padding
    new_x_max = max(node.xpos() + node.screenWidth() for node in nodes) + padding
    new_y_max = max(node.ypos() + node.screenHeight() for node in nodes) + padding

    overlapping_bds = []
    for bd in nuke.allNodes('BackdropNode'):
        bd_x_min, bd_y_min = bd.xpos(), bd.ypos()
        bd_x_max = bd_x_min + bd.knob('bdwidth').value()
        bd_y_max = bd_y_min + bd.knob('bdheight').value()
        
        if (new_x_min < bd_x_max and new_x_max > bd_x_min and
            new_y_min < bd_y_max and new_y_max > bd_y_min):
            overlapping_bds.append(bd)
    
    if not overlapping_bds:
        return 0
    
    contained_bds = []
    other_overlapping_bds = []
    for bd in overlapping_bds:
        bd_x_min, bd_y_min = bd.xpos(), bd.ypos()
        bd_x_max = bd_x_min + bd.knob('bdwidth').value()
        bd_y_max = bd_y_min + bd.knob('bdheight').value()

        if (new_x_min <= bd_x_min and new_y_min <= bd_y_min and
            new_x_max >= bd_x_max and new_y_max >= bd_y_max):
            contained_bds.append(bd)
        else:
            other_overlapping_bds.append(bd)
            
    floor_z = max([bd.knob('z_order').value() for bd in other_overlapping_bds]) if other_overlapping_bds else None
    ceiling_z = min([bd.knob('z_order').value() for bd in contained_bds]) if contained_bds else None

    if ceiling_z is None:
        return (floor_z or -10) + 10
    if floor_z is None:
        return ceiling_z - 10

    if floor_z + 10 < ceiling_z:
        return ceiling_z - 10
    else:
        return (floor_z + ceiling_z) // 2


def _apply_panel_values(nodes):
    """Helper to show the panel and create a BackdropNode"""
    panel = CreateBackdropPanel()
    default_z_order = _calculate_z_order(nodes, panel.paddingKnob.value())
    panel.zOrderKnob.setValue(int(default_z_order))

    if not panel.showModalDialog():
        return

    label = panel.labelKnob.value()
    padding = panel.paddingKnob.value()
    font_size = panel.fontSizeKnob.value()
    z_order = panel.zOrderKnob.value()
    tile_color = panel.colorKnob.value()
    appearance = panel.appearanceKnob.value()
    bookmark = panel.bookmarkKnob.value()

    x_min = min(node.xpos() for node in nodes)
    y_min = min(node.ypos() for node in nodes)
    x_max = max(node.xpos() + node.screenWidth() for node in nodes)
    y_max = max(node.ypos() + node.screenHeight() for node in nodes)

    bd = nuke.createNode('BackdropNode')
    bd.setXpos(x_min - padding)
    bd.setYpos(y_min - padding)
    bd.knob('bdwidth').setValue(x_max - x_min + 2 * padding)
    bd.knob('bdheight').setValue(y_max - y_min + 2 * padding)
    bd.knob('label').setValue(label)
    bd.knob('note_font_size').setValue(font_size)
    bd.knob('z_order').setValue(z_order)
    bd.knob('tile_color').setValue(tile_color)
    bd.knob('appearance').setValue(appearance)
    bd.knob('bookmark').setValue(int(bookmark))

    bd.selectNodes(True)
    bd['selected'].setValue(True)


def _create_backdrop_with_defaults(nodes):
    """Helper to create a backdrop instantly using default values without showing the panel"""
    padding = 100
    font_size = 42
    default_z_order = _calculate_z_order(nodes, padding)
    
    r, g, b = (random.randint(40, 100) for _ in range(3))
    tile_color = (r << 24) | (g << 16) | (b << 8) | 0xFF
    
    x_min = min(node.xpos() for node in nodes)
    y_min = min(node.ypos() for node in nodes)
    x_max = max(node.xpos() + node.screenWidth() for node in nodes)
    y_max = max(node.ypos() + node.screenHeight() for node in nodes)
    
    bd = nuke.createNode('BackdropNode')
    bd.setXpos(x_min - padding)
    bd.setYpos(y_min - padding)
    bd.knob('bdwidth').setValue(x_max - x_min + 2 * padding)
    bd.knob('bdheight').setValue(y_max - y_min + 2 * padding)
    bd.knob('note_font_size').setValue(font_size)
    bd.knob('z_order').setValue(default_z_order)
    bd.knob('tile_color').setValue(tile_color)
    bd.knob('appearance').setValue('Fill')
    bd.knob('bookmark').setValue(False)
    
    bd.selectNodes(True)
    bd['selected'].setValue(True)


def create_backdrop(advanced=False):
    """
    Main logic 
    Creates a Blur or Backdrop node based on node count and hotkey call
    """
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        # --- [ If no nodes selected, create a blur ] ---
        nuke.createNode('Blur')
        return

    if len(selected_nodes) == 1:
        # --- [ If one node selected, create a blur and connect it ] ---
        blur_node = nuke.createNode('Blur')
        blur_node.setInput(0, selected_nodes[0])
    else:
        # --- [ If 2+ nodes selected, create a backdrop ] ---
        if advanced:
            _apply_panel_values(selected_nodes)
        else:
            _create_backdrop_with_defaults(selected_nodes)