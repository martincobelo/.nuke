'''
@author: Tony Lyons (creativelyons@gmail.com)
# init.py
'''
# import os
# import nuke

nuke.pluginAddPath("/home/mcobelo/.nuke/NukeSurvivalToolkit")

nuke.pluginAddPath('./CloseAllProperties')

nuke.pluginAddPath(r"/home/mcobelo/.nuke/Expression")

nuke.pluginAddPath('/home/mcobelo/.nuke/NukeSurvivalToolkit/gizmos/spin_tools')




if nuke.NUKE_VERSION_MAJOR > 15:
	nuke.pluginAddPath("./nuke16_and_higher")
else:
	nuke.pluginAddPath("./nuke15_and_lower")





