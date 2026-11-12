# Brand: name, logo, palette, typography

The UX/UI designer proposes, the user chooses. Everything visual becomes design tokens.

## Product name (DISCOVER)

- Propose 3-5 names in different styles (descriptive, evocative, invented, local language), each with one line of rationale, how it sounds in the target languages, and possible collisions.
- Collision checks (existing products in the same domain, app stores, package registries, domain names) are HYPOTHESIS unless you actually searched; say what you searched. Trademark clearance is a legal question: suggest checking official registers (EUIPO, USPTO, the national office) or a professional before a commercial launch.

## Palette and tokens (PLAN)

1. Start from the brand intent (3 adjectives the user agrees with) and the platforms.
2. Build primitives (color scales, e.g. `color.blue.50` ... `color.blue.900`, neutrals), then semantic tokens (`color.bg.default`, `color.text.default`, `color.text.muted`, `color.action.primary`, `color.border`, `color.danger`, `color.success`), for light and dark mode when needed.
3. List every real foreground/background pair in `contrast_pairs` with its usage (`text`, `large-text`, `ui`).
4. Run `scripts/contrast_check.py design/tokens.json`; fix failures by adjusting the scale, not by dropping pairs.
5. Present 2-3 palettes as swatches (an SVG or HTML preview) with the contrast results.

## Typography

One or two families, with license checked (Google Fonts / SIL OFL are safe defaults; system font stacks are fine). Define a type scale as tokens (`font.size.xs`...`3xl`, line heights, weights). On mobile, respect dynamic type / font scaling.

## Logo

- Claude writes logos as clean SVG: simple geometry, a `viewBox`, no embedded bitmaps, works in one color, legible at 16 px (favicon) and as an app icon (square, safe area for adaptive Android icons and iOS masks).
- Propose at least three directions (wordmark, symbol + wordmark, monogram/symbol). Deliver the chosen one in: full color, one color, inverted, square icon.
- Never imitate existing logos, mascots or brand identities.

## When an external image model helps

SVG covers logos, icons and simple illustrations. For photographic or painterly images, complex illustrations, or mockups with realistic textures, use an image-generation provider:

| Need | Good fits (verify current offer and API before use) |
|---|---|
| Logos/posters with legible text | Ideogram |
| Vector-style brand assets | Recraft |
| General illustrations and mockups | OpenAI image models, Google Gemini/Imagen, Midjourney (no official public API: prompt only) |

Integration rules:
- Only if the user configured it: an MCP server, or an API key in an environment variable (for example `OPENAI_API_KEY`, `IDEOGRAM_API_KEY`). Never ask the user to paste a key into the chat.
- Otherwise write a **ready-to-paste prompt**: subject, style, palette hex values, composition, aspect ratio, text to render (exact spelling), what to avoid. The user generates the image and drops it in `design/`.
- Check the provider's terms on commercial use and ownership before using generated assets in a product; record it in the ADR for the brand.
