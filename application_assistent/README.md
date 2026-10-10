# Suraksha Mitra - Form Fill-up Guidance Assistant

A Manifest V3 Chrome extension that explains one form field at a time, featuring **premium, human-like multi-lingual voice guidance powered by ElevenLabs**. It never fills, clicks, authenticates, bypasses CAPTCHA/OTP, or submits a form.

### 🎙 Powered by ElevenLabs
This extension utilizes **ElevenLabs' state-of-the-art Text-to-Speech (TTS)** API to provide natural and accessible voice instructions to users in multiple regional languages (Hindi, Bengali, Gujarati, Punjabi, and English). The integration ensures a high-quality, ultra-realistic voice experience that guides users step-by-step through complex forms.

## Install

1. Copy `.env.example` to `.env`, add your ElevenLabs API key, then run `npm start`. The local screenshot/TTS helper saves crops into `temp\screenshots` (leave it running). The `.env` file is ignored by Git.
2. Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked** and select this project folder.
3. If your form is a local file (`file:///...`), open the extension's **Details** and turn on **Allow access to file URLs**.
4. For the cloud model, run `ollama signin` once, then confirm `gemma4:31b-cloud` is listed by Ollama.
5. Open a form (try `examples\admission-form.html`) and click the green `स` orb.

No build step or runtime dependency is required. Run `npm test` for the automated policy tests.

### ElevenLabs `.env` setup

In PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
npm start
```

Set `ELEVENLABS_API_KEY` to your secret key. Never put the key in the extension files or commit `.env`.

The enabled languages and configured ElevenLabs voices are:

| Language | Voice ID |
| --- | --- |
| Hindi | `IvLWq57RKibBrqZGpQrC` |
| Bengali | `8U6QQz51HQvOsmbnTJ3D` |
| Gujarati | `7ffYr49hOtMYH4nvM9BV` |
| Punjabi | `TMoHpmi3HTyjpoLh2KMT` |
| English | `7wlfJf72PCt9FjPj0Beg` |

ElevenLabs is tried first for these languages; if it is unreachable or fails, the extension falls back to the matching browser voice. Hindi remains the default.

## Features and architecture

- `src/content/content-script.js` discovers visible native and ARIA controls in DOM order, highlights one field, tracks local completion, and requires an explicit Next click.
- `src/content/control-adapters.js` provides control-specific completion checks for radios, checkboxes, selects, file inputs, contenteditable areas, and native text controls.
- Fallback guidance is used for sensitive fields and AI failures.
- `src/background/service-worker.js` sends sanitized metadata only to the configured Ollama `/api/generate` endpoint. Field values are never included.
- **ElevenLabs Text-to-Speech Integration**: ElevenLabs is the default, primary voice provider, ensuring high-fidelity voice instructions. A local backend (`screenshot-server.js`) proxies requests to the ElevenLabs API, keeping your API keys secure and outside the Chrome extension.
- Browser `SpeechSynthesis` is used locally only as a seamless fallback if the ElevenLabs network is unreachable.
- The available guidance languages are Hindi, Bengali, Gujarati, Punjabi, and English.
- Guidance uses a screenshot-only visual context path. For the active field, `src/shared/crop-geometry.js` works out the smallest useful area from the page layout: the field, its label and help text, the layout container that holds only that field (for example the photo-preview box next to a file input), and the section heading when the field is the first one under it. 24 px of extra margin is added on every side, and the field is outlined in orange so Gemma knows what to explain. Only that crop is captured, never the full page.
- The floating panel is hidden while the capture is taken, the page is scrolled (instantly, not smoothly) only if the area is partly off-screen, and the crop is shrunk to at most 1280 px wide.
- A value the user has already typed is masked locally, aligned to the field inside the crop. Empty fields are not masked, so Gemma can read the label, placeholder and instructions. DOM metadata is used locally for tracking (and for the crop file name) but is not sent to the LLM.
- Guidance follows the user: clicking or tabbing into another field switches to it, and a late answer for a field the user already left is discarded. The user can always press Next without completing a field; required fields left empty are offered for review at the end. The extension never fills or submits anything.
- Radio groups are treated as one field (the whole group is outlined and cropped).
- Unmasked capture/storage is disabled by default. It is available only as an explicit opt-in with an HTTPS backend URL; the crop is uploaded to `POST <backend>/screenshots` before it is sent to Gemma. Passwords and other sensitive controls remain blocked unless the user explicitly enables this mode.
- `src/ui/popup.html` configures language, speech, Ollama URL/model, and local-only mode.

The default model is `gemma4:31b-cloud`, with `http://127.0.0.1:11434` as the Ollama endpoint. Install/configure Ollama separately and confirm the model is available. Cloud-backed Ollama models may require network access. Local-only mode makes no AI request and uses deterministic fallback text.

