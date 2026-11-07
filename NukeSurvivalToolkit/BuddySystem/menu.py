#==============================================================================
#                           ---- About ----
#==============================================================================
"""
    DESCRIPTION: This script collects all the various buddy system features
                 and binds them to hotkeys and/or menu items    
    AUTHOR:      Hiram Gifford
    CONTACT:     hiramgifford.com
"""
VERSION = "01.05"
PUBLISH_DATE = "2026-05-24"
DOCUMENTATION = "https://www.hiramgifford.com/buddy-system"

#==============================================================================
#                       ---- How To Install ----
#==============================================================================
"""
    Step #1:    Copy folder into your .nuke directory e.g. "C:/Users/Hiram/.nuke" (this folder might be hidden)
    Step #2:    Put the line below in your menu.py
    
                    nuke.pluginAddPath('./BuddySystem')
                    
    Step #3:    Launch nuke and you should see a new tool bar item called "BuddySystem"

    Issues:     Please report issues via the contact forum, and provide the following information:
                    1) nuke version e.g. -> 12.2v11
                    2) BuddySystem version e.g. -> 01.00.00
                    3) operating system e.g. -> Windows, Linux, Mac
                    4) What feature you were trying to use at the time of the error
                    5) The error you see in the terminal and/or script editor
"""
#===============================================================================
#                        ---- Imports ----
#===============================================================================

import nuke
import nukescripts
import webbrowser

#===============================================================================
#                   ---- Variables & Menus ----
#===============================================================================
"""
Adds required directories
If your pipeline doesn't allow for new plugin paths, contact your TDs for help 
"""
nuke.pluginAddPath('./Icons')
nuke.pluginAddPath('./Scripts')
nuke.pluginAddPath('./Tools')

"""Create buddy system menu item"""
buddySystem = toolbar.addMenu('BuddySystem', icon = "BuddySystemIcon.png")

#===============================================================================
#              ---- NodeGraphBuddy Scripts & Hotkeys ----
#===============================================================================
"""
You can change the hotkeys here, just swap the binding near the end of each line 
If you prefer to not use hotkeys, leave the binding empty e.g. -> ''
"""

#---------------------------------[ Adjust - Align | Stack | Jump | Match ]-----------------------------------

