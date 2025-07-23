import os
import requests
from dotenv import load_dotenv
from mcp_server import mcp
from transform import transform_node_tree
from fastmcp.utilities.types import Image

load_dotenv()
FIGMA_API_KEY = os.getenv("FIGMA_API_KEY")
assert FIGMA_API_KEY, "Missing FIGMA_API_KEY in .env"

def figma_api_get(path, params=None):
    base_url = "https://api.figma.com/v1"
    headers = {"X-Figma-Token": FIGMA_API_KEY}
    url = f"{base_url}{path}"
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json()

def get_node_image_url(fileKey: str, nodeId: str, format="png"):
    """Get a Figma-hosted image URL for a node (expires in ~5 mins)."""
    params = {"ids": nodeId, "format": format}
    result = figma_api_get(f"/images/{fileKey}", params=params)
    return result.get("images", {}).get(nodeId)


@mcp.tool(
    name="get_figma_data",
    description="""
    Fetches and transforms a Figma file or node into a simplified layout/style tree.

    Use this tool when you want to get structured layout/styling data of a UI for code generation.
    """
)
def get_figma_data(fileKey: str, nodeId: str = None, depth: int = None):
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

        transformed = transform_node_tree(node)

        return {
            "instructions": "Use this layout and style data to recreate the UI. "
                            "Call `download_figma_image` to view the visual reference.",
            "design": transformed
        }

    except Exception as e:
        return {"error": f"Failed to process Figma data: {e}"}


@mcp.tool(
    name="download_figma_image",
    description="""
    Downloads a design node from Figma and returns it as an image object for visual reference.
    """
)
def download_figma_image(fileKey: str, nodeId: str):
    try:
        nodeId = nodeId.replace("-", ":")
        image_url = get_node_image_url(fileKey, nodeId)
        if not image_url:
            return {"error": f"Could not get image URL for nodeId {nodeId}"}

        image_response = requests.get(image_url)
        image_response.raise_for_status()

        img = Image(data=image_response.content, format="png")
        return img.to_image_content()

    except Exception as e:
        return {"error": f"Failed to fetch or convert image: {e}"}
