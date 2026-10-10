// Tiny local helper: receives a PNG crop from the extension and saves it to
// <project>/temp/screenshots. Chrome extensions cannot write to arbitrary
// folders, so this is how crops land in C:\codewithmay1\Hackbios\temp\screenshots.
// No dependencies. Listens on 127.0.0.1 only. Start with:  npm start
import http from "node:http";
import { readFileSync } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
loadEnvFile(path.join(root, ".env"));
const MAX_BODY_BYTES = 8 * 1024 * 1024;
const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
// Priority voices. Hindi is the default language.
const DEFAULT_TTS_LANGUAGE = "hi";
const ELEVENLABS_LANGUAGES = { hi: "hi", bn: "bn", gu: "gu", pa: "pa", en: "en" };
const ELEVENLABS_VOICE_IDS = {
  hi: "IvLWq57RKibBrqZGpQrC",
  bn: "8U6QQz51HQvOsmbnTJ3D",
  gu: "7ffYr49hOtMYH4nvM9BV",
  pa: "TMoHpmi3HTyjpoLh2KMT",
  en: "7wlfJf72PCt9FjPj0Beg"
};

function loadEnvFile(file) {
  try {
    const contents = readFileSync(file, "utf8");
    for (const line of contents.split(/\r?\n/)) {
      const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
      if (!match || match[1] in process.env) continue;
      process.env[match[1]] = match[2].replace(/^(['"])(.*)\1$/, "$2");
    }
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

export function sanitizeName(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40) || "field";
}

export function createScreenshotServer({ dir = path.join(root, "temp", "screenshots") } = {}) {
  const folder = path.resolve(dir);
  let counter = 0;
  const send = (res, status, body) => {
    res.writeHead(status, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" });
    res.end(JSON.stringify(body));
  };
  return http.createServer(async (req, res) => {
    // Only the extension (or a non-browser client such as curl) may write files; ordinary web pages are refused.
    const origin = req.headers.origin;
    if (origin && !origin.startsWith("chrome-extension://")) return send(res, 403, { ok: false, error: "origin not allowed" });
    if (req.method === "OPTIONS") return send(res, 204, {});
    if (req.method === "GET" && req.url === "/health") return send(res, 200, { ok: true, dir: folder });
    if (req.method === "POST" && req.url === "/tts") {
      if (!process.env.ELEVENLABS_API_KEY) return send(res, 503, { ok: false, error: "ELEVENLABS_API_KEY is not configured" });
      try {
        const chunks = []; let size = 0;
        for await (const chunk of req) { size += chunk.length; if (size > 64 * 1024) return send(res, 413, { ok: false, error: "text too large" }); chunks.push(chunk); }
        const payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        const language = ELEVENLABS_LANGUAGES[String(payload.language || DEFAULT_TTS_LANGUAGE)];
        const text = String(payload.text || "").trim();
        if (!language || !text) return send(res, 400, { ok: false, error: "unsupported language or empty text" });
        const voiceId = process.env[`ELEVENLABS_VOICE_ID_${language.toUpperCase()}`] || ELEVENLABS_VOICE_IDS[language] || process.env.ELEVENLABS_VOICE_ID;
        if (!voiceId) return send(res, 503, { ok: false, error: `no ElevenLabs voice configured for ${language}` });
        const modelId = process.env.ELEVENLABS_MODEL_ID || "eleven_multilingual_v2";
        const body = { text, model_id: modelId };
        // ElevenLabs rejects language_code on models that don't support it (e.g. eleven_multilingual_v2).
        if (/^eleven_(turbo|flash)_v2_5$/.test(modelId)) body.language_code = language;
        const eleven = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
          method: "POST",
          headers: { "xi-api-key": process.env.ELEVENLABS_API_KEY, "Content-Type": "application/json", Accept: "audio/mpeg" },
          body: JSON.stringify(body)
        });
        if (!eleven.ok) return send(res, 502, { ok: false, error: `ElevenLabs HTTP ${eleven.status}` });
        const audio = Buffer.from(await eleven.arrayBuffer());
        return send(res, 200, { ok: true, mime_type: "audio/mpeg", audio_base64: audio.toString("base64") });
      } catch { return send(res, 400, { ok: false, error: "bad TTS request" }); }
    }
    if (req.method !== "POST" || req.url !== "/screenshots") return send(res, 404, { ok: false, error: "not found" });
    try {
      const chunks = []; let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > MAX_BODY_BYTES) return send(res, 413, { ok: false, error: "image too large" });
        chunks.push(chunk);
      }
      const payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
      const image = Buffer.from(String(payload.image_base64 || ""), "base64");
      if (image.length < PNG_MAGIC.length || !image.subarray(0, PNG_MAGIC.length).equals(PNG_MAGIC)) return send(res, 400, { ok: false, error: "not a PNG image" });
      await fs.mkdir(folder, { recursive: true });
      const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..*/, "").replace("T", "-");
      const file = `${stamp}-${String(++counter).padStart(3, "0")}-${sanitizeName(payload.name)}.png`; // server-chosen name: no path traversal
      const full = path.join(folder, file);
      await fs.writeFile(full, image, { flag: "wx" });
      return send(res, 200, { ok: true, file, path: full });
    } catch {
      return send(res, 400, { ok: false, error: "bad request" });
    }
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.env.PORT || 8787);
  const dir = process.env.SCREENSHOT_DIR || path.join(root, "temp", "screenshots");
  createScreenshotServer({ dir }).listen(port, "127.0.0.1", () => {
    console.log(`Suraksha Mitra screenshot helper listening on http://127.0.0.1:${port}`);
    console.log(`Saving crops to ${path.resolve(dir)}`);
  });
}
