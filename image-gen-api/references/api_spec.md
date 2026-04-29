# OpenAI-Compatible Images API Specification

This skill uses the **OpenAI Images API** format. Compatible with any service
that implements the same endpoints (e.g., Azure OpenAI, self-hosted proxies).

## Environment Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `IMAGE_GEN_API_URL` | Yes | Base URL (with `/v1`) | `https://ai.t8star.cn/v1` |
| `IMAGE_GEN_API_KEY` | Yes | API key (Bearer token) | `sk-abc123` |

## Endpoints

### POST `/v1/images/generations` — Text-to-Image

**Request Body:**

```json
{
  "model": "dall-e-3",
  "prompt": "a beautiful sunset over the ocean",
  "n": 1,
  "size": "1024x1024",
  "quality": "standard",
  "style": "vivid",
  "response_format": "url"
}
```

**Response:**

```json
{
  "created": 1706735218,
  "data": [
    {
      "url": "https://...",
      "revised_prompt": "A stunning sunset..."
    }
  ]
}
```

Or with `response_format: "b64_json"`:

```json
{
  "created": 1706735218,
  "data": [
    {
      "b64_json": "<base64-encoded-image>",
      "revised_prompt": "A stunning sunset..."
    }
  ]
}
```

### POST `/v1/images/edits` — Image-to-Image

Uses `multipart/form-data` encoding.

**Form Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `image` | file | Yes | Source image (PNG, max 4MB) |
| `prompt` | string | Yes | Description of desired edit |
| `model` | string | Yes | Model name (e.g. `dall-e-2`) |
| `mask` | file | No | Transparency mask for inpainting |
| `n` | int | No | Number of images (default 1) |
| `size` | string | No | Output size |
| `response_format` | string | No | `url` or `b64_json` |

**Response:** Same format as `/images/generations`.

## Supported Models

| Model | txt2img | img2img | Max Size | Notes |
|---|---|---|---|---|
| `dall-e-3` | ✅ | ❌ | 1792x1024 | Latest, highest quality |
| `dall-e-2` | ✅ | ✅ | 1024x1024 | Supports edits & variations |
| Custom | Depends | Depends | Varies | Check your API provider |

## Supported Sizes

### DALL-E 3
- `1024x1024`
- `1024x1792` (portrait)
- `1792x1024` (landscape)

### DALL-E 2
- `256x256`
- `512x512`
- `1024x1024`

## Quality & Style (DALL-E 3 only)

| Parameter | Values | Description |
|---|---|---|
| `quality` | `standard`, `hd` | HD has finer detail, costs more |
| `style` | `vivid`, `natural` | Vivid = more creative; Natural = more realistic |

## Adapting to Non-Standard APIs

If your API has differences:

1. **Different endpoint paths** — Edit `_post_json()` / `_post_multipart()` endpoint strings
2. **Different auth header** — Modify `_get_config()` headers
3. **Extra parameters** — Use `--override_payload` to inject custom fields
4. **Different response format** — Edit `_process_response()` parsing

### Example: Azure OpenAI

Azure uses a different URL pattern:
```
POST https://{resource}.openai.azure.com/openai/deployments/{model}/images/generations?api-version=2024-02-01
Header: api-key: {key}
```

Modify `_get_config()` and endpoint construction accordingly.

### Example: Custom Proxy with Extra Fields

Some proxies require a `user` or `team_id` field:

```bash
python scripts/generate.py txt2img \
  --prompt "a cat" \
  --override_payload '{"user": "my-team", "team_id": "123"}'
```
