import hou # type: ignore
from typing import Any

def create_toolbox(node_name_list: list = [], coordinates: list[int] = [0,0]) -> dict[str,Any]:

    #-------------------------------------------------------------------------------#
    # Creates a network box named "Toolbox" to add some usefull nodes               #
    # return the list of all nodes in a dictionary                                  #
    #-------------------------------------------------------------------------------#

    lopnet = hou.node("/stage")
    node_list = {}
    nodes_to_layout = []

    for node_name in node_name_list:
        node = lopnet.createNode(node_name)
        node.setPosition(coordinates)
        nodes_to_layout.append(node)
        node_list.update({node_name : node})

    nodes_to_layout = tuple(nodes_to_layout)
    lopnet.layoutChildren(nodes_to_layout)

    toolbox_box = lopnet.createNetworkBox()
    for node in node_list:
        toolbox_box.addItem(node_list[node])
    toolbox_box.setColor(hou.Color(0.52, 0.66, 0.75))
    toolbox_box.setComment("Toolbox")
    toolbox_box.fitAroundContents()
    node_list.update({"toolbox_box" : toolbox_box})

    return node_list
