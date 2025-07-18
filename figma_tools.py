import os
import requests
from dotenv import load_dotenv
from mcp_server import mcp
from transform import transform_node_tree

load_dotenv()
FIGMA_API_KEY = os.getenv("FIGMA_API_KEY")
assert FIGMA_API_KEY, "Missing FIGMA_API_KEY in .env"


def figma_api_get(path, params=None):
    """Helper to call Figma API with authorization."""
    base_url = "https://api.figma.com/v1"
    headers = {"X-Figma-Token": FIGMA_API_KEY}
    url = f"{base_url}{path}"
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json()


@mcp.tool(name="get_figma_data", description="Fetches and transforms a Figma file or node")
def get_figma_data(fileKey: str, nodeId: str = None, depth: int = None):
    """
    Fetches and transforms a Figma file or node into a simplified layout/style tree.
    """
    try:
        if nodeId:
            nodeId = nodeId.replace("-", ":")
            params = {"ids": nodeId}
            if depth:
                params["depth"] = depth
            raw = figma_api_get(f"/files/{fileKey}/nodes", params=params)
            nodes = raw.get("nodes", {})
            if nodeId not in nodes:
                return {"error": f"Node ID '{nodeId}' not found in response. Available nodes: {list(nodes.keys())}"}
            node = nodes[nodeId].get("document")
            if not node:
                return {"error": f"Node '{nodeId}' found, but 'document' field is missing."}
        else:
            raw = figma_api_get(f"/files/{fileKey}")
            node = raw.get("document")
            if not node:
                return {"error": "Document field missing from file-level response."}

        return transform_node_tree(node)
    except Exception as e:
        return {"error": f"Failed to process Figma data: {e}"}    


@mcp.tool(
    name="download_figma_images",
    description="Returns Figma-hosted PNG or SVG image URLs for the specified nodes"
)
def download_figma_images(fileKey: str, nodes: list, format: str = "png"):
    """
    Get image URLs (PNG or SVG) for specified nodes in a Figma file.
    Parameters:
      - fileKey (string): Figma file ID.
      - nodes (list): List of dicts like {nodeId: str, fileName: str}
      - format (string): Image format, either 'png' or 'svg'
    Returns:
      - List of dicts with {fileName, url} or error. The url will expire in 5 minutes.
    """

    format = format.lower().strip()
    if format not in {"png", "svg"}:
        return {"error": f"Invalid format '{format}'. Use 'png' or 'svg'."}

    if not isinstance(nodes, list) or not all(isinstance(n, dict) and "nodeId" in n for n in nodes):
        return {
            "error": "Invalid 'nodes' format. Expected a list of dicts like {nodeId: str, fileName: str}"
        }

    node_ids = [n["nodeId"] for n in nodes]
    params = {"ids": ",".join(node_ids), "format": format}

    try:
        result = figma_api_get(f"/images/{fileKey}", params=params)
        image_map = result.get("images", {})
    except Exception as e:
        return {"error": f"Failed to get image URLs: {e}"}

    output = []
    for node in nodes:
        node_id = node["nodeId"]
        file_name = node.get("fileName", f"{node_id}.{format}")
        url = image_map.get(node_id)

        if url:
            output.append({
                "fileName": file_name,
                "format": format,
                "url": url
            })
        else:
            output.append({
                "fileName": file_name,
                "format": format,
                "error": f"No image URL found for nodeId: {node_id}"
            })

    return {"images": output}
