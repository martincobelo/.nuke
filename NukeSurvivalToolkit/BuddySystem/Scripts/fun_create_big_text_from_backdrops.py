#==============================================================================
#                ---- About ----
#==============================================================================
"""
    DESCRIPTION: This is a fun script that creates text out of backdrops
                 You can use it to create big text that is easily viewable when zoomed out 
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
    VERSION:     01.02
    PUBLISHED:   2026-05-17
    DOCS:        https://www.hiramgifford.com/buddy-system/node-graph-buddy

"""
#==============================================================================
#                   ---- How To Install ----
#==============================================================================
"""
    Step #0:     See installation instructions for BuddySystem
"""
#===============================================================================
#                       ---- Imports ----
#===============================================================================

import nuke
import nukescripts

#===============================================================================
#                   ---- Times Node Roman Font Dictionary ----
#===============================================================================
"""
Dictionary Format: 'CHAR': [(x, y, width, height)]
Designed around a 500 wide by 700 tall grid
(0, 0) is the top-left corner of the chararcter
Use a 100x100 grid in nuke to make layout with 100x100 backdrops
"""
FONT_DATA = {
    # ---[ ALPHABET ]---
    'A': [(0, 0, 5, 1), (0, 0, 1, 7), (4, 0, 1, 7), (0, 3, 5, 1)],
    'B': [(0, 0, 1, 7), (0, 0, 4, 1), (0, 3, 4, 1), (0, 6, 4, 1), (4, 1, 1, 2), (4, 4, 1, 2)],
    'C': [(0, 0, 5, 1), (0, 6, 5, 1), (0, 0, 1, 7)],
    'D': [(0, 0, 1, 7), (0, 0, 4, 1), (0, 6, 4, 1), (4, 1, 1, 5)],
    'E': [(0, 0, 1, 7), (0, 0, 5, 1), (0, 3, 4, 1), (0, 6, 5, 1)],
    'F': [(0, 0, 1, 7), (0, 0, 5, 1), (0, 3, 4, 1)],
    'G': [(0, 0, 5, 1), (0, 6, 5, 1), (0, 0, 1, 7), (4, 3, 1, 4), (2, 3, 3, 1)],
    'H': [(0, 0, 1, 7), (4, 0, 1, 7), (0, 3, 5, 1)],
    'I': [(0, 0, 5, 1), (0, 6, 5, 1), (2, 0, 1, 7)],
    'J': [(3, 0, 1, 1), (4, 0, 1, 7), (0, 6, 4, 1)],
    'K': [(0, 0, 1, 7), (1, 3, 1, 1), (2, 2, 1, 1), (2, 4, 1, 1), (3, 1, 1, 1), (3, 5, 1, 1), (4, 0, 1, 1), (4, 6, 1, 1)],
    'L': [(0, 0, 1, 7), (0, 6, 5, 1)],
    'M': [(0, 0, 1, 7), (4, 0, 1, 7), (1, 1, 1, 1), (2, 2, 1, 1), (3, 1, 1, 1)],
    'N': [(0, 0, 1, 7), (4, 0, 1, 7), (1, 1, 1, 2), (2, 3, 1, 2), (3, 5, 1, 1)],
    'O': [(0, 0, 5, 1), (0, 6, 5, 1), (0, 0, 1, 7), (4, 0, 1, 7)],
    'P': [(0, 0, 1, 7), (0, 0, 4, 1), (0, 3, 4, 1), (4, 1, 1, 2)],
    'Q': [(0, 0, 5, 1), (0, 6, 5, 1), (0, 0, 1, 7), (4, 0, 1, 7), (2, 4, 1, 1), (3, 5, 1, 1), (4, 6, 1, 1)],
    'R': [(0, 0, 1, 7), (0, 0, 4, 1), (0, 3, 4, 1), (4, 1, 1, 2), (2, 4, 1, 1), (3, 5, 1, 1), (4, 6, 1, 1)],
    'S': [(0, 0, 5, 1), (0, 3, 5, 1), (0, 6, 5, 1), (0, 1, 1, 2), (4, 4, 1, 2)],
    'T': [(0, 0, 5, 1), (2, 0, 1, 7)],
    'U': [(0, 0, 1, 7), (4, 0, 1, 7), (0, 6, 5, 1)],
    'V': [(0, 0, 1, 6), (4, 0, 1, 6), (1, 5, 1, 2), (3, 5, 1, 2), (2, 6, 1, 1)],
    'W': [(0, 0, 1, 7), (4, 0, 1, 7), (1, 5, 1, 1), (2, 4, 1, 1), (3, 5, 1, 1)],
    'X': [(0, 0, 1, 2), (4, 0, 1, 2), (1, 2, 1, 1), (3, 2, 1, 1), (2, 3, 1, 1), (1, 4, 1, 1), (3, 4, 1, 1), (0, 5, 1, 2), (4, 5, 1, 2)],
    'Y': [(0, 0, 1, 3), (4, 0, 1, 3), (1, 3, 3, 1), (2, 4, 1, 3)],
    'Z': [(0, 0, 5, 1), (0, 6, 5, 1), (4, 1, 1, 1), (3, 2, 1, 1), (2, 3, 1, 1), (1, 4, 1, 1), (0, 5, 1, 1)],
    
    # ---[ NUMBERS ]---
    '0': [(0, 0, 5, 1), (0, 6, 5, 1), (0, 0, 1, 7), (4, 0, 1, 7), (2, 3, 1, 1)],
    '1': [(1, 0, 1, 1), (2, 0, 1, 7), (0, 6, 5, 1)],
    '2': [(0, 0, 5, 1), (4, 1, 1, 2), (0, 3, 5, 1), (0, 4, 1, 2), (0, 6, 5, 1)],
    '3': [(0, 0, 5, 1), (0, 3, 5, 1), (0, 6, 5, 1), (4, 0, 1, 7)],
    '4': [(0, 0, 1, 4), (4, 0, 1, 7), (0, 3, 5, 1)],
    '5': [(0, 0, 5, 1), (0, 0, 1, 3), (0, 3, 5, 1), (4, 4, 1, 2), (0, 6, 5, 1)],
    '6': [(0, 0, 5, 1), (0, 0, 1, 7), (0, 3, 5, 1), (0, 6, 5, 1), (4, 4, 1, 2)],
    '7': [(0, 0, 5, 1), (4, 0, 1, 7)],
    '8': [(0, 0, 5, 1), (0, 3, 5, 1), (0, 6, 5, 1), (0, 0, 1, 7), (4, 0, 1, 7)],
    '9': [(0, 0, 5, 1), (0, 3, 5, 1), (0, 6, 5, 1), (0, 1, 1, 2), (4, 0, 1, 7)],
    
    # ---[ SPECIAL CHARACTERS ]---
    ' ': [],
    '!': [(2, 0, 1, 5), (2, 6, 1, 1)],
    '#': [(1, 0, 1, 7), (3, 0, 1, 7), (0, 2, 5, 1), (0, 4, 5, 1)],
    '-': [(0, 3, 5, 1)],
    '_': [(0, 6, 5, 1)],
    '?': [(1, 0, 3, 1), (0, 1, 1, 1), (4, 1, 1, 2), (3, 3, 1, 1), (2, 4, 1, 1), (2, 6, 1, 1)],
    ':': [(2, 2, 1, 1), (2, 5, 1, 1)],
    '.': [(2, 6, 1, 1)],
    ',': [(2, 5, 1, 1), (1, 6, 1, 1)],
    '|': [(2, 0, 1, 7)],
    '`': [(1, 0, 1, 1), (0, 1, 1, 1)],
    '~': [(0, 3, 1, 1), (1, 2, 1, 1), (2, 3, 1, 1), (3, 2, 1, 1)],
    '@': [(0, 1, 1, 5), (1, 0, 3, 1), (4, 1, 1, 3), (1, 6, 4, 1), (2, 4, 2, 1), (2, 3, 1, 1), (3, 2, 1, 1)],
    '$': [(0, 1, 5, 1), (0, 3, 5, 1), (0, 5, 5, 1), (0, 1, 1, 2), (4, 4, 1, 2), (2, 0, 1, 7)],
    '%': [(0, 0, 2, 2), (3, 5, 2, 2), (0, 5, 1, 1), (1, 4, 1, 1), (2, 3, 1, 1), (3, 2, 1, 1), (4, 1, 1, 1)],
    '^': [(2, 0, 1, 1), (1, 1, 1, 1), (3, 1, 1, 1), (0, 2, 1, 1), (4, 2, 1, 1)],
    '&': [(2, 0, 1, 7), (1, 1, 3, 1), (0, 2, 1, 1), (1, 3, 3, 1), (0, 4, 1, 1), (1, 5, 3, 1)],
    '*': [(1, 0, 1, 1), (3, 0, 1, 1), (2, 1, 1, 1), (1, 2, 1, 1), (3, 2, 1, 1)],
    '+': [(2, 1, 1, 5), (0, 3, 5, 1)],
    '=': [(0, 2, 4, 1), (0, 4, 4, 1)],
    '(': [(1, 0, 2, 1), (0, 1, 1, 5), (1, 6, 2, 1)],
    ')': [(2, 0, 2, 1), (4, 1, 1, 5), (2, 6, 2, 1)],
    '[': [(1, 0, 3, 1), (1, 0, 1, 7), (1, 6, 3, 1)],
    ']': [(1, 0, 3, 1), (3, 0, 1, 7), (1, 6, 3, 1)],
    '{': [(3, 0, 1, 1), (2, 1, 1, 2), (1, 3, 1, 1), (2, 4, 1, 2), (3, 6, 1, 1)],
    '}': [(1, 0, 1, 1), (2, 1, 1, 2), (3, 3, 1, 1), (2, 4, 1, 2), (1, 6, 1, 1)],
    '\\': [(0, 0, 1, 2), (1, 2, 1, 1), (2, 3, 1, 1), (3, 4, 1, 1), (4, 5, 1, 2)],
    '/': [(4, 0, 1, 2), (3, 2, 1, 1), (2, 3, 1, 1), (1, 4, 1, 1), (0, 5, 1, 2)],
    ';': [(2, 2, 1, 1), (2, 4, 1, 1), (1, 5, 1, 1)],
    '"': [(1, 0, 1, 2), (3, 0, 1, 2)], 
    "'": [(2, 0, 1, 2)],
    '<': [(3, 1, 1, 1), (2, 2, 1, 1), (1, 3, 1, 1), (2, 4, 1, 1), (3, 5, 1, 1)],
    '>': [(1, 1, 1, 1), (2, 2, 1, 1), (3, 3, 1, 1), (2, 4, 1, 1), (1, 5, 1, 1)],
}

