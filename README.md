# Pluck

AI-powered desktop tool that extracts product information from any shopping page —
**no API key required**.

- **Local mode (free, on-device)** — PaddleOCR + HTML parsing extracts name,
  price, discount, and product URLs without any cloud calls.
- **Cloud mode (optional)** — choose Claude, GPT-4o, Gemini, or Ollama (LLaVA)
  for higher-accuracy vision extraction.
- **Custom instructions** — type `"extract size, color, material"` and the
  model returns those fields under `extra` for every product.
- **Modern desktop GUI** — sidebar engine selector, sleek monogram brand,
  paste-friendly URL input.
- **Subscription tiers** (Free / Pro / Team) with HMAC-signed license keys.

## Install

```bash
cd shopping-extractor
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

> Cloud engines are optional. If you're using the default `local` engine, you
> can skip API keys entirely. To use a cloud engine, set the matching env var
> in a `.env` file:
>
> ```
> ANTHROPIC_API_KEY=sk-ant-...
> OPENAI_API_KEY=sk-...
> GEMINI_API_KEY=...
> ```

## Run

```bash
.venv/bin/python main.py --gui                                       # GUI
.venv/bin/python main.py --url "https://books.toscrape.com/"         # CLI, local engine (free)
.venv/bin/python main.py --url "..." --engine claude                 # cloud Vision
.venv/bin/python main.py --url "..." --engine gemini                 # Google free tier
.venv/bin/python main.py --url "..." --engine ollama --model llava   # fully offline
.venv/bin/python main.py --url "..." -i "extract size and color"     # custom fields
```

| Flag | Description |
|---|---|
| `--url` | Page to extract |
| `--engine` | `local` / `claude` / `openai` / `gemini` / `ollama` (default `local`) |
| `--model` | Override engine's default model |
| `--api-key` | API key for cloud engines (or use the env var) |
| `--max-products N` | Limit number of products (default 20) |
| `--output DIR` | Output folder (default `./output`) |
| `--no-headless` | Show browser window |
| `--instructions / -i` | Free-form instruction for the LLM |
| `--gui` | Launch GUI |
| `--mint-key PRO\|TEAM` | Generate a demo license key |
| `--activate KEY` | Activate a license key |
| `--plan-status` | Show plan, expiry, and today's usage |

## Engines

| Engine | API key | Cost | Accuracy | Notes |
|---|---|---|---|---|
| `local` | ❌ | Free | ★★★ | PaddleOCR/EasyOCR/Tesseract — first install ~300 MB |
| `claude` | ✅ | Paid | ★★★★★ | Best on cluttered cards, Korean/Japanese |
| `openai` | ✅ | Paid | ★★★★ | GPT-4o-mini is fast and cheap |
| `gemini` | ✅ | **Free tier** | ★★★★ | Generous free quota |
| `ollama` | ❌ | Free | ★★★ | Fully offline, requires ~4 GB LLaVA model |

## Output

```
output/
├── images/
│   ├── product_001.png
│   └── ...
├── page_full.png
├── results.json
└── results.csv
```

`results.json` example:

```json
{
  "url": "...",
  "engine": "local",
  "custom_instructions": "extract size and color",
  "products": [
    {
      "id": 1,
      "name": "...",
      "price": "$29.99",
      "discount_rate": "30%",
      "image_path": "output/images/product_001.png",
      "product_url": "...",
      "extra": { "size": "L", "color": "black" }
    }
  ]
}
```

## Subscription

| Plan | Price | Daily extractions | Max products / run | Custom instructions | Batch URLs |
|---|---|---|---|---|---|
| Free | $0 | 5 | 10 | — | — |
| Pro | $9.99 / mo | unlimited | 50 | ✓ | — |
| Team | $29.99 / mo | unlimited | 200 | ✓ | ✓ |

```bash
.venv/bin/python main.py --mint-key PRO --days 365
.venv/bin/python main.py --activate PRO-2027...-...
.venv/bin/python main.py --plan-status
```

In the GUI, click the plan badge in the sidebar to open the subscription dialog.

## Modules

| File | Role |
|---|---|
| `main.py` | CLI entry + license utilities |
| `gui.py` | CustomTkinter app + subscription dialog |
| `subscription.py` | Plans, license signing, usage tracking |
| `scraper.py` | Playwright page load + product card cropping |
| `vision.py` | Multi-engine analyzer (local OCR / Claude / OpenAI / Gemini / Ollama) |
| `parser.py` | BeautifulSoup HTML parsing |
| `extractor.py` | Orchestrates scrape → vision/OCR → merge → save |

## Error handling

- Page load failure → up to 3 retries
- Per-card crop failure → skip and continue
- Vision/OCR failure → fall back to HTML parser
- Selector auto-detection failure → log and exit cleanly with empty results
