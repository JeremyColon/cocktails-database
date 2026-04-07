# Plan: Image Recognition for Bar Setup

An AI-powered feature that lets users photograph their liquor shelf and get instant ingredient suggestions, dramatically reducing the friction of the first-time bar setup experience.

---

## Feature Overview

| Dimension | Assessment |
|---|---|
| **Value** | High — first-time bar setup is the biggest drop-off point; this collapses a 20-minute manual task into 30 seconds |
| **Complexity** | Medium-High — new AI dependency, multipart upload handling, fuzzy matching pipeline, review UI |
| **Risk** | Medium — model accuracy is uncertain; graceful degradation is critical |
| **Recommendation** | **Build it.** The value is high enough to justify the complexity. Use Claude Haiku (already in use) to keep cost near zero and integration trivial. |

> **Re: the product image dataset question from TODO.md** — a custom image dataset is not needed. The LLM vision approach (Claude Haiku reading label text + reasoning about bottle shape/color) handles recognition without any training data or dataset maintenance. The model's world knowledge of spirits brands is sufficient for the vast majority of common bottles.

---

## 1. Feature Concept — UX Flow

### Entry Point
On `MyBar.tsx`, in the "Add Ingredients" right column, a new "Scan Your Bar" card with a camera icon. The entry point is especially prominent when the bar is empty.

### Step 1: Capture
User taps/clicks "Scan Your Bar". On mobile, the browser's native file picker opens with `accept="image/*" capture="environment"` — this offers the camera directly on iOS/Android. On desktop, a standard file picker appears. A brief instructional tip: _"Take a photo of your liquor shelf or bar cart. The clearer the labels, the better."_

### Step 2: Upload and Processing
The image is uploaded immediately on selection (no extra "submit" click). A loading state replaces the upload card: a subtle animated pulse with the message "Identifying bottles…" This takes 2–5 seconds.

### Step 3: Review
The upload card transforms into a review list. Each recognized item is shown as a row with:
- The raw name the model detected (e.g. "Maker's Mark Bourbon Whiskey")
- The matched canonical name from the DB (e.g. "bourbon") with a confidence indicator — a colored dot (green / amber / red)
- A checkbox, pre-checked for high/medium confidence matches, unchecked for low confidence
- Items with no DB match are shown but grayed out with a note: _"Not in our ingredient list"_ — cannot be added but visible for transparency

The user can deselect any items they don't actually have (e.g. a bottle visible in the background they don't own).

### Step 4: Confirm
A single "Add X ingredients to my bar" button calls the existing `POST /api/bar/add` endpoint — no new add endpoint needed. The UI shows a success state with a brief count ("Added 14 ingredients"), and the bar inventory re-renders.

### Error States
- Image too large: client-side validation before upload, clear message
- API error / timeout: "Something went wrong — please try again or add ingredients manually"
- No bottles detected: "We couldn't identify any bottles in this photo. Try better lighting or a closer shot."
- All detected items have no DB match: same as above

---

## 2. Vision API Options

### Option A: Claude Haiku (claude-haiku-4-5-20251001) — via Anthropic's existing API

**Accuracy:** Strong for well-lit, labeled bottles. Claude's vision understands context — it knows what a liquor bottle looks like, can read partial labels, and can infer that "Gran Patron" maps to tequila even if the full label isn't readable. Less reliable with dark photos, reflective bottles, or partially obscured labels.

**Cost:** ~$0.001–0.002 per scan at typical image sizes. Effectively free at any realistic usage volume.

**Latency:** 2–5 seconds for a single image with a structured prompt. Acceptable for a background scan UX.

**Ease of integration:** Zero new dependencies. The `anthropic` SDK is already in the project and `ANTHROPIC_API_KEY` is already in the environment. A single new service function is all that's needed.

**Prompt control:** Full. Claude can be given the entire `mapped_ingredient` list as context and asked to map directly.

**Limitations:** Not purpose-built for OCR or product recognition. For bottles with obscured labels it may guess based on shape/color, which can produce confident-sounding wrong answers.

---

### Option B: OpenAI GPT-4o (gpt-4o-mini)

**Accuracy:** Comparable to Claude Haiku for clear images. GPT-4V is arguably slightly better trained on product imagery from internet-scale data, but the difference is marginal for common spirits brands.

**Cost:** ~$0.003 per image at typical resolution. Similar to Haiku. `gpt-4o` full: ~$0.03 per image — 15x more expensive with no meaningful accuracy gain for this use case.

**Ease of integration:** Requires adding the `openai` SDK, a new `OPENAI_API_KEY` env var, and a new vendor dependency when one already exists.

**Verdict:** No meaningful accuracy advantage. Adds a second AI vendor for no gain. Not worth it.

---

### Option C: Google Cloud Vision API

