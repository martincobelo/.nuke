#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script counts all nodes in the current Nuke script,
                 and displays the data in a panel
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
    VERSION:     01.03
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
import re
from collections import defaultdict

# --- [  Import PySide based on nuke version ] --- 
if nuke.NUKE_VERSION_MAJOR < 11:
    from PySide.QtGui import (QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView, QLineEdit,
                              QTreeWidgetItemIterator)
    from PySide.QtCore import Qt
elif nuke.NUKE_VERSION_MAJOR < 16:
    from PySide2.QtWidgets import (QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QVBoxLayout, QHBoxLayout, 
                                   QPushButton, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView, QLineEdit, 
                                   QTreeWidgetItemIterator)
    from PySide2.QtCore import Qt
else:
    from PySide6.QtWidgets import (QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QVBoxLayout, QHBoxLayout, 
                                   QPushButton, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView, QLineEdit, 
                                   QTreeWidgetItemIterator)
    from PySide6.QtCore import Qt

#===============================================================================
#                       ---- Scripts ----
#===============================================================================

class NodeorietyPanel(QWidget):
    """
    The main Panel UI for Nodeoriety
    Can switch between a hierarchical and table view, and includes a search bar.
    """
    def __init__(self, parent=None):
        """Panel Layout"""
        super(NodeorietyPanel, self).__init__(parent)
        
        # --- [ Set Default View ] ---
        self.current_view = 'table'
        self.tables = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        # --- [ Search Bar ] ---
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by class or name...")
        self.search_bar.textChanged.connect(self.filter_views)
        self.main_layout.addWidget(self.search_bar)
        
        self.content_widget = QWidget() # Placeholder for view content
        self.main_layout.addWidget(self.content_widget)

        button_layout = QHBoxLayout()
        
        self.switch_view_button = QPushButton("Switch to Hierarchical View")
        self.switch_view_button.clicked.connect(self.toggle_view)
        button_layout.addWidget(self.switch_view_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_active_view)
        button_layout.addWidget(refresh_button)
        
        self.main_layout.addLayout(button_layout)
        self.show_table_view()

    def filter_views(self):
        """Filters the active view based on the search bar text."""
        search_text = self.search_bar.text().lower()
        
        if self.current_view == 'table':
            for table in self.tables:
                for i in range(table.rowCount()):
                    item = table.item(i, 0)
                    if item:
                        match = search_text in item.text().lower()
                        table.setRowHidden(i, not match)
        else: # Hierarchical view
            tree = self.content_widget
            
            # --- [ If search is cleared, unhide everything ] ---
            if not search_text:
                iterator = QTreeWidgetItemIterator(tree)
                while iterator.value():
                    iterator.value().setHidden(False)
                    iterator += 1
                return

            # --- [ Find all items that match the search text ] ---
            matching_items = []
            iterator = QTreeWidgetItemIterator(tree)
            while iterator.value():
                item = iterator.value()
                # Initially hide all items
                item.setHidden(True)
                if search_text in item.text(0).lower():
                    matching_items.append(item)
                iterator += 1

            # --- [ Unhide matching items and their parents ] ---
            for item in matching_items:
                item.setHidden(False)
                parent = item.parent()
                while parent:
                    parent.setHidden(False)
                    parent.setExpanded(True)
                    parent = parent.parent()

    def toggle_view(self):
        """Switch between hierarchical and table views"""
        if self.current_view == 'hierarchical':
            self.current_view = 'table'
            self.switch_view_button.setText("Switch to Hierarchical View")
            self.show_table_view()
        else:
            self.current_view = 'hierarchical'
            self.switch_view_button.setText("Switch to Table View")
            self.show_hierarchical_view()

    def refresh_active_view(self):
        """Refreshes whichever view is currently active"""
        if self.current_view == 'hierarchical':
            self.show_hierarchical_view()
        else:
            self.show_table_view()

    def show_hierarchical_view(self):
        """Rebuilds hierarchical view"""
        self.content_widget.deleteLater()
        self.content_widget = QTreeWidget()
        self.content_widget.setHeaderLabels(["Nodes", "Count"])
        header = self.content_widget.header()
        try:
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        except AttributeError:
            header.setResizeMode(0, QHeaderView.Stretch)
            header.setResizeMode(1, QHeaderView.ResizeToContents)

        self.main_layout.insertWidget(1, self.content_widget)

        root_item = QTreeWidgetItem(self.content_widget, ["Root Level", ""])
        self._process_node_level(root_item, nuke.root())
        root_item.setExpanded(True)
        self.filter_views()

    def _process_node_level(self, parent_item, parent_node):
        """Recursive function for hierarchical view"""
        node_counts = defaultdict(int)
        containers_to_process = []
        for node in parent_node.nodes():
            node_counts[node.Class()] += 1
            # --- [ Check if node is a group-like container ] ---
            if hasattr(node, 'nodes'):
                containers_to_process.append(node)
        
        parent_item.setText(1, str(sum(node_counts.values())))
        for node_class, count in sorted(node_counts.items()):
            QTreeWidgetItem(parent_item, [node_class, str(count)])
        for container_node in sorted(containers_to_process, key=lambda n: n.name()):
            container_item = QTreeWidgetItem(parent_item, ["{0} ({1})".format(container_node.name(), container_node.Class()), ""])
            self._process_node_level(container_item, container_node)

    def show_table_view(self):
        """Rebuilds table view"""
        
        # --- [ Get Data ] ---
        all_nodes = nuke.allNodes(recurseGroups=True)
        node_counts = defaultdict(int)
        gizmo_counts = defaultdict(int)
        group_counts = defaultdict(int)
        livegroup_counts = defaultdict(int)
        precomp_counts = defaultdict(int)

        for node in all_nodes:
            node_class = node.Class()
            node_counts[node_class] += 1
            # --- [ Sanitize name to group instances like 'Blur1', 'Blur2' together ] ---
            sanitized_match = re.match(r'^(.*?)(?:[_0-9]+)?$', node.name())
            sanitized_name = sanitized_match.group(1) if sanitized_match else node.name()

            if node_class == 'Group':
                group_counts[sanitized_name] += 1
            elif node_class == 'LiveGroup':
                 livegroup_counts[sanitized_name] += 1
            elif node_class == 'Precomp':
                precomp_counts[sanitized_name] += 1
            # Note to self. Any other node that is an instance of a Group is likely a gizmo. Will need to update if new node types are introduced
            elif isinstance(node, nuke.Group):
                gizmo_counts[node_class] += 1
        
        # --- [ Rebuild UI ] ---
        self.content_widget.deleteLater()
        self.tables = []
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # --- [  Layout node counts by class/type ] ---
        if all_nodes:
            content_layout.addWidget(self._create_section_widget("All Nodes", len(all_nodes), node_counts, ["Node Class", "Count"]))
        if gizmo_counts:
            content_layout.addWidget(self._create_section_widget("Gizmos", sum(gizmo_counts.values()), gizmo_counts, ["Gizmo Class", "Count"]))
        if group_counts:
            content_layout.addWidget(self._create_section_widget("Groups", sum(group_counts.values()), group_counts, ["Group Name", "Count"]))
        if precomp_counts:
            content_layout.addWidget(self._create_section_widget("Precomps", sum(precomp_counts.values()), precomp_counts, ["Precomp Name", "Count"]))
        if livegroup_counts:
            content_layout.addWidget(self._create_section_widget("LiveGroups", sum(livegroup_counts.values()), livegroup_counts, ["LiveGroup Name", "Count"]))
        
        self.main_layout.insertWidget(1, self.content_widget)
        self.filter_views()

    def _create_section_widget(self, title, total, data, headers):
        """Helper to create a single vertical column for the table view"""
        section_widget = QWidget()
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(5, 0, 5, 0)
        title_label = QLabel("<b>{0}</b> (Total: {1})".format(title, total))
        section_layout.addWidget(title_label)
        table = self._create_table_widget(data, headers)
        self.tables.append(table) 
        section_layout.addWidget(table)
        return section_widget
        
    def _create_table_widget(self, data, headers):
        """Helper to create and populate a QTableWidget for the table view"""
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(headers)
        table.setSortingEnabled(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = table.horizontalHeader()

        try:
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        except AttributeError:
            header.setResizeMode(0, QHeaderView.Stretch)
            header.setResizeMode(1, QHeaderView.ResizeToContents)

        
        sorted_data = sorted(data.items(), key=lambda item: item[1], reverse=True)
        table.setRowCount(len(sorted_data))
        for row, (name, count) in enumerate(sorted_data):
            name_item = QTableWidgetItem(name)
            count_item = QTableWidgetItem()
            count_item.setData(Qt.EditRole, count)
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, count_item)
        return table

# --- [  Global variable to get around Pythons garbage collector ] ---
_nodeoriety_floating_panel = None

def show_floating_panel():
    """Launches Nodeoriety floating panel"""
    global _nodeoriety_floating_panel
    if _nodeoriety_floating_panel:
        _nodeoriety_floating_panel.close()
    
    _nodeoriety_floating_panel = NodeorietyPanel()
    _nodeoriety_floating_panel.setWindowTitle("NodeGraphBuddy - Nodeoriety Node Counter")
    _nodeoriety_floating_panel.setWindowFlags(_nodeoriety_floating_panel.windowFlags() | Qt.WindowStaysOnTopHint)
    _nodeoriety_floating_panel.setMinimumSize(900, 600)
    _nodeoriety_floating_panel.show()