import node_graph_buddy_smart_arrows
buddySystem.addCommand('Scripts/Adjust/                 --- Align | Stack | Jump | Match ---', '')
buddySystem.addCommand('Scripts/Adjust/Align | Stack | Match Right', 'node_graph_buddy_smart_arrows.align_nodes_advanced(align_direction="vertical", stack_direction="right", align_direction_bd="right")', 'Right', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Align | Stack | Match Left', 'node_graph_buddy_smart_arrows.align_nodes_advanced(align_direction="vertical", stack_direction="left", align_direction_bd="left")', 'Left', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Align | Stack | Jump | Match Up', 'node_graph_buddy_smart_arrows.align_nodes_advanced(align_direction="horizontal", stack_direction="up", align_direction_bd="top")', 'Up', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Align | Stack | Jump | Match Down', 'node_graph_buddy_smart_arrows.align_nodes_advanced(align_direction="horizontal", stack_direction="down", align_direction_bd="bottom")', 'Down', shortcutContext=2)

import node_graph_buddy_align_nodes_upstream
buddySystem.addCommand('Scripts/Adjust/Align Upstream', 'node_graph_buddy_align_nodes_upstream.align_upstream_nodes()', 'PgUp', shortcutContext=2)

buddySystem.addCommand('Scripts/Adjust/                 --- Move | LeapFrog | Bulldozer ---', '')
buddySystem.addCommand('Scripts/Adjust/Move | LeapFrog Up', "node_graph_buddy_smart_arrows.move_nodes_advanced('up', use_physics=False)", 'Ctrl+Up', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Move | LeapFrog Down', "node_graph_buddy_smart_arrows.move_nodes_advanced('down', use_physics=False)", 'Ctrl+Down', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Move Left', "node_graph_buddy_smart_arrows.move_nodes_advanced('left', use_physics=False)", 'Ctrl+Left', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Move Right', "node_graph_buddy_smart_arrows.move_nodes_advanced('right', use_physics=False)", 'Ctrl+Right', shortcutContext=2)

buddySystem.addCommand('Scripts/Adjust/Bulldoze Up', "node_graph_buddy_smart_arrows.move_nodes_advanced('up')", 'Ctrl+Alt+Meta+Up', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Bulldoze Down', "node_graph_buddy_smart_arrows.move_nodes_advanced('down')", 'Ctrl+Alt+Meta+Down', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Bulldoze Left', "node_graph_buddy_smart_arrows.move_nodes_advanced('left')", 'Ctrl+Alt+Meta+Left', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Bulldoze Right', "node_graph_buddy_smart_arrows.move_nodes_advanced('right')", 'Ctrl+Alt+Meta+Right', shortcutContext=2)
buddySystem.addCommand('Scripts/Adjust/Bulldoze Settings', "node_graph_buddy_smart_arrows.show_smart_arrows_config()", 'Ctrl+Alt+Meta+Home', shortcutContext=2)

#---------------------------------[ Adjust - Distribute ]-----------------------------------

import node_graph_buddy_distribute_nodes
buddySystem.addCommand('Scripts/Adjust/                 --- Distribute ---', '')
buddySystem.addCommand('Scripts/Adjust/Distribute | Align', 'node_graph_buddy_distribute_nodes.auto_distribute_nodes(align=True, process_clusters=False)', '*')
buddySystem.addCommand('Scripts/Adjust/Distribute | Align By Cluster', 'node_graph_buddy_distribute_nodes.auto_distribute_nodes(align=True, process_clusters=True)', 'Shift+*')

#---------------------------------[ Adjust - Mirror ]-----------------------------------

import node_graph_buddy_mirror_nodes
buddySystem.addCommand('Scripts/Adjust/                 --- Mirror ---', '')
buddySystem.addCommand('Scripts/Adjust/Mirror Horizontally', 'node_graph_buddy_mirror_nodes.mirror_nodes(direction="horizontal")', 'Alt+M')
buddySystem.addCommand('Scripts/Adjust/Mirror Vertically', 'node_graph_buddy_mirror_nodes.mirror_nodes(direction="vertical")', 'Ctrl+Alt+M')

#---------------------------------[ Adjust - Backdrops ]-----------------------------------

import node_graph_buddy_adjust_backdrops
buddySystem.addCommand('Scripts/Adjust/                 --- Backdrops ---', '')
buddySystem.addCommand('Scripts/Adjust/Increase Z Order', 'node_graph_buddy_adjust_backdrops.adjust_z_order(mode="Increase")', 'Ctrl+Shift+Alt++')
buddySystem.addCommand('Scripts/Adjust/Decrease Z Order', 'node_graph_buddy_adjust_backdrops.adjust_z_order(mode="Decrease")', 'Ctrl+Shift+Alt+-')
buddySystem.addCommand('Scripts/Adjust/Increase Font Size', 'node_graph_buddy_adjust_backdrops.adjust_font_size(mode="Increase")', 'Ctrl+Shift+Alt+PgUp')
buddySystem.addCommand('Scripts/Adjust/Decrease Font Size', 'node_graph_buddy_adjust_backdrops.adjust_font_size(mode="Decrease")', 'Ctrl+Shift+Alt+PgDown')
buddySystem.addCommand('Scripts/Adjust/Resize Backdrop to Nodes', 'node_graph_buddy_adjust_backdrops.resize_backdrop(padding=100)', 'Ctrl+Shift+Alt+*')
buddySystem.addCommand('Scripts/Adjust/Sort Z Order By Size', 'node_graph_buddy_adjust_backdrops.sort_backdrops_by_size_and_zorder()', 'Ctrl+Shift+Alt+Z')

#---------------------------------[ Scale - Biased ]-----------------------------------

import node_graph_buddy_smart_arrows
buddySystem.addCommand('Scripts/Scale/                 --- Scale: Biased ---', '')
buddySystem.addCommand('Scripts/Scale/Decrease Height', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="decrease", direction="bdheight")', 'Ctrl+Shift+Up', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Increase Height', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="increase", direction="bdheight")', 'Ctrl+Shift+Down', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Decrease Width', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="decrease", direction="bdwidth")', 'Ctrl+Shift+Left', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Increase Width', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="increase", direction="bdwidth")', 'Ctrl+Shift+Right', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Increase Uniform', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="increase", direction="bdboth_top")', 'Ctrl+Shift++', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Decrease Uniform', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="decrease", direction="bdboth_bottom")', 'Ctrl+Shift+-', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Scale: Biased Settings', 'node_graph_buddy_smart_arrows.show_smart_arrows_config("scale")', 'Ctrl+Shift+Home', shortcutContext=2)

