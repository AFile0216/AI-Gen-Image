#!/usr/bin/env python3
"""
Image Generation Script - OpenAI-Compatible API

Supports text-to-image (generations) and image-to-image (edits)
via any OpenAI-compatible API endpoint.

Environment Variables:
  IMAGE_GEN_API_URL  - Base URL (e.g. https://ai.t8star.cn/v1)
  IMAGE_GEN_API_KEY  - API key (e.g. sk-xxx)

Usage:
  python generate.py txt2img --prompt "a cat" --size 1024x1024
  python generate.py img2img --prompt "oil painting style" --init_image "photo.png"
  python generate.py img2img --prompt "add a hat" --init_image "https://example.com/img.jpg"
"""

import argparse
import base64
import io
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# ─── Config ──────────────────────────────────────────────────────────────────

def _get_config():
    """Lazily load API config. Raises SystemExit if not configured."""
    api_url = os.environ.get("IMAGE_GEN_API_URL", "").rstrip("/")
    api_key = os.environ.get("IMAGE_GEN_API_KEY", "")
    if not api_url:
        print("ERROR: IMAGE_GEN_API_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not api_key:
        print("ERROR: IMAGE_GEN_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    return api_url, api_key, headers


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _read_image_bytes(source: str) -> bytes:
    """Read an image from a local path or URL and return raw bytes."""
    parsed = urlparse(source)

    # URL source
    if parsed.scheme in ("http", "https"):
        req = Request(source, headers={"User-Agent": "image-gen-api/1.0"})
        with urlopen(req, timeout=30) as resp:
            return resp.read()

    # Local path
    path = Path(source)
    if not path.exists():
        print(f"ERROR: Image file not found: {source}", file=sys.stderr)
        sys.exit(1)
    return path.read_bytes()


def _read_image_as_base64(source: str) -> str:
    """Read image and return base64 encoded string."""
    return base64.b64encode(_read_image_bytes(source)).decode("utf-8")


def _save_image_from_url(url: str, output_dir: str, prefix: str = "gen") -> str:
    """Download image from URL and save locally. Returns saved file path."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    req = Request(url, headers={"User-Agent": "image-gen-api/1.0"})
    with urlopen(req, timeout=60) as resp:
        data = resp.read()

    ts = int(time.time())
    fname = f"{prefix}_{ts}_{uuid.uuid4().hex[:6]}.png"
    fpath = out_dir / fname
    fpath.write_bytes(data)
    print(f"  Saved: {fpath}")
    return str(fpath.resolve())


def _save_image_from_b64(b64_str: str, output_dir: str, prefix: str = "gen") -> str:
    """Decode base64 image and save locally. Returns saved file path."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Strip optional data URI prefix
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]

    img_bytes = base64.b64decode(b64_str)
    ts = int(time.time())
    fname = f"{prefix}_{ts}_{uuid.uuid4().hex[:6]}.png"
    fpath = out_dir / fname
    fpath.write_bytes(img_bytes)
    print(f"  Saved: {fpath}")
    return str(fpath.resolve())


def _post_json(endpoint: str, payload: dict) -> dict:
    """Send a POST request with JSON body and return parsed JSON response."""
    api_url, _, headers = _get_config()
    url = f"{api_url}{endpoint}"
    data = json.dumps(payload).encode("utf-8")

    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: API returned {e.code} {e.reason}", file=sys.stderr)
        print(f"  Response: {body[:500]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: API request failed: {e}", file=sys.stderr)
        sys.exit(1)


def _post_multipart(endpoint: str, fields: dict, files: dict) -> dict:
    """Send a POST request with multipart/form-data (for img2img edits)."""
    api_url, api_key, _ = _get_config()
    url = f"{api_url}{endpoint}"

    boundary = uuid.uuid4().hex
    body_parts = []

    # Add regular fields
    for key, value in fields.items():
        if value is None:
            continue
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        )
        body_parts.append(f"{value}\r\n".encode())

    # Add file fields
    for key, (filename, file_data, content_type) in files.items():
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(
            f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode()
        )
        body_parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        body_parts.append(file_data)
        body_parts.append(b"\r\n")

    body_parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(body_parts)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }

    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: API returned {e.code} {e.reason}", file=sys.stderr)
        print(f"  Response: {err_body[:500]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: API request failed: {e}", file=sys.stderr)
        sys.exit(1)


def _process_response(result: dict, output_dir: str, prefix: str) -> list:
    """Parse OpenAI response and save images. Returns list of saved file paths."""
    data = result.get("data", [])
    if not data:
        print("WARNING: No images returned from API.", file=sys.stderr)
        return []

    saved = []
    revised_prompt = None
    for item in data:
        # Save revised prompt if available
        if item.get("revised_prompt") and not revised_prompt:
            revised_prompt = item["revised_prompt"]

        # Image as URL
        if item.get("url"):
            path = _save_image_from_url(item["url"], output_dir, prefix)
            saved.append(path)

        # Image as base64
        elif item.get("b64_json"):
            path = _save_image_from_b64(item["b64_json"], output_dir, prefix)
            saved.append(path)

    if revised_prompt:
        print(f"  Revised prompt: {revised_prompt}")

    return saved


