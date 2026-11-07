#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script finds all write nodes in the current file,
                 populates a table with their info, and allows you to mangage them
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
import re
import time
import nukescripts

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

class NumericTableWidgetItem(QtWidgets.QTableWidgetItem):
    """For proper numeric sorting"""
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except (ValueError, TypeError):
            return super(NumericTableWidgetItem, self).__lt__(other)

class WriteOrderPanel(QtWidgets.QWidget):
    """The main Panel UI for Write Node Manager"""
    def __init__(self):
        """Panel Layout"""
        super(WriteOrderPanel, self).__init__()
        self._is_updating = False

        self.main_layout = QtWidgets.QVBoxLayout()
        info_label = QtWidgets.QLabel("Double click a field to edit. Double click Node Name to zoom/edit")
        info_label.setStyleSheet("font-style: italic; color: #999;")

        self.write_nodes_table = QtWidgets.QTableWidget()
        self.write_nodes_table.setColumnCount(11)
        self.write_nodes_table.setHorizontalHeaderLabels(["Disable", "Order", "Node Name", "Label", "File", "Channels", "Colour Space", "File Type", "First", "Last", "Limit to range"])
        
        self.write_nodes_table.setSortingEnabled(False) 
        
        self.write_nodes_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.write_nodes_table.horizontalHeader().setStretchLastSection(True)
        
        self.write_nodes_table.horizontalHeader().setSortIndicator(1, QtCore.Qt.AscendingOrder)
        
        self.write_nodes_table.setAlternatingRowColors(True)
        self.write_nodes_table.setStyleSheet("""QTableView {alternate-background-color: rgb(50, 50, 50);}""")

        self.refresh_button = QtWidgets.QPushButton("Refresh List")

        self.main_layout.addWidget(info_label)
        self.main_layout.addWidget(self.write_nodes_table)
        self.main_layout.addWidget(self.refresh_button)
        self.setLayout(self.main_layout)
        
        self.refresh_button.clicked.connect(self.populate_table)
        self.write_nodes_table.itemChanged.connect(self.on_item_changed)
        self.write_nodes_table.cellChanged.connect(self.on_cell_changed)
        self.write_nodes_table.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.populate_table()

    def populate_table(self):
        """Refreshes the table to keep data up to date"""
        self.write_nodes_table.blockSignals(True)
        self.write_nodes_table.setSortingEnabled(False)
        
        header = self.write_nodes_table.horizontalHeader()
        sort_column = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()

        all_write_nodes = nuke.allNodes('Write')
        node_data_list = []

        for node in all_write_nodes:
            try:
                node_data_list.append({
                    'name': node.name(),
                    'label': node['label'].value(),
                    'file': node['file'].value(),
                    'render_order': int(node['render_order'].value()),
                    'channels': node['channels'].value(),
                    'colorspace': node['colorspace'].value(),
                    'file_type': node['file_type'].value(),
                    'is_disabled': node['disable'].value(),
                    'first': int(node['first'].value()),
                    'last': int(node['last'].value()),
                    'use_limit': node['use_limit'].value()
                })
            except Exception as e:
                print("Write Order Panel: Error processing node '{}', skipping it.".format(node.name()))

        self.write_nodes_table.setRowCount(0)
        self.write_nodes_table.setRowCount(len(node_data_list))

        # --- [ Define conditional row colors ] ---
        disabled_bg_color = QtGui.QColor(30, 30, 30) 
        muted_text_color = QtGui.QColor(128, 128, 128)

        for row_index, node_dict in enumerate(node_data_list):
            disable_check_item = QtWidgets.QTableWidgetItem()
            disable_check_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            disable_check_item.setCheckState(QtCore.Qt.Checked if node_dict['is_disabled'] else QtCore.Qt.Unchecked)
            
            item_order = NumericTableWidgetItem(str(node_dict['render_order']))
            item_name = QtWidgets.QTableWidgetItem(node_dict['name'])
            item_label = QtWidgets.QTableWidgetItem(node_dict['label'])
            item_file = QtWidgets.QTableWidgetItem(node_dict['file'])
            item_channels = QtWidgets.QTableWidgetItem(node_dict['channels'])
            item_colorspace = QtWidgets.QTableWidgetItem(node_dict['colorspace'])
            item_file_type = QtWidgets.QTableWidgetItem(node_dict['file_type'])
            item_first = NumericTableWidgetItem(str(node_dict['first']))
            item_last = NumericTableWidgetItem(str(node_dict['last']))
            
            use_limit_check_item = QtWidgets.QTableWidgetItem()
            use_limit_check_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            use_limit_check_item.setCheckState(QtCore.Qt.Checked if node_dict['use_limit'] else QtCore.Qt.Unchecked)

            item_name.setData(QtCore.Qt.UserRole, node_dict['name'])
            
            # --- [ Styling ] ---
            font = item_name.font()
            is_disabled = node_dict['is_disabled']
            font.setStrikeOut(is_disabled)
            
            all_items_in_row = [disable_check_item, item_order, item_name, item_label, item_file, item_channels, item_colorspace, item_file_type, item_first, item_last, use_limit_check_item]
            
            for item in all_items_in_row:
                item.setFont(font)
                if is_disabled:
                    item.setBackground(disabled_bg_color)
            
            item_channels.setForeground(muted_text_color)
            item_colorspace.setForeground(muted_text_color)
            item_file_type.setForeground(muted_text_color)
            
            # --- [ Conditional Knobs ] ---
            uneditable_flags = item_channels.flags() & ~QtCore.Qt.ItemIsEditable
            item_channels.setFlags(uneditable_flags)
            item_colorspace.setFlags(uneditable_flags)
            item_file_type.setFlags(uneditable_flags)
            
            if not node_dict['use_limit']:
                item_first.setFlags(uneditable_flags)
                item_last.setFlags(uneditable_flags)
                item_first.setForeground(muted_text_color)
                item_last.setForeground(muted_text_color)
            
            # --- [ Place items in table ] ---
            self.write_nodes_table.setItem(row_index, 0, disable_check_item)
            self.write_nodes_table.setItem(row_index, 1, item_order)
            self.write_nodes_table.setItem(row_index, 2, item_name)
            self.write_nodes_table.setItem(row_index, 3, item_label)
            self.write_nodes_table.setItem(row_index, 4, item_file)
            self.write_nodes_table.setItem(row_index, 5, item_channels)
            self.write_nodes_table.setItem(row_index, 6, item_colorspace)
            self.write_nodes_table.setItem(row_index, 7, item_file_type)
            self.write_nodes_table.setItem(row_index, 8, item_first)
            self.write_nodes_table.setItem(row_index, 9, item_last)
            self.write_nodes_table.setItem(row_index, 10, use_limit_check_item)

        self.write_nodes_table.resizeColumnsToContents()
        
        # --- [ Column widths ] ---
        self.write_nodes_table.setColumnWidth(1, 75) # Order
        self.write_nodes_table.setColumnWidth(2, 100) # Node Name
        self.write_nodes_table.setColumnWidth(3, 100) # Label
        self.write_nodes_table.setColumnWidth(4, 500) # File

        self.write_nodes_table.setSortingEnabled(True)
        self.write_nodes_table.sortItems(sort_column, sort_order)
        
        self.write_nodes_table.blockSignals(False)

    def on_item_double_clicked(self, item):
        """Double click logic"""
        if item.column() == 2:
            self.zoom_to_node(item)

    def on_item_changed(self, item):
        """Knob changed"""
        if self._is_updating: return

        column = item.column()
        # --- [ 'disable' checkbox (column 0) ] ---
        if column == 0:
            self._is_updating = True
            row = item.row()
            name_item = self.write_nodes_table.item(row, 2)
            if name_item:
                node = nuke.toNode(name_item.data(QtCore.Qt.UserRole))
                if node:
                    node['disable'].setValue(item.checkState() == QtCore.Qt.Checked)
                    self.populate_table()
            self._is_updating = False
        
        # --- [ 'use_limit' checkbox (column 10)  ] ---
        elif column == 10:
            self._is_updating = True
            row = item.row()
            name_item = self.write_nodes_table.item(row, 2)
            if name_item:
                node = nuke.toNode(name_item.data(QtCore.Qt.UserRole))
                if node:
                    node['use_limit'].setValue(item.checkState() == QtCore.Qt.Checked)
                    self.populate_table()
            self._is_updating = False
            
    def on_cell_changed(self, row, column):
        """Main logic for handling node edits after the user finishes"""
        if self._is_updating: return
        
        if column == 1: self.handle_integer_knob_change(row, column, 'render_order')
        elif column == 2: self.handle_node_name_change(row, column)
        elif column == 3: self.handle_string_knob_change(row, column, 'label')
        elif column == 4: self.handle_string_knob_change(row, column, 'file')
        elif column == 8: self.handle_integer_knob_change(row, column, 'first')
        elif column == 9: self.handle_integer_knob_change(row, column, 'last')

    def handle_integer_knob_change(self, row, column, knob_name):
        """Logic for integer based knobs"""
        self._is_updating = True
        
        item = self.write_nodes_table.item(row, column)
        name_item = self.write_nodes_table.item(row, 2) 
        if not name_item: self._is_updating = False; return
        
        node_name = name_item.data(QtCore.Qt.UserRole)
        new_value_str = item.text()
        
        try:
            new_value = int(new_value_str)
            node = nuke.toNode(node_name)
            if node:
                node[knob_name].setValue(new_value)
        except (ValueError, TypeError):
            node = nuke.toNode(node_name)
            if node:
                original_value = node[knob_name].value()
                item.setText(str(int(original_value)))
            nuke.message("Invalid Input:\n\nValue for '{}' must be a whole number.".format(knob_name))
        finally:
            self._is_updating = False
            self.populate_table()

    def handle_string_knob_change(self, row, column, knob_name):
        """Logic for string based knobs"""
        self._is_updating = True
        
        item = self.write_nodes_table.item(row, column)
        name_item = self.write_nodes_table.item(row, 2) 
        if not name_item: self._is_updating = False; return
        
        node_name = name_item.data(QtCore.Qt.UserRole)
        node = nuke.toNode(node_name)
        if node:
            node[knob_name].setValue(item.text())

        self._is_updating = False
            
    def handle_node_name_change(self, row, column):
        """Logic for changes to the nodes name"""
        self._is_updating = True
        
        name_item = self.write_nodes_table.item(row, column)
        old_node_name = name_item.data(QtCore.Qt.UserRole)
        new_node_name = name_item.text().replace(" ", "_")
        
        if new_node_name != name_item.text():
            name_item.setText(new_node_name)

        node = nuke.toNode(old_node_name)
        if not node: self._is_updating = False; self.populate_table(); return
        
        if not new_node_name:
            nuke.message("Invalid Name:\n\nNode names cannot be empty.")
            name_item.setText(old_node_name)
        elif new_node_name != old_node_name:
            if nuke.toNode(new_node_name):
                nuke.message("Invalid Name:\n\nNode name '{}' is already in use.".format(new_node_name))
                name_item.setText(old_node_name)
            else:
                try:
                    node.setName(new_node_name)
                    name_item.setData(QtCore.Qt.UserRole, new_node_name)
                except RuntimeError as e:
                    nuke.message("Could not rename node.\n\nError: {}".format(e))
                    name_item.setText(old_node_name)
        
        self._is_updating = False

    def zoom_to_node(self, item):
        """Zoom logic"""
        node_name = self.write_nodes_table.item(item.row(), 2).data(QtCore.Qt.UserRole)
        if node_name:
            try:
                target_node = nuke.toNode(node_name)
                nuke.zoom(2, [target_node.xpos(), target_node.ypos()])
                target_node.showControlPanel()
            except ValueError:
                nuke.message("Node '{}' no longer exists.".format(node_name))
                self.populate_table()

# --- [  Global variable to get around Pythons garbage collector ] ---
_write_order_floating_panel = None

def show_floating_panel():
    """Launches Write Order Manager floating panel"""
    global _write_order_floating_panel

    if _write_order_floating_panel:
        _write_order_floating_panel.populate_table()
        _write_order_floating_panel.show()
        _write_order_floating_panel.raise_()
        _write_order_floating_panel.activateWindow()
    else:
        _write_order_floating_panel = WriteOrderPanel()
        _write_order_floating_panel.setWindowTitle("NodeGraphBuddy - Write Node Manager")
        _write_order_floating_panel.setWindowFlags(_write_order_floating_panel.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        _write_order_floating_panel.resize(1300, 400)
        _write_order_floating_panel.show()