**Accuracy:** Highest raw OCR accuracy. But it returns generic labels ("bottle", "distilled beverage") and raw OCR text — not structured "this is a bottle of Bulleit Rye Whiskey." Post-processing the OCR output to extract brand/spirit type requires significant extra code.

**Cost:** $1.50/1,000 images. Very cheap. But the post-processing engineering cost exceeds the benefit.

**Prompt control:** None — it's a deterministic API, not a language model. Cannot give it context about what you're looking for.

**Verdict:** Better OCR, worse understanding. The engineering cost of the post-processing layer exceeds the cost of just using Claude and getting the reasoning for free.

---

### Recommendation: Claude Haiku

**Use `claude-haiku-4-5-20251001`.** Already integrated, zero marginal setup cost, and the combination of vision + language reasoning is exactly what this task needs — you want a model that can say "this partial label says 'Maker' and the bottle shape is bourbon, so this is bourbon" rather than one that returns raw OCR tokens you have to parse yourself. Cost per scan is negligible. The review step mitigates accuracy risk.

---

## 3. Prompt Design

### Structure
Pass the full list of canonical `mapped_ingredient` values to the model so it can perform the mapping in a single pass — avoiding a round-trip between model output and server-side fuzzy matching for most cases.

**System prompt:**
```
You are a bar inventory assistant. Your job is to identify bottles of spirits, liqueurs, mixers, and cocktail ingredients from photos.

The user will send you a photo of their liquor shelf or bar cart. Identify every bottle or ingredient you can see.

You must return ONLY a JSON object in this exact format:
{
  "items": [
    {
      "detected_name": "<what you see on the label or can reasonably infer>",
      "mapped_name": "<best match from the canonical list, or null if none fits>",
      "confidence": "high" | "medium" | "low"
    }
  ]
}

Confidence guidelines:
- "high": you can clearly read the label and are certain of the match
- "medium": you can partially read the label or are inferring from bottle shape/color
- "low": you are guessing; label is obscured or ambiguous

Canonical ingredient list (match mapped_name to one of these exactly, or return null):
<INSERT mapped_ingredient values, comma-separated>

Rules:
- Only include items that are actually visible in the photo
- Do not invent items that are not visible
- If the same bottle appears twice, list it once
- Non-alcoholic mixers (juices, syrups, sodas) should be included if visible
- If you cannot identify any bottles, return {"items": []}
```

**User message:** the image (base64 encoded), with a short text: `"Please identify all the bottles and ingredients you can see."`

### Response Parsing
The model returns pure JSON with no prose. Parse with `json.loads()`. Wrap in try/except — if parsing fails, treat as a recognition failure and return an empty result. The structured format is reliable with Haiku when the system prompt is strict.

### Handling the Canonical List Size
The `ingredients` table's distinct `mapped_ingredient` values fit comfortably within Haiku's context window as a comma-separated string. Fetch and cache alongside the starters cache (1-hour TTL).

---

## 4. Ingredient Matching

### Primary Strategy: Model-Side Mapping
By giving the model the canonical list, most items come back already mapped. A `mapped_name` of `"bourbon"` is looked up directly:
```sql
SELECT ingredient_id FROM ingredients
WHERE lower(mapped_ingredient) = lower(:mapped_name)
LIMIT 1
```

### Fallback: Server-Side Fuzzy Match (pg_trgm)
For cases where the model returns a `mapped_name` not exactly in the DB, run a pg_trgm similarity query:
```sql
SELECT ingredient_id, mapped_ingredient,
       similarity(lower(mapped_ingredient), lower(:candidate)) AS sim
FROM ingredients
WHERE similarity(lower(mapped_ingredient), lower(:candidate)) > 0.4
ORDER BY sim DESC
LIMIT 1
```

A threshold of 0.4 catches "rye whisky" → "rye whiskey" while rejecting nonsense matches. If nothing clears the threshold, the item gets `ingredient_id: null`.

**pg_trgm:** Requires `CREATE EXTENSION IF NOT EXISTS pg_trgm` — a single-line migration. Check if already enabled before adding.

### No Embedding Similarity Needed
Ingredient names are short, structured text where trigram similarity is highly effective. Embeddings would add pgvector infrastructure complexity for negligible accuracy gain over pg_trgm on this problem.

### Unmatched Items
Shown in the review UI in a "Not in our database" section. Each unmatched row shows a "Find it" button that expands an inline ingredient search (reusing the existing `GET /cocktails/ingredients?search=` endpoint), pre-filled with the detected name. When the user selects a result, the row upgrades to a confirmed match and becomes addable. This requires no new backend work — the existing search API handles it entirely.

---

## 5. Backend Design

### New Endpoint

```
POST /api/bar/scan-image
```