#---------------------------------[ Scale - Center ]-----------------------------------

buddySystem.addCommand('Scripts/Scale/                 --- Scale: Center ---', '')
buddySystem.addCommand('Scripts/Scale/Decrease Scale Height', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="increase", direction="bdheight_center")', 'Shift+Up', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Increase Scale Height', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="decrease", direction="bdheight_center")', 'Shift+Down', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Decrease Scale Width', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="decrease", direction="bdwidth_center")', 'Shift+Left', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Increase Scale Width', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="increase", direction="bdwidth_center")', 'Shift+Right', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Increase Scale Uniform', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="increase", direction="bdboth_center")', 'Shift++', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Decrease Scale Uniform', 'node_graph_buddy_smart_arrows.scale_nodes_advanced(mode="decrease", direction="bdboth_center")', 'Shift+-', shortcutContext=2)
buddySystem.addCommand('Scripts/Scale/Scale: Center Settings', 'node_graph_buddy_smart_arrows.show_smart_arrows_config("scale")', 'Shift+Home', shortcutContext=2)

#---------------------------------[ Create ]-----------------------------------

import node_graph_buddy_create_backdrop
buddySystem.addCommand('Scripts/Create/Create Blur Or Backdrop', 'node_graph_buddy_create_backdrop.create_backdrop(advanced=False)', 'B')
buddySystem.addCommand('Scripts/Create/Create Blur Or Backdrop Advanced', 'node_graph_buddy_create_backdrop.create_backdrop(advanced=True)', 'Shift+B')

#---------------------------------[ Utilities - General ]-----------------------------------

buddySystem.addCommand('Scripts/Utilities/                 --- General ---', '')
import node_graph_buddy_smart_select_all
buddySystem.addCommand('Scripts/Utilities/Smart Select All', 'node_graph_buddy_smart_select_all.smart_select_all(select_contents=True)', 'Ctrl+A', shortcutContext=2)
buddySystem.addCommand('Scripts/Utilities/Smart Select Backdrops', 'node_graph_buddy_smart_select_all.smart_select_all(select_contents=False)', 'Ctrl+Shift+A', shortcutContext=2)

import node_graph_buddy_label_node
buddySystem.addCommand('Scripts/Utilities/Set Node Label', 'node_graph_buddy_label_node.label_and_recenter_nodes(auto_case=True)', 'A', shortcutContext=2)

import node_graph_buddy_smart_copy_paste
""" Replaces existing copy/paste menu items so it's not confusing to user """
nuke.menu('Nuke').addCommand('Edit/Copy', 'node_graph_buddy_smart_copy_paste.copy()', 'Ctrl+C')
nuke.menu('Nuke').addCommand('Edit/Paste', 'node_graph_buddy_smart_copy_paste.smart_multipaste()', 'Ctrl+V')

""" Also in BuddySystem menu for clarity """
buddySystem.addCommand('Scripts/Utilities/Copy Reconnect (Ctrl+C)', 'node_graph_buddy_smart_copy_paste.copy()', '')
buddySystem.addCommand('Scripts/Utilities/Paste Reconnect', 'node_graph_buddy_smart_copy_paste.paste_reconnect()', 'Shift+N')
buddySystem.addCommand('Scripts/Utilities/Paste To Multiple (Ctrl+V)', 'node_graph_buddy_smart_copy_paste.smart_multipaste()', '')

import node_graph_buddy_toggle_disable
buddySystem.addCommand('Scripts/Utilities/Toggle Disable', 'node_graph_buddy_toggle_disable.toggle_disable()', 'Shift+F')


#---------------------------------[ Utilities - Panels ]-----------------------------------

buddySystem.addCommand('Scripts/Utilities/                 --- Panels ---', '')

