# Full Report API — Frontend Guide

Generate a combined website-analysis **PDF** from one URL. It runs 6 tools
(PageSpeed, GTmetrix, WAVE accessibility, SSL/TLS, broken links, structured data)
and returns a styled PDF with a recommendations section, in **English or Arabic**.

Base URL: `http://localhost:8000/api/v1` (change per environment).

It's an **async job**: you `POST` to start it, then **poll** a status endpoint until
the PDF is ready, then use the `download_url`.

No auth required for this endpoint.

---

## ⏳ Important: this is a background job — it takes time

The report does **not** come back in the POST response. When you `POST`, the server
only **queues** the work on a background worker (Celery) and immediately returns a
job **`id`** with `status: "pending"`. The actual analysis (6 tools + PDF) then runs
in the background and usually takes **~20–60 seconds** (occasionally more for slow
sites).

So the frontend flow is:

1. **`POST`** the URL → get back the job **`id`** (response is instant, `202`).
2. **Save that `id`** and show a **loading indicator** (spinner / progress).
3. **Poll** `GET /full_report/{id}/` every ~3s while `status` is `pending` or
   `processing` — keep the loader visible.
4. When `status` becomes `completed`, **stop the loader** and use `download_url`.
   If `status` is `failed`, stop the loader and show `error_message`.

> There is no "wait for the PDF" endpoint — you **must** capture the `id` and poll.
> There is no public "list my reports" endpoint either, so **don't lose the `id`**:
> persist it in component state (or the page URL) until the job finishes.

```
POST  ──▶  { id, status: "pending" }        ← instant, save the id + show loader
  │
  └─▶ GET /full_report/{id}/  (repeat ~3s)   ← "pending" / "processing" → keep loading
        │
        └─▶ status: "completed"              ← hide loader, use download_url
```

---

## 1. Start a report

```
POST /api/v1/full_report/
Content-Type: application/json
```

**Body**

| Field | Type | Required | Values | Default |
|---|---|---|---|---|
| `url` | string | ✅ | any public `http(s)` URL | — |
| `strategy` | string | ❌ | `mobile` \| `desktop` | `mobile` |
| `lang` | string | ❌ | `en` \| `ar` | `en` |

```json
{ "url": "https://example.com", "strategy": "desktop", "lang": "en" }
```

**Response `202 Accepted`**

```json
{
  "id": "b1c2...-uuid",
  "status": "pending",
  "status_url": "http://localhost:8000/api/v1/full_report/b1c2...-uuid/"
}
```

Keep the `id` (or the `status_url`) and start polling.

---

## 2. Poll for status

```
GET /api/v1/full_report/{id}/
```

**Response `200 OK`**

```json
{
  "id": "b1c2...-uuid",
  "url": "https://example.com",
  "strategy": "desktop",
  "lang": "en",
  "status": "completed",
  "tools_status": {
    "pagespeed": "ok",
    "gtmetrix": "failed",
    "accessibility": "ok",
    "ssl": "ok",
    "links": "ok",
    "structured_data": "ok"
  },
  "download_url": "http://localhost:8000/media/reports/.../analysis-example-com-en.pdf",
  "error_message": "",
  "created_at": "2026-07-16T09:30:00Z",
  "updated_at": "2026-07-16T09:30:42Z"
}
```

### `status` values
| Status | Meaning | What to do |
|---|---|---|
| `pending` | queued, not started | keep polling |
| `processing` | tools running | keep polling |
| `completed` | PDF ready | use `download_url` ✅ |
| `failed` | job errored | show `error_message` |

Notes:
- `download_url` is `null` until `status` is `completed`.
- `tools_status` reports each tool independently. Each value is one of:
  `"ok"` (ran fine), `"failed"` (errored — e.g. GTmetrix out of credits), or
  `"skipped"` (disabled on the server via config). A `failed` or `skipped` tool
  does **not** fail the whole report — the PDF is still produced, with that
  section marked "Could not run" / "not included".
- Which tools run is a **server setting** (`FULL_REPORT_TOOLS`), not something the
  request controls. If a tool is always `skipped`, it's turned off server-side.
- Poll every **~3 seconds**. A full report typically takes ~20–60s.

---

## 3. Show / download the PDF

`download_url` points to the finished PDF. Open it in a new tab or offer a
download link:

```html
<a :href="downloadUrl" target="_blank" rel="noopener">Download PDF</a>
```

---

## Minimal example (fetch + poll + loading state)

`onStatus` is called on every poll so you can keep a loader on screen (and
optionally show which stage it's in) until the PDF is ready.

```js
const BASE = "http://localhost:8000/api/v1";

async function runFullReport(url, { strategy = "mobile", lang = "en", onStatus } = {}) {
  // 1) start — instant; we only get a job id back, NOT the PDF
  const start = await fetch(`${BASE}/full_report/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, strategy, lang }),
  });
  if (!start.ok) throw new Error("Failed to start report");
  const { id } = await start.json(); // <-- save this id

  // 2) poll until done — keep the loader up while pending/processing
  while (true) {
    const res = await fetch(`${BASE}/full_report/${id}/`);
    const job = await res.json();

    onStatus?.(job.status); // "pending" | "processing" | "completed" | "failed"

    if (job.status === "completed") return job.download_url;
    if (job.status === "failed") throw new Error(job.error_message || "Report failed");

    await new Promise((r) => setTimeout(r, 3000)); // wait 3s, then poll again
  }
}

// usage
let loading = true; // drive your spinner off this
runFullReport("https://example.com", {
  strategy: "desktop",
  lang: "ar",
  onStatus: (s) => console.log("report status:", s), // update UI text if you like
})
  .then((pdfUrl) => window.open(pdfUrl, "_blank"))
  .catch((err) => alert(err.message))
  .finally(() => { loading = false; }); // hide the spinner
```

### React sketch

```jsx
const [loading, setLoading] = useState(false);
const [pdfUrl, setPdfUrl] = useState(null);

async function onGenerate() {
  setLoading(true);
  setPdfUrl(null);
  try {
    const url = await runFullReport(input, { strategy, lang });
    setPdfUrl(url);
  } catch (e) {
    alert(e.message);
  } finally {
    setLoading(false);
  }
}

// {loading && <Spinner label="Generating report… this can take up to a minute" />}
// {pdfUrl && <a href={pdfUrl} target="_blank" rel="noopener">Download PDF</a>}
```

---

## Errors

Validation and other errors use one envelope:

```json
{ "error": "Validation failed.", "extra": { "url": ["Enter a valid URL."] } }
```

| Code | When |
|---|---|
| `400` | bad/missing `url`, invalid `strategy`/`lang`, or localhost URL |
| `404` | unknown report `id` |
| `429` | rate limit hit (submissions are throttled) — retry later |

---

## Quick reference

| Step | Method | Path |
|---|---|---|
| Start report | `POST` | `/api/v1/full_report/` |
| Poll status | `GET` | `/api/v1/full_report/{id}/` |
