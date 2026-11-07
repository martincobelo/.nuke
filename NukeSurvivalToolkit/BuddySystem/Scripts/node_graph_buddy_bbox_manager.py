#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script finds and sorts all bounding box info, for every root level node.
                 Then populates a table with their info, and allows you to manage them
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
    VERSION:     01.02
    PUBLISHED:   2025-09-21
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

#===============================================================================
#                ---- Scripts ----
#===============================================================================

class NumericTableWidgetItem(QtWidgets.QTableWidgetItem):
    """For proper numeric sorting"""
    def __lt__(self, other):
        self_value = self.data(QtCore.Qt.UserRole) or 0
        other_value = other.data(QtCore.Qt.UserRole) or 0
        return self_value < other_value


class BoundingBoxInfoPanel(QtWidgets.QWidget):
    """The main Panel UI for Bounding Box Manger"""
    def __init__(self):
        """Panel Layout"""
        super(BoundingBoxInfoPanel, self).__init__()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.is_refreshing = False
        self._last_valid_format = ""
        self._last_valid_min_bbox = "100x100"

        # --- [ Hardcoded list of classes to always ignore ] ---
        self.hardcoded_ignore_classes = {'BackdropNode', 'StickyNote', 'Dot', 'Viewer', 'NoOp'}

        # --- [ Main Controls Layout ] ---
        controls_layout = QtWidgets.QHBoxLayout()
        mode_label = QtWidgets.QLabel("Mode:")
        self.mode_combobox = QtWidgets.QComboBox()
        self.mode_combobox.addItems(["Percentage Growth", "Format Comparison"])
        self.mode_combobox.setToolTip("Switch between different bbox analysis modes")

        self.show_all_checkbox = QtWidgets.QCheckBox("Show All Nodes")
        self.show_all_checkbox.setChecked(False)
        self.show_all_checkbox.setToolTip("When unchecked, only shows nodes that meet the criteria of the current mode")

        controls_layout.addWidget(mode_label)
        controls_layout.addWidget(self.mode_combobox)
        controls_layout.addSpacing(25)
        controls_layout.addWidget(self.show_all_checkbox)
        controls_layout.addStretch()

        # --- [ Mode Specific Controls ] ---
        self.format_controls_widget = QtWidgets.QWidget()
        format_layout = QtWidgets.QHBoxLayout(self.format_controls_widget)
        format_layout.setContentsMargins(0, 0, 0, 0)
        format_label = QtWidgets.QLabel("Root Format:")
        self.format_lineEdit = QtWidgets.QLineEdit()
        self.format_lineEdit.setToolTip("Set a custom format to check against")
        self.get_format_button = QtWidgets.QPushButton("Update")
        self.get_format_button.setFixedWidth(55)
        self.get_format_button.setToolTip("Update the format from the project's root settings")
        overscan_label = QtWidgets.QLabel("Overscan:")
        self.overscan_spinbox = QtWidgets.QSpinBox()
        self.overscan_spinbox.setRange(0, 9999)
        self.overscan_spinbox.blockSignals(True)
        self.overscan_spinbox.setValue(100)
        self.overscan_spinbox.blockSignals(False)
        self.overscan_spinbox.setSuffix(" px")
        self.overscan_spinbox.setToolTip("Sets a pixel tolerance around the format")
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_lineEdit)
        format_layout.addWidget(self.get_format_button)
        format_layout.addSpacing(15)
        format_layout.addWidget(overscan_label)
        format_layout.addWidget(self.overscan_spinbox)
        format_layout.addStretch()

        # --- [ Percentage Growth Controls ] ---
        self.percentage_controls_widget = QtWidgets.QWidget()
        percentage_layout = QtWidgets.QHBoxLayout(self.percentage_controls_widget)
        percentage_layout.setContentsMargins(0, 0, 0, 0)
        percentage_label = QtWidgets.QLabel("Growth Threshold:")
        self.percentage_spinbox = QtWidgets.QDoubleSpinBox()
        self.percentage_spinbox.setRange(0.1, 9999.0)
        self.percentage_spinbox.blockSignals(True)
        self.percentage_spinbox.setValue(10.0)
        self.percentage_spinbox.blockSignals(False)
        self.percentage_spinbox.setSuffix(" %")
        self.percentage_spinbox.setToolTip("Show nodes that increase bbox area by at least this percentage")
        min_bbox_label = QtWidgets.QLabel("Min Input BBox:")
        self.min_bbox_lineEdit = QtWidgets.QLineEdit(self._last_valid_min_bbox)
        self.min_bbox_lineEdit.setToolTip("Inputs equal to or less than this format will be ignored during growth calculation")
        percentage_layout.addWidget(percentage_label)
        percentage_layout.addWidget(self.percentage_spinbox)
        percentage_layout.addSpacing(15)
        percentage_layout.addWidget(min_bbox_label)
        percentage_layout.addWidget(self.min_bbox_lineEdit)
        percentage_layout.addStretch()

        # --- [ Ignore Classes Layout ] ---
        ignore_class_layout = QtWidgets.QHBoxLayout()
        ignore_class_label = QtWidgets.QLabel("Ignore Classes:")
        self.ignore_class_lineEdit = QtWidgets.QLineEdit()
        self.ignore_class_lineEdit.setText("")
        self.ignore_class_lineEdit.setToolTip("Add comma separated classes to the ignore list.\nThe following classes are automaticly ignored: BackdropNode, StickyNote, Dot, Viewer, NoOp")
        self.add_class_button = QtWidgets.QPushButton("Add")
        self.add_class_button.setFixedWidth(50)
        self.add_class_button.setToolTip("Add the class of the selected nodes to the ignore list")
        ignore_class_layout.addWidget(ignore_class_label)
        ignore_class_layout.addWidget(self.ignore_class_lineEdit)
        ignore_class_layout.addWidget(self.add_class_button)

        # --- [ Ignore Names Layout ] ---
        ignore_name_layout = QtWidgets.QHBoxLayout()
        ignore_name_label = QtWidgets.QLabel("Ignore Names:")
        self.ignore_name_lineEdit = QtWidgets.QLineEdit()
        self.ignore_name_lineEdit.setToolTip("A comma separated list of specific node names to ignore")
        self.add_name_button = QtWidgets.QPushButton("Add")
        self.add_name_button.setFixedWidth(50)
        self.add_name_button.setToolTip("Add the name of the selected nodes to the ignore list")
        ignore_name_layout.addWidget(ignore_name_label)
        ignore_name_layout.addWidget(self.ignore_name_lineEdit)
        ignore_name_layout.addWidget(self.add_name_button)

        # --- [ Table Layout ] ---
        self.info_label = QtWidgets.QLabel()
        self.info_label.setStyleSheet("font-style: italic; color: #999;")
        self.nodes_table = QtWidgets.QTableWidget()
        self.nodes_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.nodes_table.setSortingEnabled(True)
        self.nodes_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.nodes_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.nodes_table.horizontalHeader().setStretchLastSection(True)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.hide()
        self.refresh_button = QtWidgets.QPushButton("Refresh List")

        # --- [ Assemble Layout ] ---
        self.main_layout.addLayout(controls_layout)
        self.main_layout.addWidget(self.format_controls_widget)
        self.main_layout.addWidget(self.percentage_controls_widget)
        self.main_layout.addLayout(ignore_class_layout)
        self.main_layout.addLayout(ignore_name_layout)
        self.main_layout.addWidget(self.info_label)
        self.main_layout.addWidget(self.nodes_table)
        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self.refresh_button)
        self.setLayout(self.main_layout)

        # --- [ Connections ] ---
        self.refresh_button.clicked.connect(self.populate_table)
        self.nodes_table.itemDoubleClicked.connect(self.zoom_to_node)
        self.nodes_table.itemSelectionChanged.connect(self._select_node_in_graph)
        self.mode_combobox.currentIndexChanged.connect(self._on_mode_change)
        self.show_all_checkbox.stateChanged.connect(self.populate_table)

        self.overscan_spinbox.editingFinished.connect(self.populate_table)
        self.format_lineEdit.editingFinished.connect(self._validate_and_refresh_format)
        self.percentage_spinbox.editingFinished.connect(self.populate_table)
        self.min_bbox_lineEdit.editingFinished.connect(self._validate_and_refresh_min_bbox)
        self.ignore_class_lineEdit.editingFinished.connect(self.populate_table)
        self.ignore_name_lineEdit.editingFinished.connect(self.populate_table)
        
        self.get_format_button.clicked.connect(self._fetch_and_set_root_format)
        self.add_class_button.clicked.connect(self._add_selected_classes_to_ignore_list)
        self.add_name_button.clicked.connect(self._add_selected_names_to_ignore_list)

        self._update_ui_for_mode()
        QtCore.QTimer.singleShot(50, self._deferred_initial_load)

    def _deferred_initial_load(self):
        """Runs the first data population after the UI is shown"""
        self._fetch_and_set_root_format()
        self.populate_table()

    def _set_controls_enabled(self, enabled):
        """Enable or disable UI controls during processing"""
        self.mode_combobox.setEnabled(enabled)
        self.show_all_checkbox.setEnabled(enabled)
        self.format_lineEdit.setEnabled(enabled)
        self.get_format_button.setEnabled(enabled)
        self.overscan_spinbox.setEnabled(enabled)
        self.percentage_spinbox.setEnabled(enabled)
        self.min_bbox_lineEdit.setEnabled(enabled)
        self.ignore_class_lineEdit.setEnabled(enabled)
        self.add_class_button.setEnabled(enabled)
        self.ignore_name_lineEdit.setEnabled(enabled)
        self.add_name_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)

    def _update_ui_for_mode(self):
        """Shows/hides UI elements and sets table headers based on the selected mode"""
        mode = self.mode_combobox.currentText()
        base_info_text = "<span style='color: #D32F2F;'>Red cells</span> show severity of overscan. <b>Double click</b> node to zoom"

        if mode == "Format Comparison":
            self.format_controls_widget.show()
            self.percentage_controls_widget.hide()
            mode_specific_text = "Shows nodes with bboxs larger than the format + overscan"
            self.info_label.setText("{}<br>{}".format(base_info_text, mode_specific_text))
            self.nodes_table.setColumnCount(5)
            self.nodes_table.setHorizontalHeaderLabels(["Input BBox", "BBox", "Total Pixels", "Node Name", "Class"])
            self.nodes_table.setColumnHidden(0, True)
            self.nodes_table.horizontalHeader().setSortIndicator(2, QtCore.Qt.DescendingOrder)
        else: # Percentage Growth
            self.format_controls_widget.hide()
            self.percentage_controls_widget.show()
            mode_specific_text = "Shows nodes that grow bbox vs input. 'Source' means it has no input"
            self.info_label.setText("{}<br>{}".format(base_info_text, mode_specific_text))
            self.nodes_table.setColumnCount(6)
            self.nodes_table.setHorizontalHeaderLabels(["Input BBox", "BBox", "Growth", "Pixel Increase", "Node Name", "Class"])
            self.nodes_table.setColumnHidden(0, False)
            self.nodes_table.horizontalHeader().setSortIndicator(3, QtCore.Qt.DescendingOrder)

    def _on_mode_change(self):
        """Handles mode change event"""
        self._update_ui_for_mode()
        self.populate_table()

    def _fetch_and_set_root_format(self):
        """Gets the format from Nuke's root settings and populates the line edit"""
        self.format_lineEdit.blockSignals(True)
        root_format = nuke.root().format()
        format_str = "{}x{}".format(root_format.width(), root_format.height())
        self.format_lineEdit.setText(format_str)
        self._last_valid_format = format_str
        self.format_lineEdit.blockSignals(False)

    def _add_selected_classes_to_ignore_list(self):
        """Adds selected node classes to the ignore list and filters the current view"""
        selected_nodes = nuke.selectedNodes()
        if not selected_nodes: return
        
        newly_ignored_classes = {node.Class() for node in selected_nodes}
        current_text = self.ignore_class_lineEdit.text()
        current_items = {item.strip() for item in current_text.split(',') if item.strip()}
        current_items.update(newly_ignored_classes)
        new_text = ", ".join(sorted(list(current_items)))
        self.ignore_class_lineEdit.setText(new_text)

        class_column = 5 if self.mode_combobox.currentText() == "Percentage Growth" else 4
        self._filter_current_view(newly_ignored_classes, column_index=class_column)

    def _add_selected_names_to_ignore_list(self):
        """Adds selected node names to the ignore list and filters the current view"""
        selected_nodes = nuke.selectedNodes()
        if not selected_nodes: return

        newly_ignored_names = {node.name() for node in selected_nodes}
        current_text = self.ignore_name_lineEdit.text()
        current_items = {item.strip() for item in current_text.split(',') if item.strip()}
        current_items.update(newly_ignored_names)
        new_text = ", ".join(sorted(list(current_items)))
        self.ignore_name_lineEdit.setText(new_text)

        name_column = 4 if self.mode_combobox.currentText() == "Percentage Growth" else 3
        self._filter_current_view(newly_ignored_names, column_index=name_column)

    def _filter_current_view(self, items_to_remove, column_index):
        """Removes rows from the current table view without a full refresh"""
        if not items_to_remove or self.nodes_table.isHidden():
            return
            
        for row in reversed(range(self.nodes_table.rowCount())):
            item = self.nodes_table.item(row, column_index)
            if item and item.text() in items_to_remove:
                self.nodes_table.removeRow(row)

    def _get_color_from_factor(self, factor):
        """Calculates a red tint based on a severity factor"""
        if factor <= 1.0: return None
        max_factor = 3.0
        t = min(1.0, (factor - 1.0) / (max_factor - 1.0))
        hue, saturation, lightness = 0, 120 + (t * 135), 190 - (t * 90)
        return QtGui.QColor.fromHsl(int(hue), int(saturation), int(lightness))

    def _validate_format_string(self, text):
        """Checks if a string is a valid 'WIDTHxHEIGHT' format"""
        parts = text.split('x')
        if len(parts) != 2:
            return False
        try:
            w = int(parts[0])
            h = int(parts[1])
            return w > 0 and h > 0
        except (ValueError, IndexError):
            return False

    def _validate_and_refresh_format(self):
        """Validates the root format input and refreshes if valid and changed"""
        current_text = self.format_lineEdit.text()
        if self._validate_format_string(current_text):
            if current_text != self._last_valid_format:
                self._last_valid_format = current_text
                self.populate_table()
        else:
            self.format_lineEdit.setText(self._last_valid_format)

    def _validate_and_refresh_min_bbox(self):
        """Validates the min bbox input and refreshes if it's valid and changed"""
        current_text = self.min_bbox_lineEdit.text()
        if self._validate_format_string(current_text):
            if current_text != self._last_valid_min_bbox:
                self._last_valid_min_bbox = current_text
                self.populate_table()
        else:
            self.min_bbox_lineEdit.setText(self._last_valid_min_bbox)

    def populate_table(self):
        """Builds/Refreshes the table with a progress bar"""
        if self.is_refreshing:
            return
        self.is_refreshing = True
        try:
            self._set_controls_enabled(False)
            self.nodes_table.setSortingEnabled(False)
            self.nodes_table.setRowCount(0)

            show_all = self.show_all_checkbox.isChecked()
            mode = self.mode_combobox.currentText()

            user_ignore_classes_raw = self.ignore_class_lineEdit.text().split(',')
            user_ignore_class_set = {item.strip() for item in user_ignore_classes_raw if item.strip()}
            combined_ignore_class_set = self.hardcoded_ignore_classes.union(user_ignore_class_set)
            ignore_name_list_raw = self.ignore_name_lineEdit.text().split(',')
            ignore_name_set = {item.strip() for item in ignore_name_list_raw if item.strip()}

            all_nodes = nuke.allNodes()
            total_nodes = len(all_nodes)
            
            self.progress_bar.setRange(0, total_nodes)
            self.progress_bar.setValue(0)
            self.progress_bar.show()

            node_data_list = []

            # --- [ Get root area for color calculations ] ---
            root_width, root_height = 0, 0
            try:
                format_str = self.format_lineEdit.text() or self._last_valid_format
                parts = format_str.split('x')
                if len(parts) == 2: root_width, root_height = int(parts[0]), int(parts[1])
            except (ValueError, IndexError): pass
            root_area = float(root_width * root_height)

            if mode == "Format Comparison":
                overscan_value = self.overscan_spinbox.value()
                acceptable_width = root_width + (2 * overscan_value)
                acceptable_height = root_height + (2 * overscan_value)
                acceptable_area = float(acceptable_width * acceptable_height)
            else: # Percentage Growth
                threshold = self.percentage_spinbox.value()
                min_area = 0
                try:
                    min_bbox_str = self.min_bbox_lineEdit.text()
                    parts = min_bbox_str.split('x')
                    if len(parts) == 2: min_area = int(parts[0]) * int(parts[1])
                except (ValueError, IndexError): pass

            for i, node in enumerate(all_nodes):
                self.progress_bar.setValue(i + 1)
                if i % 20 == 0: QtWidgets.QApplication.processEvents()

                if node.Class() in combined_ignore_class_set or node.name() in ignore_name_set:
                    continue
                
                try:
                    if mode == "Format Comparison":
                        bbox = node.bbox()
                        bbox_w, bbox_h = bbox.w(), bbox.h()
                        is_oversized = (bbox_w > acceptable_width or bbox_h > acceptable_height)
                        if show_all or is_oversized:
                            total_pixels = bbox_w * bbox_h
                            bg_color = None
                            if is_oversized and acceptable_area > 0:
                                factor = total_pixels / acceptable_area
                                bg_color = self._get_color_from_factor(factor)
                            node_data_list.append({
                                'name': node.name(), 'class': node.Class(), 'input_bbox_str': 'N/A',
                                'bbox_str': "{} x {}".format(int(bbox_w), int(bbox_h)),
                                'value': total_pixels, 'bg_color': bg_color
                            })
                    else:
                        current_bbox = node.bbox()
                        current_area = float(current_bbox.w() * current_bbox.h())
                        input_node = node.input(0) if node.inputs() > 0 else None
                        growth, is_source, input_bbox_str = 0, False, "N/A"
                        pixel_increase = current_area
                        input_area = 0

                        if input_node:
                            try:
                                input_bbox = input_node.bbox()
                                input_area = float(input_bbox.w() * input_bbox.h())
                                input_bbox_str = "{} x {}".format(int(input_bbox.w()), int(input_bbox.h()))
                                if input_area <= min_area: continue
                                if input_area > 0: growth = ((current_area / input_area) - 1.0) * 100.0
                                pixel_increase = current_area - input_area
                            except Exception: pass
                        elif current_area > 0: is_source = True

                        if show_all or growth >= threshold or (is_source and show_all):
                            bg_color = None
                            if root_area > 0:
                                factor = (max(0, pixel_increase) / root_area) + 1.0
                                bg_color = self._get_color_from_factor(factor)
                            node_data_list.append({
                                'name': node.name(), 'class': node.Class(), 'input_bbox_str': input_bbox_str,
                                'bbox_str': "{} x {}".format(int(current_bbox.w()), int(current_bbox.h())),
                                'value': growth, 'bg_color': bg_color, 'is_source': is_source,
                                'pixel_increase': pixel_increase
                            })
                except Exception:
                    if show_all:
                        node_data_list.append({
                            'name': node.name(), 'class': node.Class(), 'input_bbox_str': 'N/A',
                            'bbox_str': "N/A", 'value': 0, 'bg_color': None, 'is_source': False
                        })
            
            QtWidgets.QApplication.processEvents()
            self._render_table(node_data_list, is_percentage=(mode == "Percentage Growth"))
            self.progress_bar.hide()
            
            name_col = 4 if mode == "Percentage Growth" else 3
            class_col = 5 if mode == "Percentage Growth" else 4
            self.nodes_table.resizeColumnsToContents()

            if mode == "Percentage Growth":
                input_col = 0
                growth_col = 2
                pixel_increase_col = 3
                current_input_width = self.nodes_table.columnWidth(input_col)
                self.nodes_table.setColumnWidth(input_col, int(current_input_width * 1.2))
                current_growth_width = self.nodes_table.columnWidth(growth_col)
                self.nodes_table.setColumnWidth(growth_col, int(current_growth_width * 1.2))
                current_pixel_increase_width = self.nodes_table.columnWidth(pixel_increase_col)
                self.nodes_table.setColumnWidth(pixel_increase_col, int(current_pixel_increase_width * 1.2))

            self.nodes_table.setColumnWidth(name_col, 200)
            self.nodes_table.setColumnWidth(class_col, 150)

            self.nodes_table.setSortingEnabled(True)
            self._set_controls_enabled(True)
        finally:
            self.is_refreshing = False

    def _render_table(self, node_data_list, is_percentage):
        """Fills the table with the data"""
        self.nodes_table.setRowCount(0)
        self.nodes_table.setRowCount(len(node_data_list))
        muted_text_color = QtGui.QColor(128, 128, 128)

        for row, data in enumerate(node_data_list):
            item_input_bbox = QtWidgets.QTableWidgetItem(data['input_bbox_str'])
            item_bbox = NumericTableWidgetItem(data['bbox_str'])
            item_name = QtWidgets.QTableWidgetItem(data['name'])
            item_class = QtWidgets.QTableWidgetItem(data['class'])

            item_name.setData(QtCore.Qt.UserRole, data['name'])
            item_input_bbox.setForeground(muted_text_color)
            item_class.setForeground(muted_text_color)
            
            self.nodes_table.setItem(row, 0, item_input_bbox)
            self.nodes_table.setItem(row, 1, item_bbox)

            if is_percentage:
                growth_value = data.get('value', 0)
                if data.get('is_source', False): item_growth_text = "Source"
                else: item_growth_text = "{:,.1f} %".format(growth_value)
                item_growth = NumericTableWidgetItem(item_growth_text)
                item_growth.setData(QtCore.Qt.UserRole, growth_value)

                pixel_increase = data.get('pixel_increase', 0)
                item_pixels = NumericTableWidgetItem("{:,}".format(int(pixel_increase)))
                item_pixels.setData(QtCore.Qt.UserRole, pixel_increase)

                self.nodes_table.setItem(row, 2, item_growth)
                self.nodes_table.setItem(row, 3, item_pixels)
                self.nodes_table.setItem(row, 4, item_name)
                self.nodes_table.setItem(row, 5, item_class)

                if data['bg_color']:
                    item_bbox.setBackground(data['bg_color'])
                    item_growth.setBackground(data['bg_color'])
                    item_pixels.setBackground(data['bg_color'])
            else:
                total_pixels = data.get('value', 0)
                item_pixels = NumericTableWidgetItem("{:,}".format(int(total_pixels)))
                item_pixels.setData(QtCore.Qt.UserRole, total_pixels)

                self.nodes_table.setItem(row, 2, item_pixels)
                self.nodes_table.setItem(row, 3, item_name)
                self.nodes_table.setItem(row, 4, item_class)

                if data['bg_color']:
                    item_bbox.setBackground(data['bg_color'])
                    item_pixels.setBackground(data['bg_color'])


    def _select_node_in_graph(self):
        """Selects the corresponding node in the Nuke node graph"""
        selected_items = self.nodes_table.selectedItems()
        if not selected_items: return
        row = selected_items[0].row()
        name_column = 4 if self.mode_combobox.currentText() == "Percentage Growth" else 3
        node_name_item = self.nodes_table.item(row, name_column)
        if not node_name_item: return
        node_name = node_name_item.data(QtCore.Qt.UserRole)
        try:
            target_node = nuke.toNode(node_name)
            if not target_node: return
            if not target_node.isSelected():
                for node in nuke.selectedNodes(): node.setSelected(False)
                target_node.setSelected(True)
        except (ValueError, AttributeError): pass

    def zoom_to_node(self, item):
        """Zooms to and selects the double clicked node in the node graph"""
        name_column = 4 if self.mode_combobox.currentText() == "Percentage Growth" else 3
        node_name_item = self.nodes_table.item(item.row(), name_column)
        if node_name_item:
            node_name = node_name_item.data(QtCore.Qt.UserRole)
            try:
                target_node = nuke.toNode(node_name)
                if not target_node: raise ValueError("Node not found")
                
                if not target_node.isSelected():
                    for node in nuke.selectedNodes(): node.setSelected(False)
                    target_node.setSelected(True)

                target_node.showControlPanel()
                nuke.zoom(2, [target_node.xpos(), target_node.ypos()])
            except (ValueError, AttributeError):
                nuke.message("Node '{}' no longer exists".format(node_name))
                self.populate_table()
                
# --- [  Global variable to get around Pythons garbage collector ] ---
_bbox_info_panel = None

def show_floating_panel():
    """Launches BBox Manager floating panel"""
    global _bbox_info_panel
    if _bbox_info_panel and not _bbox_info_panel.isHidden():
        _bbox_info_panel.raise_()
        _bbox_info_panel.activateWindow()
    else:
        _bbox_info_panel = BoundingBoxInfoPanel()
        _bbox_info_panel.setWindowTitle("NodeGraphBuddy - BBox Manager")
        _bbox_info_panel.setWindowFlags(_bbox_info_panel.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        _bbox_info_panel.resize(850, 650)
        _bbox_info_panel.show()