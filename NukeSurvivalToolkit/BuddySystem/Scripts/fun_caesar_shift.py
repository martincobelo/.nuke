#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This is a silly script that applies a caesar cipher to the selected nodes label
                 You can use it to send secret messages to your legions 
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
    VERSION:     01.02
    PUBLISHED:   2025-10-19
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
import re

#===============================================================================
#                       ---- Scripts ----
#===============================================================================

# --- [ Global variable of panel to prevent doubled up instances ] ---
active_panel = None

def caesar_shift_string(text, shift):
    """Shift logic"""
    shift = shift % 26
    out = []
    for c in text:
        if 'A' <= c <= 'Z':
            out.append(chr((ord(c) - ord('A') + shift) % 26 + ord('A')))
        elif 'a' <= c <= 'z':
            out.append(chr((ord(c) - ord('a') + shift) % 26 + ord('a')))
        else:
            out.append(c)
    return ''.join(out)

def shift_label_preserving_brackets(text, shift):
    """Helper to avoid HTML and TCL text"""
    pattern = r'(<[^>]*>|\[[^\]]*\])'
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if not part:
            continue
        if (part.startswith('<') and part.endswith('>')) or \
           (part.startswith('[') and part.endswith(']')):
            continue
        parts[i] = caesar_shift_string(part, shift)
    return ''.join(parts)

class CaesarShiftLabelPanel(nukescripts.PythonPanel):
    """
    The main Panel UI for Caesar Shift
    Shows the current and shifted alphabet
    """
    def __init__(self):
        """Panel Layout"""
        nukescripts.PythonPanel.__init__(self, "Caesar Shift Labels")

        self.addKnob(nuke.Text_Knob("howToUse", "How To Use:", "Select nodes to apply encryption"))

        self.shift_knob = nuke.Int_Knob("shift", "Shift Amount")
        self.shift_knob.setRange(-52, 52)
        self.shift_knob.setValue(0)
        self.addKnob(self.shift_knob)

        base = "abcdefghijklmnopqrstuvwxyz"
        spaced = " ".join(base)
        self.addKnob(nuke.Text_Knob("ref_alpha", "Reference Alphabet", spaced))
        self.shifted_alpha = nuke.Text_Knob("shifted_alpha", "Shifted Alphabet", spaced)
        self.addKnob(self.shifted_alpha)

        self.original_labels = {}
        self.last_shift = 0

    def knobChanged(self, knob):
        """Panel and node update logic"""
        if knob is not self.shift_knob:
            return

        selected = nuke.selectedNodes()
        if not selected:
            return

        new_shift = knob.value()

        # --- [ Record original labels for new selections ] ---
        for node in selected:
            lbl = node.knob("label")
            if not lbl:
                continue
            try:
                if node not in self.original_labels:
                    self.original_labels[node] = lbl.value()
            except ValueError:
                continue

        # --- [ Check for manual edits under the old shift ] ---
        for node in selected:
            lbl = node.knob("label")
            if not lbl:
                continue
            try:
                current = lbl.value()
            except ValueError:
                continue
            expected = shift_label_preserving_brackets(
                self.original_labels.get(node, ""),
                self.last_shift
            )
            if current != expected:
                self.original_labels[node] = current

        # --- [ Apply the new shift ] ---
        for node in selected:
            lbl = node.knob("label")
            if not lbl:
                continue
            base_txt = self.original_labels.get(node, "")
            try:
                shifted = shift_label_preserving_brackets(base_txt, new_shift)
                lbl.setValue(shifted)
            except ValueError:
                continue

        # --- [ Update shifted-alphabet display ] ---
        base = "abcdefghijklmnopqrstuvwxyz"
        spaced_shifted = " ".join(caesar_shift_string(base, new_shift))
        self.shifted_alpha.setValue(spaced_shifted)

        self.last_shift = new_shift
        
    def hide(self):
        """Clear the global variable if closed"""
        global active_panel
        active_panel = None
        
    
def show_caesar_shift_label():
    """Launches Caesar Shift in a floating panel"""
    global active_panel
    if active_panel:
        try:
            active_panel.show()
            return
        except RuntimeError:
            active_panel = None

    active_panel = CaesarShiftLabelPanel()
    return active_panel.show()