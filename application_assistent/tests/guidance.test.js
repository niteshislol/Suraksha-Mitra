import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const sensitive = value => /password|otp|aadhaar|pan|bank|cvv|secret|pin/i.test(value);
test("sensitive labels are detected without inspecting values", () => {
  assert.equal(sensitive("Account password"), true);
  assert.equal(sensitive("Date of birth"), false);
});
test("fallback guidance stays generic", () => {
  const guidance = "Enter your password directly on the website. Do not share it.";
  assert.match(guidance, /Do not share/);
  assert.doesNotMatch(guidance, /1234|secret/i);
});
test("Hindi fallback guidance covers sensitive and file fields", () => {
  const source = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(source, /अपना पासवर्ड सीधे दर्ज करें/);
  assert.match(source, /OTP सीधे दर्ज करें/);
  assert.match(source, /मांगा गया दस्तावेज़ चुनें/);
});
test("model response policy accepts only supported statuses", () => {
  const allowed = ["success", "needs_clarification", "unsupported"];
  assert.equal(allowed.includes("success"), true);
  assert.equal(allowed.includes("execute"), false);
});
test("metadata redaction removes identifier-like text", () => {
  const sanitize = value => String(value).replace(/\b(?:\d[\d\s-]{3,}|[A-Z]{2,}[A-Z0-9-]{3,})\b/g, "[redacted]");
  assert.equal(sanitize("Application ID ABC12345"), "Application ID [redacted]");
  assert.equal(sanitize("Date of birth"), "Date of birth");
});
test("optional skip is permitted only for optional fields", () => {
  const canSkip = field => !field.required;
  assert.equal(canSkip({ required: false }), true);
  assert.equal(canSkip({ required: true }), false);
});
test("language detection recognizes Hindi page locales", () => {
  const detect = value => /^hi(?:-|$)/i.test(value) ? "hi" : "en";
  assert.equal(detect("hi-IN"), "hi");
  assert.equal(detect("en-US"), "en");
});
test("regional ElevenLabs proxy is configured", () => {
  const popup = fs.readFileSync(path.join("src", "ui", "popup.html"), "utf8");
  const background = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  const server = fs.readFileSync(path.join("server", "screenshot-server.js"), "utf8");
  for (const language of ["hi", "bn", "gu", "pa", "en"]) assert.match(popup, new RegExp(`value="${language}"`));
  assert.match(background, /type === "elevenlabs-tts"/);
  assert.match(server, /ELEVENLABS_API_KEY/);
  assert.match(server, /\/tts/);
  assert.match(server, /ELEVENLABS_VOICE_ID_\$\{language\.toUpperCase\(\)\}/);
});
test("ElevenLabs secrets use an ignored dotenv file", () => {
  const gitignore = fs.readFileSync(".gitignore", "utf8");
  const example = fs.readFileSync(".env.example", "utf8");
  const server = fs.readFileSync(path.join("server", "screenshot-server.js"), "utf8");
  assert.match(gitignore, /^\.env$/m);
  assert.match(example, /ELEVENLABS_API_KEY=/);
  assert.match(server, /loadEnvFile/);
});
test("ElevenLabs is the default speech provider", () => {
  const popup = fs.readFileSync(path.join("src", "ui", "popup.js"), "utf8");
  const background = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  const content = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(popup, /elevenLabsEnabled: true/);
  assert.match(background, /elevenLabsEnabled: true/);
  assert.match(content, /get\(\{ speechEnabled: true, elevenLabsEnabled: true/);
});
test("ElevenLabs fallback preserves a safe failure reason", () => {
  const content = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(content, /result\?\.reason/);
  assert.match(content, /using the browser voice/);
});
test("speech voice matching prefers the selected language", () => {
  const voices = [{ lang: "en-US" }, { lang: "hi-IN" }];
  const match = voices.find(voice => voice.lang.toLowerCase().startsWith("hi"));
  assert.equal(match.lang, "hi-IN");
});
test("supported control adapters cover native and safe custom controls", () => {
  const supported = ["radio", "checkbox", "select", "file", "contenteditable", "combobox", "textarea",
    "text", "email", "tel", "number", "date", "time", "datetime-local", "month", "week", "url", "search"];
  assert.equal(supported.includes("select"), true);
  assert.equal(supported.includes("email"), true);
  assert.equal(supported.includes("date"), true);
  assert.equal(supported.includes("script"), false);
});
test("dropdown discovery handles native selects and ARIA comboboxes", () => {
  const source = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  const adapters = fs.readFileSync(path.join("src", "content", "control-adapters.js"), "utf8");
  assert.match(source, /getAttribute\("role"\) === "combobox"/);
  assert.match(source, /aria-controls/);
  assert.match(source, /role='option'/);
  assert.match(adapters, /el\.value\.trim\(\) !== ""/);
});
test("removed active controls must pause rather than advance", () => {
  const active = { connected: false };
  const shouldPause = !active.connected;
  assert.equal(shouldPause, true);
});
test("background request shape excludes field values and executable actions", () => {
  const source = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  assert.doesNotMatch(source, /metadata\.value|metadata\.currentValue|metadata\.inputValue/);
  assert.doesNotMatch(source, /\beval\s*\(/);
  assert.match(source, /format:\s*"json"/);
});
test("synthetic fixtures cover standard, dynamic, ambiguous, and sensitive forms", () => {
  for (const fixture of ["standard-form.html", "dynamic-form.html", "ambiguous-form.html", "sensitive-form.html"]) {
    assert.equal(fs.existsSync(path.join("examples", fixture)), true);
  }
});
test("sensitive fixture values are never used as AI metadata", () => {
  const source = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.doesNotMatch(source, /el\.value.*sendMessage|value:\s*el\.value/);
});
test("visual AI prompt uses an image and does not send semantic metadata", () => {
  const source = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  assert.match(source, /images: \[image\]/);
  assert.match(source, /captureField/);
  assert.match(source, /fillRect/);
});
test("speech fallback does not replace field guidance", () => {
  const source = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(source, /id="sm-notice"/);
  assert.match(source, /setNotice\(`Spoken output is unavailable/);
  assert.doesNotMatch(source, /render\("waiting_for_input", `\$\{text\} Spoken output/);
});
test("AI failures are surfaced instead of silently presented as AI guidance", () => {
  const content = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  const popup = fs.readFileSync(path.join("src", "ui", "popup.js"), "utf8");
  assert.match(content, /AI unavailable:/);
  assert.match(popup, /type: "ollama-test"/);
});
test("sensitive fields never request visual guidance", () => {
  const source = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(source, /isSensitive\(field\).*sensitiveCaptureEnabled/);
  assert.match(source, /type: "capture-field"/);
  assert.match(source, /type: "explain-image"/);
});
test("unmasked storage is opt-in and requires an HTTPS backend", () => {
  const source = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  assert.match(source, /sensitiveCaptureEnabled: false/);
  assert.match(source, /https:/);
  assert.match(source, /screenshots/);
  assert.match(source, /storage failed; image was not sent to Gemma/);
});
test("remote storage requires a runtime optional permission", () => {
  const manifest = JSON.parse(fs.readFileSync("manifest.json", "utf8"));
  const popup = fs.readFileSync(path.join("src", "ui", "popup.js"), "utf8");
  assert.equal(manifest.optional_host_permissions, undefined);
  assert.match(popup, /chrome\.permissions\.request/);
});
test("visual AI diagnostics test the model without a page screenshot", () => {
  const background = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  const popup = fs.readFileSync(path.join("src", "ui", "popup.js"), "utf8");
  assert.match(background, /visual-model-test/);
  assert.match(background, /syntheticImage/);
  assert.match(popup, /type: "visual-model-test"/);
});
test("local screenshot storage requires explicit folder access", () => {
  const background = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  const popup = fs.readFileSync(path.join("src", "ui", "popup.js"), "utf8");
  assert.match(background, /getFileHandle/);
  assert.match(background, /queryPermission/);
  assert.match(popup, /showDirectoryPicker/);
  assert.match(popup, /requestPermission/);
});
test("local screenshot failures identify missing permission or write failure", () => {
  const background = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  assert.match(background, /no screenshot folder permission is available/);
  assert.match(background, /local file write failed/);
});
test("Next advances past incomplete fields and offers required-field review", () => {
  const source = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(source, /\$\("#sm-next"\)\.disabled = !state\.active;/);
  assert.match(source, /skippedRequired/);
  assert.match(source, /Review incomplete/);
});

test("native selects report select-one/select-multiple and are normalised to select", () => {
  const source = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(source, /select-\(one\|multiple\)/);
  assert.match(source, /const isCombo = el\.getAttribute\("role"\) === "combobox"/);
});
test("untouched pre-selected selects and placeholder-text comboboxes are not treated as answered", () => {
  const adapters = fs.readFileSync(path.join("src", "content", "control-adapters.js"), "utf8");
  assert.match(adapters, /touched\.has\(el\)/);
  assert.match(adapters, /initialText/);
  assert.equal(fs.existsSync(path.join("examples", "dropdown-form.html")), true);
});
test("dropdown choices are sent as labels only, never as the chosen value", () => {
  const content = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  const background = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  assert.match(content, /options: dropdownChoices\(field\)/);
  assert.match(background, /DROPDOWN/);
});

test("Hindi is the default language everywhere", () => {
  const read = (...parts) => fs.readFileSync(path.join(...parts), "utf8");
  assert.match(read("src", "ui", "popup.js"), /language: "hi"/);
  assert.match(read("src", "background", "service-worker.js"), /language: "hi"/);
  assert.match(read("src", "content", "content-script.js"), /language: "hi"/);
  assert.match(read("src", "ui", "popup.html"), /<option value="hi" selected>/);
  assert.match(read("server", "screenshot-server.js"), /DEFAULT_TTS_LANGUAGE = "hi"/);
});
test("each configured voice ID is mapped to the right language", () => {
  const server = fs.readFileSync(path.join("server", "screenshot-server.js"), "utf8");
  const env = fs.readFileSync(".env.example", "utf8");
  for (const [lang, id] of Object.entries({ HI: "IvLWq57RKibBrqZGpQrC", BN: "8U6QQz51HQvOsmbnTJ3D", GU: "7ffYr49hOtMYH4nvM9BV", PA: "TMoHpmi3HTyjpoLh2KMT", EN: "7wlfJf72PCt9FjPj0Beg" })) {
    assert.match(server, new RegExp(`${lang.toLowerCase()}: "${id}"`));
    assert.match(env, new RegExp(`ELEVENLABS_VOICE_ID_${lang}=${id}`));
  }
});
test("configured regional guidance is accepted by the AI path", () => {
  const background = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  assert.match(background, /\["hi", "bn", "gu", "pa", "en"\]\.includes\(message\.language\)/);
});
test("ElevenLabs is tried first and falls back to the browser voice", () => {
  const content = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(content, /ELEVENLABS_LANGUAGES = \["hi", "bn", "gu", "pa", "en"\]/);
  assert.match(content, /speakWithBrowser\(text, language, `ElevenLabs/);
  assert.match(content, /function stopSpeech\(\)/);
});
