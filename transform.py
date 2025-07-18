# transform.py

def extract_layout_info(node: dict) -> dict:
    layout = {
        "x": node.get("absoluteBoundingBox", {}).get("x"),
        "y": node.get("absoluteBoundingBox", {}).get("y"),
        "width": node.get("absoluteBoundingBox", {}).get("width"),
        "height": node.get("absoluteBoundingBox", {}).get("height"),
        "layoutMode": node.get("layoutMode"),
        "primaryAxisAlignItems": node.get("primaryAxisAlignItems"),
        "counterAxisAlignItems": node.get("counterAxisAlignItems"),
        "itemSpacing": node.get("itemSpacing"),
        "paddingLeft": node.get("paddingLeft"),
        "paddingRight": node.get("paddingRight"),
        "paddingTop": node.get("paddingTop"),
        "paddingBottom": node.get("paddingBottom"),
        "layoutAlign": node.get("layoutAlign"),
        "layoutGrow": node.get("layoutGrow"),
        "constraints": node.get("constraints"),
        "clipsContent": node.get("clipsContent"),
    }
    return {k: v for k, v in layout.items() if v is not None}


def extract_style_info(node: dict) -> dict:
    styles = {}

    # Fill
    if isinstance(node.get("fills"), list) and node["fills"]:
        fill = node["fills"][0]
        if fill.get("type") == "SOLID" and "color" in fill:
            color = fill["color"]
            styles["fill"] = {
                "r": round(color["r"] * 255),
                "g": round(color["g"] * 255),
                "b": round(color["b"] * 255),
                "a": fill.get("opacity", 1.0)
            }

    # Stroke
    if isinstance(node.get("strokes"), list) and node["strokes"]:
        stroke = node["strokes"][0]
        if stroke.get("type") == "SOLID" and "color" in stroke:
            color = stroke["color"]
            styles["stroke"] = {
                "r": round(color["r"] * 255),
                "g": round(color["g"] * 255),
                "b": round(color["b"] * 255),
                "a": stroke.get("opacity", 1.0)
            }
        if "strokeWeight" in node:
            styles["strokeWeight"] = node["strokeWeight"]

    # Typography
    for key in ["fontName", "fontSize", "lineHeightPx", "letterSpacing", "textAlignHorizontal", "textAlignVertical"]:
        if key in node:
            styles[key] = node[key]

    # Effects
    if isinstance(node.get("effects"), list) and node["effects"]:
        visible = [e for e in node["effects"] if e.get("visible", True)]
        if visible:
            styles["effects"] = visible

    return styles


def prune_node(node: dict) -> dict:
    ignored = {
        "id", "pluginData", "sharedPluginData", "componentId", "absoluteRenderBounds",
        "isMask", "isMaskOutline", "transitionNodeID", "visible", "layoutGrids",
        "styles", "characterStyleOverrides", "styleOverrideTable", "overrideValues",
        "componentPropertyReferences"
    }
    return {k: v for k, v in node.items() if k not in ignored}


def transform_node_tree(node: dict) -> dict:
    if not isinstance(node, dict):
        return {}

    transformed = prune_node(node)
    transformed["layout"] = extract_layout_info(node)
    transformed["styles"] = extract_style_info(node)

    children = node.get("children", [])
    if isinstance(children, list) and children:
        transformed["children"] = [transform_node_tree(c) for c in children]

    return transformed