## Permissions and privacy

`storage` stores preferences. `<all_urls>` host access is needed because `captureVisibleTab` only works with it (clicking the in-page orb does not grant `activeTab`); a capture happens only after the user starts guidance, and only a small crop of the active field is used. The extension does not collect history, analytics, cookies, page values, credentials, or telemetry. Page labels are untrusted metadata; model output is treated as text and never executed.

## Supported controls and limitations

Visible text/email/tel/number/date/time inputs, textareas, selects, file inputs, contenteditable elements, and basic ARIA radio/checkbox/combobox controls are best-effort supported. Complex widgets, cross-origin iframes, server-only validation, and inaccessible controls may pause guidance. A repeated or unclear label receives a clarification message rather than an invented explanation.
Dynamic page changes are debounced and the active control is revalidated before advancing; removed or unsupported controls pause instead of being silently skipped.

## Development and tests

This project intentionally has no bundler or runtime dependency. The extension files are loaded directly by Chrome. Run:

```text
npm test
node --check src\content\control-adapters.js
node --check src\content\content-script.js
node --check src\background\service-worker.js
node --check src\ui\popup.js
```

The tests cover sensitive-field policy, metadata redaction, model response policy, language selection, adapter coverage, stale controls, source-level privacy checks, and fixture presence.

## Final Chrome verification procedure

1. Run the commands above and confirm all tests pass.
2. Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked**, and select `C:\codewithmay1\Hackbios`.
3. Open `examples\standard-form.html` in Chrome. Click the orb; verify one field is outlined, guidance is shown, and the form is not modified automatically.
4. Leave the required name empty and click **Next**. Confirm progression is blocked. Enter synthetic data, then confirm the explicit **Next** action advances.
5. Confirm the optional PIN field can be skipped and the file control remains user-operated.
6. Open `examples\dynamic-form.html`, change Category, and verify the newly created field is discovered without losing the session.
7. Open `examples\ambiguous-form.html` and verify repeated labels receive a clarification message.
8. Open `examples\sensitive-form.html` and confirm fallback guidance is used. Never use real credentials or OTPs.
9. In the popup, enable **Local-only** and verify the flow still works without an Ollama service.
10. For Ollama, configure the endpoint and model, confirm the service is reachable, and inspect only non-sensitive request metadata. Do not paste credentials into fixtures.

## Ollama configuration

The default endpoint is `http://127.0.0.1:11434` and the default model is `gemma4:31b-cloud`. Ollama must expose its `/api/generate` endpoint and the configured model must be available. The extension sends a JSON request with `stream: false` and `format: "json"`. The request times out after 45 seconds. A timeout, empty reply or non-2xx response uses local fallback guidance, and the reason is shown in the panel. Local-only mode returns before making any model request and never silently falls back to cloud.

For visual assist, the request also includes one locally cropped PNG image, with the language to answer in. It is not a full-page screenshot. Because the configured model may be cloud-backed, users who do not want any image leaving the machine must enable Local-only mode.

The default permissions authorize Ollama endpoints and visible-tab capture for the active crop. Enabling sensitive screenshot storage prompts for an optional permission for the specific configured HTTPS backend origin; do not approve it unless you control and trust that backend.

### Sensitive screenshot storage contract

The optional backend must accept JSON at `POST /screenshots`:

```json
{"image_base64":"...","content_type":"image/png","captured_at":"2026-01-01T00:00:00.000Z"}
```

The backend is responsible for authentication, encryption at rest, access control, retention limits, deletion, audit logging, and HTTPS certificate validation. The extension does not include credentials or implement a server-side delete operation.

### Local screenshot folder

Chrome extensions cannot write to an arbitrary folder such as `C:\codewithmay1\Hackbios\temp\screenshots`, so `server/screenshot-server.js` (no dependencies) does it. Run `npm start`; it listens on `127.0.0.1:8787` only, accepts PNG data only from the extension, and saves files named like `20261009-160211-001-upload-passport-size-photo.png`. Use **Test screenshot helper** in the popup to check it. Set `SCREENSHOT_DIR` to save elsewhere.

A failed save never blocks guidance; the panel shows the saved path, or why the crop was not saved. As a fallback you can still pick a folder in the popup (**Choose screenshot folder**).

## Roadmap and known limitations

Implemented: user-triggered orb, local validation, explicit progression, fallback guidance, English/Hindi speech selection, metadata minimization, dynamic rescanning, adapters, and security-oriented tests.

Not implemented: speech recognition, autofill, automatic portal submission, CAPTCHA/OTP/eKYC bypass, cross-origin iframe inspection, universal custom-widget support, server-side validation, and live-portal compatibility guarantees. These are intentionally excluded for safety or browser security reasons.
