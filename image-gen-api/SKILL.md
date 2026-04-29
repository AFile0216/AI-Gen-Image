---
name: image-gen-api
description: >
  AI image generation via OpenAI-compatible API. Supports text-to-image (generations)
  and image-to-image (edits). Trigger when user wants to: generate images, create artwork,
  produce illustrations, transform photos, apply style transfer, draw pictures, or any
  request involving AI-powered image creation or modification. Keywords: 生图, 文生图,
  图生图, 画图, 生成图片, AI绘图, generate image, create image, draw, img2img, txt2img,
  style transfer, image transformation.
---

# Image Generation API Skill

Generate images from text prompts (txt2img) or transform existing images (img2img)
via any **OpenAI-compatible API** endpoint.

## Prerequisites

Set environment variables before use:

```powershell
# Windows PowerShell
$env:IMAGE_GEN_API_URL = "https://ai.t8star.cn/v1"
$env:IMAGE_GEN_API_KEY = "sk-xxx"
```

```bash
# Linux/macOS
export IMAGE_GEN_API_URL="https://ai.t8star.cn/v1"
export IMAGE_GEN_API_KEY="sk-xxx"
```

The API format follows the **OpenAI Images API** specification.
For detailed API reference, see [references/api_spec.md](references/api_spec.md).

## Workflow

### 1. Determine Generation Mode

| User Intent | Mode | Endpoint |
|---|---|---|
| "画一只猫" / "generate a cat" | txt2img | `/images/generations` |
| "把这张图变成油画" / "make this oil painting" | img2img | `/images/edits` |
| "参考这张图生成..." / "based on this image..." | img2img | `/images/edits` |
| "风格迁移" / "style transfer" | img2img | `/images/edits` |

### 2. Build the Prompt

- Enhance brief user requests with quality modifiers (e.g., "4k, detailed, masterpiece")
- Keep prompts descriptive but concise
- Some models (DALL-E 3) may revise the prompt automatically

### 3. Execute Generation

Run the script with `python`:

**Text-to-Image:**

```bash
python scripts/generate.py txt2img \
  --prompt "a beautiful cat sitting on a windowsill, 4k, detailed" \
  --model "gpt-image-2" \
  --size 1024x1024 \
  --quality standard \
  --output_dir "generated-images"
```

**Image-to-Image (local file):**

```bash
python scripts/generate.py img2img \
  --prompt "transform into oil painting style" \
  --init_image "path/to/photo.png" \
  --model "gpt-image-2" \
  --output_dir "generated-images"
```

**Image-to-Image (URL):**

```bash
python scripts/generate.py img2img \
  --prompt "add cyberpunk neon lights" \
  --init_image "https://example.com/photo.jpg" \
  --output_dir "generated-images"
```

### 4. Custom Payload

Use `--override_payload` to pass arbitrary JSON merged into the request:

```bash
python scripts/generate.py txt2img \
  --prompt "a cat" \
  --override_payload '{"style": "vivid", "user": "test"}'
```

### 5. Present Results

After generation, the script outputs:
- Saved file paths (one per image)
- A `RESULT:` JSON line for machine parsing: `RESULT:{"images": [...], "count": N}`

Show the generated images to the user and provide file locations.

## Parameter Guide

### Common Parameters

| Parameter | Default | Description |
|---|---|---|
| `--prompt` | required | Text description of desired image |
| `--model` | `gpt-image-2` | Model to use |
| `--size` | `1024x1024` | Output size (e.g. 256x256, 512x512, 1024x1024) |
| `--n` | 1 | Number of images per request |
| `--response_format` | `b64_json` | `url` or `b64_json` |
| `--output_dir` | `generated-images` | Where to save images |

### txt2img Only

| Parameter | Default | Description |
|---|---|---|
| `--quality` | `standard` | `standard` or `hd` |
| `--style` | — | `vivid` or `natural` |

### img2img Only

| Parameter | Default | Description |
|---|---|---|
| `--init_image` | required | Source image: local path or URL |

## Troubleshooting

| Issue | Solution |
|---|---|
| `IMAGE_GEN_API_URL is not set` | Set the environment variable |
| API returned 401 | Check `IMAGE_GEN_API_KEY` is correct |
| API returned 404 | Check `IMAGE_GEN_API_URL` ends with `/v1` |
| No images returned | Check model name; try `gpt-image-2` |
| img2img fails | Verify your API supports edits endpoint with the model |
| Connection refused | Check API URL and network connectivity |
| Invalid size | Supported: 256x256, 512x512, 1024x1024, 1024x1792, 1792x1024 |

## API Adaptation

For detailed API specification, response format, and adaptation to non-standard
endpoints, see [references/api_spec.md](references/api_spec.md).
