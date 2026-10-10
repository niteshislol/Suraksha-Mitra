import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import "../src/shared/crop-geometry.js";
import { createScreenshotServer, sanitizeName } from "../server/screenshot-server.js";

const G = globalThis.SurakshaMitraGeometry;
const PNG_1PX = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

test("union covers every part (field, label, help text)", () => {
  const box = G.union([G.rect(100, 100, 200, 40), G.rect(100, 70, 120, 20), G.rect(100, 150, 180, 16)]);
  assert.deepEqual(box, { left: 100, top: 70, width: 200, height: 96 });
});
test("extra padding is added on every side", () => {
  const padded = G.pad(G.rect(100, 100, 200, 40), G.EXTRA_PADDING);
  assert.deepEqual(padded, { left: 76, top: 76, width: 248, height: 88 });
});
test("tiny areas are grown around their centre to a legible minimum", () => {
  const grown = G.ensureMin(G.rect(500, 300, 20, 20), G.MIN_W, G.MIN_H);
  assert.equal(grown.width, G.MIN_W); assert.equal(grown.height, G.MIN_H);
  assert.equal(grown.left + grown.width / 2, 510); assert.equal(grown.top + grown.height / 2, 310);
});
test("clamp keeps the crop inside the viewport and returns null when off-screen", () => {
  assert.deepEqual(G.clamp(G.rect(-20, 700, 300, 200), 1000, 800), { left: 0, top: 700, width: 280, height: 100 });
  assert.equal(G.clamp(G.rect(0, 900, 100, 100), 1000, 800), null);
});
test("toPixels handles device-pixel scaling and stays inside the bitmap", () => {
  const px = G.toPixels(G.rect(10.5, 20, 100, 50), 2, 2, 400, 300);
  assert.deepEqual(px, { left: 21, top: 40, width: 200, height: 100 });
  const edge = G.toPixels(G.rect(350, 250, 100, 100), 1, 1, 400, 300);
  assert.equal(edge.left + edge.width <= 400 && edge.top + edge.height <= 300, true);
});
test("wide crops are shrunk but never enlarged", () => {
  assert.equal(G.shrinkFactor(2560, 1280), 0.5);
  assert.equal(G.shrinkFactor(600, 1280), 1);
});
test("sanitizeName makes safe file-name fragments", () => {
  assert.equal(sanitizeName("Upload Passport Size Photo *"), "upload-passport-size-photo");
  assert.equal(sanitizeName("../../etc/passwd"), "etc-passwd");
  assert.equal(sanitizeName(""), "field");
});
test("screenshot helper saves a PNG, rejects non-PNG data and web-page origins", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "sm-shots-"));
  const server = createScreenshotServer({ dir });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const post = (body, headers = {}) => fetch(`${base}/screenshots`, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) });
  try {
    const ok = await post({ image_base64: PNG_1PX, name: "First Name *" });
    assert.equal(ok.status, 200);
    const body = await ok.json();
    assert.match(body.file, /^\d{8}-\d{6}-001-first-name\.png$/);
    assert.equal(fs.existsSync(path.join(dir, body.file)), true);
    assert.equal((await post({ image_base64: Buffer.from("hello").toString("base64") })).status, 400);
    assert.equal((await post({ image_base64: PNG_1PX }, { Origin: "https://evil.example" })).status, 403);
    assert.equal((await fetch(`${base}/health`)).status, 200);
  } finally {
    server.close(); fs.rmSync(dir, { recursive: true, force: true });
  }
});
test("capture crops only the computed area and never the whole page", () => {
  const worker = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  const content = fs.readFileSync(path.join("src", "content", "content-script.js"), "utf8");
  assert.match(worker, /G\.toPixels\(box/);
  assert.doesNotMatch(worker, /rect\.top\) - 180/);          // old hard-coded 180px crop is gone
  assert.match(content, /contextBox\(field\.target\)/);
  assert.match(content, /style\.visibility = "hidden"/);       // panel is hidden during capture
});
test("only typed values are masked, and the mask is placed relative to the crop", () => {
  const worker = fs.readFileSync(path.join("src", "background", "service-worker.js"), "utf8");
  assert.match(worker, /message\.mask && field/);
  assert.match(worker, /field\.left \* scaleX - crop\.left/);
});
test("the manifest loads the geometry module before the content script and allows tab capture", () => {
  const manifest = JSON.parse(fs.readFileSync("manifest.json", "utf8"));
  const js = manifest.content_scripts[0].js;
  assert.equal(js.indexOf("src/shared/crop-geometry.js") < js.indexOf("src/content/content-script.js"), true);
  assert.equal(manifest.host_permissions.includes("<all_urls>"), true);
});
