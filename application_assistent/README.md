# Suraksha Mitra - Application Assistant

Suraksha Mitra is a privacy-conscious Chrome extension that explains online application forms one field at a time. It helps people understand what a form is asking for without filling fields, clicking controls, bypassing security checks, or submitting anything on the user's behalf.

> **Safety principle:** the user remains in control of every form action.

## What it does

- Detects visible form controls in page order.
- Highlights the current field and explains its purpose.
- Supports text, email, telephone, number, date, time, textarea, radio, checkbox, select, file, contenteditable, and common ARIA controls.
- Handles native dropdowns and many custom comboboxes.
- Provides deterministic fallback guidance for sensitive or unsupported fields.
- Offers guidance in Hindi, Bengali, Gujarati, Punjabi, and English.
- Uses ElevenLabs for speech when enabled, with the browser's local speech engine as a fallback.
- Can use Ollama/Gemma for visual and contextual explanations.
- Keeps the extension UI and form progression explicit: it never auto-fills or auto-submits a form.

## Project structure

```text
application_assistent/
├── examples/                  # Safe local demo forms
├── server/
│   └── screenshot-server.js    # Local screenshot storage and ElevenLabs proxy
├── src/
│   ├── background/             # Chrome service worker and AI requests
│   ├── content/               # Field discovery, guidance, speech, controls
│   ├── shared/                # Shared crop and geometry helpers
│   └── ui/                    # Extension popup and settings
├── tests/                     # Node's built-in test suite
├── .env.example               # Safe environment-variable template
├── manifest.json              # Manifest V3 configuration
└── package.json               # Scripts; no runtime dependencies
```

## Requirements

- Google Chrome or a Chromium-based browser with Manifest V3 support.
- Node.js 18 or newer for the local helper and tests.
- Optional: [Ollama](https://ollama.com/) for AI-generated explanations.
- Optional: an ElevenLabs API key for spoken guidance.

## Installation

### 1. Load the extension

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Select **Load unpacked**.
4. Choose this `application_assistent` folder.
5. If testing a local HTML file, open the extension's **Details** page and enable **Allow access to file URLs**.

There is no bundler and no build step. The browser loads the source files directly.

### 2. Install project dependencies

The project intentionally has no declared runtime dependencies. Running `npm install` creates or verifies the lockfile:

```powershell
npm install
```

## ElevenLabs voice setup

The extension keeps the ElevenLabs API key in the local Node.js helper rather than exposing it to extension pages.

```powershell
Copy-Item .env.example .env
notepad .env
npm start
```

Set `ELEVENLABS_API_KEY` in `.env`. Keep `.env` private; it is ignored by Git and must never be committed.

The default voice configuration is:

| Language | Code | Voice |
| --- | --- | --- |
| Hindi | `hi` | `IvLWq57RKibBrqZGpQrC` |
| Bengali | `bn` | `8U6QQz51HQvOsmbnTJ3D` |
| Gujarati | `gu` | `7ffYr49hOtMYH4nvM9BV` |
| Punjabi | `pa` | `TMoHpmi3HTyjpoLh2KMT` |
| English | `en` | `7wlfJf72PCt9FjPj0Beg` |

The helper listens only on `http://127.0.0.1:8787`. The extension calls:

```text
Chrome extension -> service worker -> local helper -> ElevenLabs -> audio
```

The helper reads `.env` at startup. Restart `npm start` after changing environment values.

## Ollama setup

The default Ollama endpoint is:

```text
http://127.0.0.1:11434
```

The default model is `gemma4:31b-cloud`. Install Ollama separately, sign in if required by the selected model, and make sure the model is available before enabling AI guidance.

The extension sends only the active field's cropped visual context and non-sensitive guidance metadata. It does not send the full page or the user's field values. **Local-only** mode disables AI requests and uses deterministic fallback guidance.

## Using the extension

1. Open one of the forms in `examples/`, or open a compatible web form.
2. Click the green `स` floating button.
3. Select a guidance language in the extension popup.
4. Review the highlighted field and its explanation.
5. Enter information yourself, then use **Next** when you are ready.
6. Use the popup to configure speech, Ollama, local-only mode, and screenshot options.

The assistant may ask for clarification when labels are repeated or ambiguous. It can pause when a control is removed, inaccessible, inside a cross-origin iframe, or not safely identifiable.

## Privacy and security

- The extension does not collect browsing history, cookies, analytics, telemetry, credentials, or form submissions.
- It never fills, clicks, authenticates, bypasses CAPTCHA/OTP, or submits forms.
- Passwords, OTPs, PINs, and similar sensitive controls use safe fallback guidance by default.
- Typed values are masked locally before an allowed visual request.
- Only a small crop around the active field is captured; the full page is not captured.
- Unmasked screenshot capture is disabled by default and requires an explicit opt-in plus an HTTPS backend that the user controls.
- The ElevenLabs key stays in the local helper and is not stored in extension settings or source files.
- Treat any AI response as explanatory text, not as an instruction to perform an unsafe action.

Do not use real credentials, identity documents, OTPs, or other private information in the example forms or during testing.

## Development and tests

Run the automated tests:

```powershell
npm test
```

Run JavaScript syntax checks:

```powershell
node --check src\content\control-adapters.js
node --check src\content\content-script.js
node --check src\background\service-worker.js
node --check src\ui\popup.js
node --check server\screenshot-server.js
```

The tests cover field policy, sensitive-data redaction, fallback guidance, language selection, dropdown adapters, stale controls, source-level privacy checks, and the local helper.

## Troubleshooting

### ElevenLabs is unavailable

- Confirm `npm start` is still running.
- Confirm `.env` contains a valid `ELEVENLABS_API_KEY`.
- Restart the helper after changing `.env`.
- Check `http://127.0.0.1:8787/health`.
- The extension automatically falls back to the browser speech engine when ElevenLabs cannot be reached.

### AI guidance is unavailable

- Check that Ollama is running at the configured URL.
- Confirm the selected model is installed and available.
- Enable **Local-only** to use the extension without Ollama.

### A local example page cannot be inspected

Open `chrome://extensions`, select the extension's **Details**, and enable **Allow access to file URLs**. Reload the example page afterward.

## License and contribution

This project is part of the Suraksha Mitra repository. Before contributing, preserve the core safety guarantees: do not add automatic form completion, automatic submission, credential collection, or secret values to source control.