- **Auth:** `get_current_user` (required)
- **Content-Type:** `multipart/form-data`
- **Request:** single file field `image`, max 10MB enforced server-side
- **No storage:** image bytes are read into memory, base64-encoded, sent to Claude, then discarded. Nothing persisted.
- **Rate limiting:** 5 scans per user per 10 minutes via Redis key `scan_ratelimit:{user_id}`. If Redis is unavailable, fail open (allow the request) — don't hard-block on optional infrastructure.

### Response Shape

```json
{
  "items": [
    {
      "detected_name": "Maker's Mark Bourbon Whiskey",
      "mapped_name": "bourbon",
      "ingredient_id": 42,
      "confidence": "high",
      "match_method": "exact"
    },
    {
      "detected_name": "Gran Patron Platinum",
      "mapped_name": "tequila",
      "ingredient_id": 8,
      "confidence": "medium",
      "match_method": "fuzzy"
    },
    {
      "detected_name": "Some Obscure Amaro",
      "mapped_name": null,
      "ingredient_id": null,
      "confidence": "low",
      "match_method": "none"
    }
  ]
}
```

`match_method` distinguishes `"exact"` (model returned a canonical name that matched directly), `"fuzzy"` (pg_trgm fallback), and `"none"` (no match). The frontend uses this alongside `confidence` to set appropriate UI state.

### New Service: `backend/services/image_service.py`

Kept separate from `bar_service.py` — different dependency surface (Anthropic SDK vs. DB-heavy bar ops).

Steps:
1. Validate file size and MIME type
2. Fetch distinct `mapped_ingredient` values from DB (cached 1 hour)
3. Build system prompt with canonical list
4. Optionally downscale image to max 1600px longest edge via `Pillow` (keeps token count predictable)
5. Base64-encode image bytes
6. Call `anthropic.messages.create(model="claude-haiku-4-5-20251001", ...)`
7. Parse JSON response
8. For each item: exact DB match → pg_trgm fuzzy fallback → `none`
9. Return structured result

### Error Responses

| Scenario | HTTP |
|---|---|
| File > 10MB | 413 |
| Unsupported MIME type | 415 |
| Rate limit exceeded | 429 |
| Claude API error / timeout | 503 |
| Claude returns unparseable JSON | 200 with `{"items": []}` |
| No bottles detected | 200 with `{"items": []}` |

### New Dependency
`Pillow` — for image resizing before sending to Claude. One new entry in `requirements.txt`. If token cost is acceptable without resizing (it likely is at Haiku prices), this step can be skipped.

---

## 6. Frontend Design

### Upload UI (Idle State)
A dashed-border card in the right column with:
- `Camera` icon (lucide-react)
- Title: "Scan your bar"
- Subtitle: "Take a photo of your shelf — we'll identify the bottles"
- Hidden `<input type="file" accept="image/*" capture="environment" />` triggered by clicking the card

The `capture="environment"` attribute opens the rear camera on mobile; on desktop it shows a file picker. No custom camera UI needed.

### Loading State
The card shows an animated pulse with "Identifying bottles…" while the request is in flight.

### Review UI
Each detected item as a row:
```
[✓]  Maker's Mark Bourbon    →  bourbon    ● High
[✓]  Gran Patron             →  tequila    ◑ Medium
[ ]  Some Obscure Amaro      →  No match   — (disabled)
```

- Green dot = high, pre-checked
- Amber dot = medium, pre-checked (user can deselect)
- Low confidence with a match: pre-unchecked, user can opt in
- No match: row shown, checkbox disabled, grayed out

Items already in the user's bar (checked against the existing `barMappedNames` set in `MyBar.tsx`) are shown with a green check and pre-unchecked — already have it.

Footer: "Add N ingredients to my bar" button → `addToBar.mutateAsync(selectedIds)` via the existing `useAddToBar` hook. "Scan again" link resets to idle state.

### State Machine (local to the scan section)

```typescript
type ScanState =
  | { status: 'idle' }
  | { status: 'uploading' }
  | { status: 'review'; items: ScanResultItem[]; selectedIds: Set<number> }
  | { status: 'error'; message: string }
```

### New Hook

```typescript
// useBar.ts
export function useBarScan() {
  return useMutation({
    mutationFn: (file: File) => barApi.scanImage(file),
  })
}
```

### API Call Note
`barApi.scanImage()` must use a direct `fetch` call with `FormData` — **not** the existing `api.post()` helper, which sets `Content-Type: application/json` and would break multipart upload. The browser must set the Content-Type boundary automatically by omitting the header.

### New Types (`bar.ts`)

```typescript
export type MatchMethod = 'exact' | 'fuzzy' | 'none'
export type Confidence = 'high' | 'medium' | 'low'

export interface ScanResultItem {
  detected_name: string
  mapped_name: string | null
  ingredient_id: number | null
  confidence: Confidence
  match_method: MatchMethod
}

export interface ScanResponse {
  items: ScanResultItem[]
}
```

