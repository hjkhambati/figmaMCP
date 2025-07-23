import os
import requests
from dotenv import load_dotenv
from mcp_server import mcp
from transform import transform_node_tree
from fastmcp.utilities.types import Image
import json
from pathlib import Path

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

@mcp.tool(
    name="download_figma_assets",
    description="""
    Downloads all images from a Figma file and saves them in the React app's assets directory.
    Handles renaming and organizing the assets appropriately.
    """
)
def download_figma_assets(fileKey: str, nodeId: str = None):
    try:
        # Get the React app assets directory
        assets_dir = Path("react-app/src/assets")
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # Get the Figma file data
        if nodeId:
            nodeId = nodeId.replace("-", ":")
            params = {"ids": nodeId}
            raw = figma_api_get(f"/files/{fileKey}/nodes", params=params)
            nodes = raw.get("nodes", {})
            if nodeId not in nodes:
                return {"error": f"Node ID '{nodeId}' not found"}
            node = nodes[nodeId].get("document")
        else:
            raw = figma_api_get(f"/files/{fileKey}")
            node = raw.get("document")

        if not node:
            return {"error": "No document found in response"}

        # Function to extract image nodes
        def extract_images(node, images=None):
            if images is None:
                images = []
            
            # Check if the node is an image or has a fill that's an image
            if node.get("type") in ["IMAGE", "VECTOR"] or (
                node.get("fills") and any(fill.get("type") == "IMAGE" for fill in node.get("fills", []))
            ):
                images.append({
                    "id": node.get("id"),
                    "name": node.get("name", "").lower().replace(" ", "_")
                })
            
            # Recursively process children
            for child in node.get("children", []):
                extract_images(child, images)
            
            return images

        # Get all image nodes
        image_nodes = extract_images(node)
        if not image_nodes:
            return {"message": "No images found in the design"}

        # Download and save each image
        downloaded_images = []
        asset_mapping = {}

        for img in image_nodes:
            try:
                # Generate a unique filename
                base_name = ''.join(c for c in img["name"] if c.isalnum() or c in "_-")
                if not base_name:
                    base_name = f"image_{img['id'].replace(':', '_')}"
                filename = f"{base_name}.png"
                
                # Get image URL
                image_url = get_node_image_url(fileKey, img["id"])
                if not image_url:
                    continue

                # Download and save image
                image_response = requests.get(image_url)
                image_response.raise_for_status()
                
                file_path = assets_dir / filename
                with open(file_path, "wb") as f:
                    f.write(image_response.content)
                
                downloaded_images.append(filename)
                asset_mapping[img["id"]] = f"/src/assets/{filename}"
                
            except Exception as e:
                print(f"Failed to download image {img['id']}: {e}")
                continue

        # Create an asset manifest
        manifest = {
            "assets": asset_mapping
        }
        with open(assets_dir / "asset-manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        return {
            "message": f"Successfully downloaded {len(downloaded_images)} images",
            "downloaded": downloaded_images,
            "manifest": manifest
        }

    except Exception as e:
        return {"error": f"Failed to download assets: {e}"}