# ─── Text-to-Image (Generations) ─────────────────────────────────────────────

def txt2img(
    prompt: str,
    model: str = "gpt-image-2",
    size: str = "1024x1024",
    quality: str = "standard",
    n: int = 1,
    style: str = "",
    response_format: str = "b64_json",
    output_dir: str = "generated-images",
    override_payload: str = "",
) -> list:
    """Generate images from a text prompt via /v1/images/generations."""
    payload = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
        "quality": quality,
        "response_format": response_format,
    }

    if style:
        payload["style"] = style

    if override_payload:
        try:
            custom = json.loads(override_payload)
            payload.update(custom)
        except json.JSONDecodeError as e:
            print(f"WARNING: override_payload is not valid JSON, ignoring: {e}", file=sys.stderr)

    print(f"[txt2img] model={model} prompt={prompt!r} size={size}")
    result = _post_json("/images/generations", payload)
    return _process_response(result, output_dir, prefix="txt2img")


# ─── Image-to-Image (Edits) ──────────────────────────────────────────────────

def img2img(
    prompt: str,
    init_image: str,
    model: str = "gpt-image-2",
    size: str = "1024x1024",
    n: int = 1,
    response_format: str = "b64_json",
    output_dir: str = "generated-images",
    override_payload: str = "",
) -> list:
    """Generate images from a text prompt + reference image via /v1/images/edits."""
    print(f"[img2img] model={model} prompt={prompt!r} init_image={init_image!r}")
    img_bytes = _read_image_bytes(init_image)

    # Determine filename and content type
    parsed = urlparse(init_image)
    if parsed.scheme in ("http", "https"):
        filename = Path(parsed.path).name or "image.png"
    else:
        filename = Path(init_image).name

    # Guess content type
    ext = Path(filename).suffix.lower()
    content_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    content_type = content_types.get(ext, "image/png")
    if ext not in content_types:
        filename = filename + ".png"

    # Build multipart fields
    fields = {
        "model": model,
        "prompt": prompt,
        "n": str(n),
        "response_format": response_format,
    }

    if size:
        fields["size"] = size

    # Apply override as additional fields
    if override_payload:
        try:
            custom = json.loads(override_payload)
            for k, v in custom.items():
                fields[k] = str(v) if not isinstance(v, str) else v
        except json.JSONDecodeError as e:
            print(f"WARNING: override_payload is not valid JSON, ignoring: {e}", file=sys.stderr)

    files = {
        "image": (filename, img_bytes, content_type),
    }

    result = _post_multipart("/images/edits", fields, files)
    return _process_response(result, output_dir, prefix="img2img")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Image Generation - OpenAI-Compatible API (txt2img / img2img)"
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # ── Shared arguments ──
    def add_common_args(p):
        p.add_argument("--prompt", required=True, help="Positive prompt")
        p.add_argument("--model", default="", help="Model name (default: gpt-image-2)")
        p.add_argument("--size", default="1024x1024", help="Image size (e.g. 1024x1024, 512x512)")
        p.add_argument("--n", type=int, default=1, help="Number of images to generate")
        p.add_argument("--response_format", default="b64_json", choices=["url", "b64_json"], help="Response format")
        p.add_argument("--output_dir", default="generated-images", help="Output directory")
        p.add_argument("--override_payload", default="", help="JSON string to merge into API payload")

    # ── txt2img ──
    p_txt = sub.add_parser("txt2img", help="Text-to-image generation")
    add_common_args(p_txt)
    p_txt.add_argument("--quality", default="standard", choices=["standard", "hd"], help="Image quality")
    p_txt.add_argument("--style", default="", choices=["", "vivid", "natural"], help="Image style (DALL-E 3 only)")

    # ── img2img ──
    p_img = sub.add_parser("img2img", help="Image-to-image generation")
    add_common_args(p_img)
    p_img.add_argument("--init_image", required=True, help="Init image: local path or URL")

    args = parser.parse_args()

    if args.mode == "txt2img":
        model = args.model or "gpt-image-2"
        saved = txt2img(
            prompt=args.prompt,
            model=model,
            size=args.size,
            quality=args.quality,
            n=args.n,
            style=args.style,
            response_format=args.response_format,
            output_dir=args.output_dir,
            override_payload=args.override_payload,
        )
    else:
        model = args.model or "gpt-image-2"
        saved = img2img(
            prompt=args.prompt,
            init_image=args.init_image,
            model=model,
            size=args.size,
            n=args.n,
            response_format=args.response_format,
            output_dir=args.output_dir,
            override_payload=args.override_payload,
        )

    if saved:
        print(f"\nDone! Generated {len(saved)} image(s).")
        result = {"images": saved, "count": len(saved)}
        print(f"RESULT:{json.dumps(result)}")
    else:
        print("\nNo images generated.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
