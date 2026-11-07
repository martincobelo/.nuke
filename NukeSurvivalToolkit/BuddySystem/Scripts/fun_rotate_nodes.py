#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This is a silly script that rotates selected nodes
                 You can use it to comp sideways 
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
import math

# --- [  Import PySide based on nuke version ] --- 
if nuke.NUKE_VERSION_MAJOR < 11:
    from PySide import QtCore, QtGui
    QtWidgets = QtGui
elif nuke.NUKE_VERSION_MAJOR < 16:
    from PySide2 import QtWidgets, QtCore, QtGui
else:
    from PySide6 import QtWidgets, QtCore, QtGui
    
#===============================================================================
#                       ---- Scripts ----
#===============================================================================

# -- [ Global dictionary for storage of original centers and sizes ] ---
_rotation_data = {}

class RotateNodesPanel(QtWidgets.QDialog):
    """
    The main Panel UI for Rotate Nodes
    Allows user to rotate nodes around a collective center point
    """
    def __init__(self, parent=None):
        """Panel Layout"""
        super(RotateNodesPanel, self).__init__(parent)
        self.setWindowTitle("Rotate Nodes")
        self.resize(200, 140)

        self.selected_nodes = nuke.selectedNodes()

        self._collect_originals()
        self._compute_centroid()

        angle_layout = QtWidgets.QHBoxLayout()
        angle_layout.setAlignment(QtCore.Qt.AlignLeft)
        angle_label = QtWidgets.QLabel("Angle:")
        self.degree_input = QtWidgets.QLineEdit("0")
        self.degree_input.setFixedWidth(50)
        validator = QtGui.QIntValidator(0, 360)
        self.degree_input.setValidator(validator)
        self.degree_input.editingFinished.connect(self.on_input_changed)
        angle_layout.addWidget(angle_label)
        angle_layout.addWidget(self.degree_input)
 
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, 360)
        self.slider.setValue(0)
        self.slider.setTickInterval(10)
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slider.valueChanged.connect(self.on_slider_changed)

        self.ignore_backdrops = QtWidgets.QCheckBox("Ignore Backdrops")
        self.ignore_backdrops.setChecked(False)
        self.ignore_stickynotes = QtWidgets.QCheckBox("Ignore StickyNotes")
        self.ignore_stickynotes.setChecked(False)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(angle_layout)
        main_layout.addWidget(self.slider)
        main_layout.addWidget(self.ignore_backdrops)
        main_layout.addWidget(self.ignore_stickynotes)
        self.setLayout(main_layout)

    def _collect_originals(self):
        """Stores original positions"""
        global _rotation_data
        _rotation_data.clear()
        for node in self.selected_nodes:
            key = node.fullName()
            w = node.screenWidth()
            h = node.screenHeight()
            orig_x = node.xpos()
            orig_y = node.ypos()
            orig_cx = orig_x + (w / 2.0)
            orig_cy = orig_y + (h / 2.0)
            _rotation_data[key] = {
                'node': node,
                'orig_cx': orig_cx,
                'orig_cy': orig_cy,
                'w': w,
                'h': h
            }

    def _compute_centroid(self):
        """Finds center of selection"""
        coords_x = []
        coords_y = []
        for data in _rotation_data.values():
            coords_x.append(data['orig_cx'])
            coords_y.append(data['orig_cy'])
        self.group_cx = sum(coords_x) / float(len(coords_x))
        self.group_cy = sum(coords_y) / float(len(coords_y))

    def on_slider_changed(self, value):
        """Updates panel"""
        angle = int(value)
        self.degree_input.setText(str(angle))
        self._apply_rotation(angle)

    def on_input_changed(self):
        """Updates panel"""
        text = self.degree_input.text()
        try:
            val = int(text)
        except ValueError:
            return
        if 0 <= val <= 360:
            self.slider.setValue(val)
        else:
            self.degree_input.setText(str(self.slider.value()))

    def _apply_rotation(self, angle_deg):
        """Rotation Logic"""
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        ignore_bd = self.ignore_backdrops.isChecked()
        ignore_sn = self.ignore_stickynotes.isChecked()

        for data in _rotation_data.values():
            node = data['node']

            if ignore_bd and node.Class() == 'BackdropNode':
                continue

            if ignore_sn and node.Class() == 'StickyNote':
                continue
            ox_c = data['orig_cx']
            oy_c = data['orig_cy']
            dx = ox_c - self.group_cx
            dy = oy_c - self.group_cy

            new_dx = dx * cos_a - dy * sin_a
            new_dy = dx * sin_a + dy * cos_a
            new_cx = self.group_cx + new_dx
            new_cy = self.group_cy + new_dy

            new_x = int(round(new_cx - (data['w'] / 2.0)))
            new_y = int(round(new_cy - (data['h'] / 2.0)))
            node.setXpos(new_x)
            node.setYpos(new_y)


def rotate_nodes():
    """Launches Rotate Nodes in a floating panel"""
    if not nuke.selectedNodes():
        nuke.message("No nodes selected. Please select at least two nodes.")
        return
    dialog = RotateNodesPanel()
    if dialog:
        dialog.exec_()