import node_graph_buddy_write_node_manager
nuke.menu('Pane').addCommand('Write Node Manager', "nukescripts.panels.restorePanel('hg.buddysystem.WriteNodeManager')", icon='BuddySystemIcon.png')
nukescripts.panels.registerWidgetAsPanel('node_graph_buddy_write_node_manager.WriteOrderPanel', 'Write Node Manager', 'hg.buddysystem.WriteNodeManager')
buddySystem.addCommand('Scripts/Utilities/Write Node Manager', 'node_graph_buddy_write_node_manager.show_floating_panel()','Ctrl+Shift+W')

import node_graph_buddy_bbox_manager
nuke.menu('Pane').addCommand('BBox Manager', "nukescripts.panels.restorePanel('hg.buddysystem.BBoxManager')", icon='BuddySystemIcon.png')
nukescripts.panels.registerWidgetAsPanel('node_graph_buddy_bbox_manager.BoundingBoxInfoPanel', 'BBox Manager', 'hg.buddysystem.BBoxManager')
buddySystem.addCommand('Scripts/Utilities/BBox Manager', 'node_graph_buddy_bbox_manager.show_floating_panel()','')

import node_graph_buddy_nodeoriety_node_counter 
nuke.menu('Pane').addCommand('Nodeoriety Node Counter', "nukescripts.panels.restorePanel('hg.buddysystem.Nodeoriety')", icon='BuddySystemIcon.png')
nukescripts.panels.registerWidgetAsPanel('node_graph_buddy_nodeoriety_node_counter.NodeorietyPanel', 'Nodeoriety Node Counter', 'hg.buddysystem.Nodeoriety')
buddySystem.addCommand('Scripts/Utilities/Nodeoriety Node Counter', 'node_graph_buddy_nodeoriety_node_counter.show_floating_panel()','')

#===============================================================================
#                           ---- Buddy Tools ----
#===============================================================================

#---------------------------------[ ! Warning ! ]-----------------------------------
"""
BuddySystem Tools are stored as Grizmos (Gizmofied Groups) for easy importing, but should not be turned into proper gizmos
If you turn these tools into Gizmos many of the dynamic knobs, and features will no work properly. Please leave them as Grizmos, or groups

You can change the hotkeys here, just modify the bindings at the end of each line
If you prefer to tab search and not use hotkeys, leave the binding empty e.g. -> ''
"""
buddySystem.addCommand('Tools/AnimBuddy', 'nuke.createNode("AnimBuddy")', 'Alt+Shift+A')
buddySystem.addCommand('Tools/CardBuddy', 'nuke.createNode("CardBuddy")', 'Alt+Shift+C')
buddySystem.addCommand('Tools/DepthBuddy', 'nuke.createNode("DepthBuddy")', 'Alt+Shift+Z')
buddySystem.addCommand('Tools/MaskBuddy', 'nuke.createNode("MaskBuddy")', 'Alt+Shift+M')
buddySystem.addCommand('Tools/ProjectionBuddy', 'nuke.createNode("ProjectionBuddy")', 'Alt+Shift+P')
buddySystem.addCommand('Tools/ReflectionBuddy', 'nuke.createNode("ReflectionBuddy")', 'Alt+Shift+R')

#===============================================================================
#                           ---- Fun Stuff ----
#===============================================================================

import fun_rotate_nodes
buddySystem.addCommand('Fun/Rotate Nodes', 'fun_rotate_nodes.rotate_nodes()', '')

import fun_node_randomizer
buddySystem.addCommand('Fun/Node Randomizer', 'fun_node_randomizer.show_randomize_panel()', '')

import fun_caesar_shift
buddySystem.addCommand('Fun/Caesar Shift Labels', 'fun_caesar_shift.show_caesar_shift_label()', '')

import fun_create_big_text_from_backdrops
buddySystem.addCommand('Fun/Create BIG Text', 'fun_create_big_text_from_backdrops.show_create_big_text()', '')

#===============================================================================
#                    ---- Documentation | Version ----
#===============================================================================

buddySystem.addSeparator()

"""Opens the documentation URL in your default web browser"""
#buddySystem.addCommand('Documentation', 'webbrowser.open(DOCUMENTATION)')
buddySystem.addCommand('Documentation/BuddySystem', 'webbrowser.open(DOCUMENTATION)')
buddySystem.addCommand('Documentation/NodeGraphBuddy', 'webbrowser.open("https://www.hiramgifford.com/buddy-system/node-graph-buddy")')