#===============================================================================
#                       ---- Scripts ----
#===============================================================================

# --- [ Global variable of panel to prevent doubled up instances ] ---
active_panel = None

# --- [ Font grid size ] ---
CHAR_GRID_WIDTH = 5
CHAR_GRID_HEIGHT = 7

# --- [ Spacing between characters ] ---
CHAR_SPACING = 2

class CreateBackdropTextPanel(nukescripts.PythonPanel):
    """
    The main Panel UI for Create Big Text
    Allows user to input text and adjust settings
    """
    def __init__(self):
        """Panel Layout"""
        nukescripts.PythonPanel.__init__(self, 'Create BIG Text')
        
        # --- [ Flag for valid characters ] ---
        self._is_valid = True 
        
        self.aboutKnob = nuke.Text_Knob("about_text", "About:", """<p style="color:#A9A9A9;">Creates big, blocky text from Backdrops<br>Text generates in the center of node graph</p>""")
        self.dividerKnob = nuke.Text_Knob("divider", "", "")
        self.textKnob = nuke.String_Knob("text", "Text:", "big_text")
        self.sizeKnob = nuke.Int_Knob("block_size", "Font Size:")
        self.colorKnob = nuke.ColorChip_Knob("color", "Color:")       
        self.warningKnob = nuke.Text_Knob("warning", "Warnings:", "")        
        self.appearanceKnob = nuke.Enumeration_Knob("appearance", "Appearance:", ['Fill', 'Border'])
        self.borderWidthKnob = nuke.Int_Knob("border_width", "Width:")
        self.borderWidthKnob.clearFlag(nuke.STARTLINE)
        self.zOrderKnob = nuke.Int_Knob("z_order", "Z Order:")
        self.generateButton = nuke.PyScript_Knob("generate", "<b>Generate Text</b>")
        self.generateButton.setFlag(nuke.STARTLINE)
        
        self.textKnob.setTooltip("Enter the text you want to generate")
        self.sizeKnob.setTooltip("Set the size for each block of the font")
        self.colorKnob.setTooltip("Pick the color")
        self.warningKnob.setTooltip("Displays a warning if you use unsupported characters")
        self.appearanceKnob.setTooltip("Choose 'Fill' for solid fonts or 'Border' for fonts made of outlines")
        self.borderWidthKnob.setTooltip("Set the width of the border")
        self.zOrderKnob.setTooltip("Set the z order")
        self.generateButton.setTooltip("Click to generate your text as big backdrops in the center of the node graph")
        
        self.sizeKnob.setValue(100)
        self.colorKnob.setValue(4294967295)
        self.borderWidthKnob.setValue(2)
        self.zOrderKnob.setValue(100)
        
        self.addKnob(self.aboutKnob)
        self.addKnob(self.dividerKnob)
        self.addKnob(self.textKnob)
        self.addKnob(self.warningKnob)
        self.addKnob(self.sizeKnob)
        self.addKnob(self.colorKnob)
        self.addKnob(self.appearanceKnob)
        self.addKnob(self.borderWidthKnob)
        self.addKnob(self.zOrderKnob)
        self.addKnob(self.generateButton)
        
        self._validate_input()
        
        self.knobChanged(self.appearanceKnob)

    def _validate_input(self):
        """Checks input text and updates warning knob"""        
        try:
            # --- [ Decodes multi byte utf-8 characters ] ---
            text_to_draw_upper = self.textKnob.value().decode('utf-8').upper()
        except Exception:
            # --- [ Fallback if decoding doesn't work ] ---
            text_to_draw_upper = self.textKnob.value().upper()
            
        valid_keys = FONT_DATA.keys()
        invalid_chars = set()

        for char in text_to_draw_upper:
            if char not in valid_keys:
                invalid_chars.add(char)
        
        if invalid_chars:
            invalid_string = u", ".join(sorted(list(invalid_chars)))            
            warning_message = u"<b><font color='red'>Unsupported character:</font></b> %s" % invalid_string
            self.warningKnob.setValue(warning_message.encode('utf-8'))            
            self._is_valid = False
        else:
            self.warningKnob.setValue("<b><font color='grey'>none</font></b>") 
            self._is_valid = True

    def knobChanged(self, knob):
        """Called when knobs are changed"""
        if knob is self.textKnob:
            self._validate_input()
            
        if knob is self.generateButton:
            self.run_generate_text()
            
        if knob is self.appearanceKnob:
            appearance_value = self.appearanceKnob.value()
            self.borderWidthKnob.setVisible(appearance_value == 'Border')

    def _get_values(self):
        """Retrieves values from panel"""
        return {
            "text": self.textKnob.value(),
            "block_size": self.sizeKnob.value(),
            "color": self.colorKnob.value(),
            "is_valid": self._is_valid,
            "appearance": self.appearanceKnob.value(),
            "border_width": self.borderWidthKnob.value(),
            "z_order": self.zOrderKnob.value()
        }

    def run_generate_text(self):
        """Builds the text using Backdrop nodes"""        
        values = self._get_values()
        text_to_draw = values["text"]

        if not text_to_draw or not values["is_valid"]:
            nuke.message("Create Big Text: Aborted (no text or invalid characters)")
            return

        block_size = values["block_size"]
        color_to_use = values["color"]
        appearance_value = values["appearance"]        
        border_width_value = values["border_width"]
        z_order_value = values["z_order"]
            
        if block_size < 15:
            nuke.message("Font Size must be 15 or greater...\nThis is Create BIG Text after all")
            return
            
        # --- [ Find center of text ] ---           
        center_pos = nuke.center()
        text_to_draw_upper = text_to_draw.upper()
        num_chars = len(text_to_draw_upper)
        unit_width = block_size         

        total_grid_width = (num_chars * (CHAR_GRID_WIDTH + CHAR_SPACING)) - CHAR_SPACING
        
        if total_grid_width < 0:
            total_grid_width = 0
            
        total_pixel_width = total_grid_width * unit_width        
        start_x = center_pos[0] - (total_pixel_width / 2.0)
        current_x = start_x
        current_y = center_pos[1]
        unit_height = block_size
        
        # --- [ Deselect all ] ---
        for n in nuke.selectedNodes():
            n['selected'].setValue(False)
            
        created_nodes = []
        
        # --- [ Main loop to create letters ] ---
        text_to_draw_upper = text_to_draw.upper()
        for char in text_to_draw_upper: 
            
            char_data = FONT_DATA[char]

            if char_data:
                for (x, y, w, h) in char_data:
                    
                    bd = nuke.createNode("BackdropNode", inpanel=False)
                    bd.setName("font_backdrop")
                    
                    xpos = current_x + (x * unit_width)
                    ypos = current_y + (y * unit_height)
                    bd_width = w * unit_width
                    bd_height = h * unit_height
                    
                    bd['xpos'].setValue(xpos)
                    bd['ypos'].setValue(ypos)
                    bd['bdwidth'].setValue(bd_width)
                    bd['bdheight'].setValue(bd_height)                    
                    bd['tile_color'].setValue(color_to_use)
                    bd['z_order'].setValue(z_order_value)
                    bd['note_font_size'].setValue(0)
                    if bd.knob('appearance'):
                        bd['appearance'].setValue(appearance_value)
                    if bd.knob('border_width'):
                        bd['border_width'].setValue(border_width_value)
                    
                    # --- [ For creating new characters. Enable to see coords on backdrops ] ---
                    #coord_text = str((x, y, w, h))          
                    #bd['label'].setValue(coord_text)
                    #bd['note_font_size'].setValue(51)
                    
                    bd['selected'].setValue(False)
                    created_nodes.append(bd)

            current_x += (CHAR_GRID_WIDTH + CHAR_SPACING) * unit_width
            
        # --- [ Select all backrop font nodes ] ---
        if created_nodes:
            for bd in created_nodes:
                bd['selected'].setValue(True)
        else:
            pass

    def hide(self):
        """Clear the global variable if closed"""
        global active_panel
        active_panel = None
        

def show_create_big_text():
    """Launches Create Big Text in a floating panel"""
    global active_panel
    if active_panel:
        try:
            active_panel.show()
            return
        except RuntimeError:
            active_panel = None

    active_panel = CreateBackdropTextPanel()
    return active_panel.show()