---

## 7. Complexity, Risks, and Open Questions

### Risks

**1. Model accuracy on real bar photos**
This is the biggest unknown. Poor lighting, reflective surfaces, overlapping bottles, and angled shots are genuinely hard. The review step mitigates this — a bad scan result just means the user adds items manually, which is the current baseline. **Recommendation: test with 10–15 real bar photos before committing to the full frontend build.**

**2. Model hallucination**
Claude may confidently identify a bottle that isn't present (e.g., interesting textures or partially obscured labels triggering a guess). The prompt instruction "only include items actually visible" helps but doesn't eliminate this. The review step is the safety net.

**3. Canonical list in the prompt**
If the `mapped_ingredient` list is very large, verify the model doesn't over-map (returning something from the list rather than null) for genuinely unrecognized items. Needs empirical validation.

**4. Pillow dependency**
New addition to `requirements.txt`. If image resizing turns out unnecessary (Haiku handles large images without meaningful cost increase), skip it.

**5. Rate limiting without Redis**
Redis is optional in this app. Without it, rate limiting is a no-op. At $0.002/call this is low financial risk, but consider an in-process fallback counter for abuse prevention.

**6. multipart/FormData gotcha**
The existing `api` client sets `Content-Type: application/json`. The scan endpoint requires a raw `fetch` with `FormData`. Easy to get wrong — needs explicit documentation in code.

### Decisions

1. **Where on the page?** Above bulk add in the right column, always (not conditional on bar state).

2. **Cap on returned items?** No cap — show all detected items and trust the user to deselect. A long scrollable list is a better outcome than silently dropping bottles.

3. **Quality logging?** Yes — log `{user_id, detected_count, matched_count, timestamp}` on every scan from day one. Cheap to add, valuable for assessing real-world accuracy over time.

4. **Multiple photos?** Out of scope for v1. Prove out the single-image approach first.

---

## 8. Estimated Scope

### Backend

| Task | Effort |
|---|---|
| `POST /api/bar/scan-image` endpoint | 1–2 hrs |
| `image_service.py` — scan function | 3–4 hrs |
| Anthropic API integration + prompt tuning | 1–2 hrs |
| Ingredient matching (exact + pg_trgm fallback) | 2–3 hrs |
| `pg_trgm` migration (if not already enabled) | 30 min |
| Rate limiting | 1–2 hrs |
| Image validation + optional Pillow resizing | 1–2 hrs |
| New Pydantic schemas | 30 min |
| Error handling + logging | 1 hr |
| **Backend total** | **~11–16 hrs** |

### Frontend

| Task | Effort |
|---|---|
| `barApi.scanImage()` with FormData | 1 hr |
| `useBarScan()` hook | 30 min |
| New TypeScript types | 30 min |
| Upload card (idle + loading states) | 2 hrs |
| Review list UI (confidence dots, checkboxes, disabled states) | 3–4 hrs |
| Error + empty states | 1 hr |
| Integration with `useAddToBar` | 30 min |
| Mobile testing (camera capture, touch targets) | 1–2 hrs |
| **Frontend total** | **~9–12 hrs** |

**Total: ~20–28 hours** of implementation. Add 4–6 hours for prompt iteration and real-photo testing.

### Go / No-Go

**Lean go.** The feature directly addresses the highest-friction point in the user journey, uses an already-integrated vendor at negligible cost, requires no custom dataset or new infrastructure, and fails gracefully. The main risk (model accuracy) is bounded and can be evaluated cheaply with a backend-only prototype before committing to the full frontend build.

**Recommended sequence:**
1. Backend service + endpoint — test with Postman and real bar photos, iterate on the prompt
2. Evaluate accuracy with real photos before proceeding
3. Frontend upload + loading state
4. Frontend review UI
5. Mobile testing

---

## Files to Change

| File | Change |
|---|---|
| `backend/services/image_service.py` | **New** — `scan_bar_image()` service function |
| `backend/routers/bar.py` | Add `POST /scan-image` endpoint |
| `backend/schemas.py` | Add `ScanResultItem`, `ScanResponse` |
| `backend/config.py` | Confirm `anthropic_api_key` setting exists |
| `migrations/versions/XXX_enable_pg_trgm.py` | `CREATE EXTENSION IF NOT EXISTS pg_trgm` (if not already enabled) |
| `requirements.txt` | Add `Pillow` (if image resizing needed) |
| `frontend/src/api/bar.ts` | Add `ScanResultItem`, `ScanResponse` types + `barApi.scanImage()` |
| `frontend/src/hooks/useBar.ts` | Add `useBarScan()` |
| `frontend/src/pages/MyBar.tsx` | Add scan section (or extract to `BarScanSection.tsx`) |