buddySystem.addCommand('Documentation/Scripts/Adjust/Align | Stack | Match', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-smart-arrows-adjust")')
buddySystem.addCommand('Documentation/Scripts/Adjust/Jump', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-smart-arrows-adjust#adjust-jump-anchor-link")')
buddySystem.addCommand('Documentation/Scripts/Adjust/Mirror', 'webbrowser.open("https://www.hiramgifford.com/https://www.hiramgifford.com/nodegraphbuddy-mirror")')
buddySystem.addCommand('Documentation/Scripts/Adjust/Distribute | Align', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-distribute")')
buddySystem.addCommand('Documentation/Scripts/Adjust/Move | LeapFrog', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-smart-arrows-move#move-fast-anchor-link")')
buddySystem.addCommand('Documentation/Scripts/Adjust/Bulldoze', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-smart-arrows-move")')
buddySystem.addCommand('Documentation/Scripts/Adjust/Adjust Backdrops', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-backdrops")')
buddySystem.addCommand('Documentation/Scripts/Scale/Scale: Biased', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-smart-arrows-scale")')
buddySystem.addCommand('Documentation/Scripts/Scale/Scale: Center', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-smart-arrows-scale#scale-center-anchor-link")')
buddySystem.addCommand('Documentation/Scripts/Create/Create Backdrop', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-create-backdrop")')

buddySystem.addCommand('Documentation/Scripts/Utilities/Smart Select All', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-smart-select-all")')
buddySystem.addCommand('Documentation/Scripts/Utilities/Node Label', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-set-node-label")')
buddySystem.addCommand('Documentation/Scripts/Utilities/Smart Copy', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-smart-copy")')
buddySystem.addCommand('Documentation/Scripts/Utilities/Toggle Disable', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-toggle-disable")')
buddySystem.addCommand('Documentation/Scripts/Utilities/BBox Manger', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-bbox-manger")')
buddySystem.addCommand('Documentation/Scripts/Utilities/Write Manager', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-write-manger")')
buddySystem.addCommand('Documentation/Scripts/Utilities/Nodeoriety - Node Counter', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-nodeoriety")')


buddySystem.addCommand('Documentation/Tools/AnimBuddy', 'webbrowser.open("https://www.hiramgifford.com/buddy-system/animbuddy")')
buddySystem.addCommand('Documentation/Tools/CardBuddy', 'webbrowser.open("https://www.hiramgifford.com/buddy-system/cardbuddy")')
buddySystem.addCommand('Documentation/Tools/DepthBuddy', 'webbrowser.open("https://www.hiramgifford.com/buddy-system/depthbuddy")')
buddySystem.addCommand('Documentation/Tools/MaskBuddy', 'webbrowser.open("https://www.hiramgifford.com/buddy-system/maskbuddy")')
buddySystem.addCommand('Documentation/Tools/ProjectionBuddy', 'webbrowser.open("https://www.hiramgifford.com/buddy-system/projectionbuddy")')
buddySystem.addCommand('Documentation/Tools/ReflectionBuddy', 'webbrowser.open("https://www.hiramgifford.com/buddy-system/reflectionbuddy")')

buddySystem.addCommand('Documentation/Fun/Rotate Nodes', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-rotate-nodes")')
buddySystem.addCommand('Documentation/Fun/Create BIG Text', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-create-big-text")')
buddySystem.addCommand('Documentation/Fun/Node Randomizer', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-node-randomizer")')
buddySystem.addCommand('Documentation/Fun/Caesar Shift', 'webbrowser.open("https://www.hiramgifford.com/nodegraphbuddy-caesar-shift")')

"""Displays the version number and other info"""
buddySystem.addCommand("Version " + VERSION, 'nuke.message("""BuddySystem \nVersion {0} | {1} \n<a href="https://www.hiramgifford.com/"><font color=#b16ec2>hiramgifford.com</font></a>""")'.format(VERSION, PUBLISH_DATE))
nuke.tprint('BuddySystem: Installed | Version: {0} | Date: {1} | Contact: hiramgifford.com'.format(VERSION, PUBLISH_DATE))
