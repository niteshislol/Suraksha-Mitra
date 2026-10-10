(() => {
  const fallback = {
    name: "Enter your name as requested by the form.", "date of birth": "Enter your date of birth in the format requested by the form.",
    email: "Enter an email address you can access.", phone: "Enter your phone number using the format shown.",
    pin: "Enter the postal PIN code requested by the form.", address: "Enter the address requested in this field.",
    password: "Enter your password directly on the website. Do not share it.", otp: "Enter the OTP directly on the website. Do not share it.",
    file: "Choose the requested document from your device.", radio: "Select the option that best matches your information.",
    checkbox: "Select the options that apply to you."
  };
  const hindiFallback = {
    name: "फॉर्म के अनुसार अपना नाम दर्ज करें।", "date of birth": "फॉर्म में दिए गए प्रारूप के अनुसार अपनी जन्मतिथि दर्ज करें।",
    email: "ऐसा ईमेल पता दर्ज करें जिसे आप इस्तेमाल कर सकते हैं।", phone: "दिए गए प्रारूप के अनुसार अपना फोन नंबर दर्ज करें।",
    pin: "फॉर्म में मांगा गया पिन कोड दर्ज करें।", address: "इस फ़ील्ड में मांगा गया पता दर्ज करें।",
    password: "वेबसाइट पर अपना पासवर्ड सीधे दर्ज करें। इसे किसी के साथ साझा न करें।",
    otp: "वेबसाइट पर OTP सीधे दर्ज करें। इसे किसी के साथ साझा न करें।",
    file: "अपने डिवाइस से मांगा गया दस्तावेज़ चुनें।",
    radio: "अपने लिए सही विकल्प चुनें।", checkbox: "लागू होने वाले विकल्प चुनें।"
  };
  const languageNames = { hi: "Hindi", bn: "Bengali", gu: "Gujarati", pa: "Punjabi", en: "English" };
  const CONTROLS = "input, textarea, select, [contenteditable='true'], [role='combobox'], [role='radio'], [role='checkbox']";
  const state = { status: "idle", fields: [], index: -1, active: null, settings: {}, skippedRequired: [], token: 0 };
  const orb = document.createElement("button"); orb.id = "sm-orb"; orb.textContent = "स"; orb.title = "Start Suraksha Mitra guidance"; orb.setAttribute("aria-label", "Start Suraksha Mitra guidance");
  const panel = document.createElement("section"); panel.id = "sm-panel"; panel.hidden = true; panel.setAttribute("aria-live", "polite");
  panel.innerHTML = `<div id="sm-status"></div><p id="sm-guidance"></p><p id="sm-notice" role="status" hidden></p><p id="sm-saved" hidden></p><button id="sm-replay">Replay</button><button id="sm-pause">Pause</button><button id="sm-stop">Stop</button><button id="sm-skip">Skip optional</button><button id="sm-review" hidden>Review incomplete</button><button id="sm-next" class="primary">Next</button>`;
  document.documentElement.append(orb, panel);
  const $ = id => panel.querySelector(id);
  orb.addEventListener("click", () => state.status === "idle" || state.status === "completed" ? start() : togglePause());
  $("#sm-replay").addEventListener("click", () => speak($("#sm-guidance").textContent));
  $("#sm-pause").addEventListener("click", togglePause);
  $("#sm-stop").addEventListener("click", stop);
  $("#sm-skip").addEventListener("click", () => advance(true));
  $("#sm-next").addEventListener("click", () => advance(false));
  $("#sm-review").addEventListener("click", reviewIncomplete);
  document.addEventListener("input", updateCompletion, true); document.addEventListener("change", updateCompletion, true);

  // Follow the user: if they click or Tab into a different field, explain that one instead.
  let focusTimer;
  document.addEventListener("focusin", event => {
    if (["idle", "completed", "paused"].includes(state.status) || panel.contains(event.target)) return;
    const target = event.target;
    const field = state.fields.find(f => f.el === target || (f.type === "radio" && target.type === "radio" && f.el.name && f.el.name === target.name));
    if (!field || (state.active && field.el === state.active.el)) return;
    clearTimeout(focusTimer);
    focusTimer = setTimeout(() => { if (window.SurakshaMitraAdapters?.supports(field)) showField(field); }, 250);
  }, true);

  let rescanTimer;
  const observer = new MutationObserver(() => {
    if (state.status === "idle" || state.status === "completed") return;
    clearTimeout(rescanTimer);
    rescanTimer = setTimeout(() => {
      state.fields = discoverFields();
      if (state.active) {
        const same = state.fields.find(f => f.el === state.active.el);
        if (same) { state.active = same; state.index = state.fields.indexOf(same); }
      }
      if (state.active && !document.contains(state.active.el)) {
        state.active = null;
        render("unsupported", "The current field changed or disappeared. Review the updated page before continuing.");
      }
    }, 150);
  });
  observer.observe(document.body, { childList: true, subtree: true });
  chrome.storage.local.get({ speechEnabled: true, elevenLabsEnabled: true, localOnly: false, language: "hi" }).then(settings => { state.settings = settings; });

  async function start() { state.status = "scanning"; panel.hidden = false; state.fields = discoverFields(); state.index = -1; state.skippedRequired = []; await advance(false); }

  // The user may leave a field at any time; required fields left empty are remembered for review.
  function leave(field) {
    const validSelect = field.el.tagName === "SELECT" && field.el.value !== "";
    if (!isComplete(field) && !validSelect && field.required && !state.skippedRequired.some(f => f.el === field.el)) state.skippedRequired.push(field);
    field.target.classList.remove("sm-active-field");
  }

  async function advance(skip) {
    if (state.active && !document.contains(state.active.el)) return render("unsupported", "The current field changed or disappeared. Review the updated page before continuing.");
    if (state.active) leave(state.active);
    state.fields = discoverFields();
    let next = state.fields.slice(state.index + 1).find(field => !isComplete(field));
    if (!next) {
      state.status = "completed"; state.active = null; state.token++;
      const count = state.skippedRequired.filter(field => !isComplete(field)).length;
      $("#sm-review").hidden = count === 0;
      const message = count ? `Guidance complete. ${count} required field${count === 1 ? "" : "s"} still need attention.` : "Guidance complete. Review the form and submit it yourself.";
      speak(message); return render("completed", message);
    }
    if (!window.SurakshaMitraAdapters?.supports(next)) {
      state.index = state.fields.indexOf(next); state.active = next; next.target.classList.add("sm-active-field");
      return render("unsupported", "This control is not supported safely. Complete it manually, then select Next, or stop guidance.");
    }
    await showField(next);
  }

  async function showField(field) {
    const token = ++state.token;
    stopSpeech();
    if (state.active && state.active.el !== field.el) leave(state.active);
    state.index = state.fields.findIndex(f => f.el === field.el); state.active = field; field.target.classList.add("sm-active-field");
    setNotice(""); setSaved("");
    state.status = "explaining"; render("explaining", "Looking at this field...");
    const guidance = localGuidance(field);
    const result = await requestGuidance(field, token);
    if (token !== state.token) return; // the user moved on while Gemma was working
    const text = result?.status === "success" ? result.display_guidance : guidance;
    if (result?.status === "unavailable") setNotice(`AI unavailable: ${result.reason || "using local fallback guidance."}`);
    else if (result?.status === "fallback") setNotice("Using local fallback guidance.");
    if (result?.status === "needs_clarification" || result?.status === "unsupported") return render("unsupported", "This field needs your review before continuing.");
    render("waiting_for_input", text); speak(text);
  }

  function discoverFields() {
    const radioGroups = new Set();
    const elements = [...document.querySelectorAll(CONTROLS)].filter(el => {
      const type = (el.type || "").toLowerCase();
      const isCombo = el.getAttribute("role") === "combobox";   // custom dropdowns are often <input readonly> or <button role="combobox">
      if (el.disabled || (el.readOnly && !isCombo) || type === "hidden" || !isVisible(el) || (!isCombo && /submit|button|reset|captcha/i.test(`${type} ${el.getAttribute("aria-label") || ""}`))) return false;
      if (type === "radio" && el.name) { if (radioGroups.has(el.name)) return false; radioGroups.add(el.name); } // one guidance per radio group
      return true;
    });
    return elements.map((el, i, all) => {
      const label = labelFor(el); const group = el.getAttribute("role") === "radio" || el.getAttribute("role") === "checkbox";
      const type = group ? el.getAttribute("role") : (el.getAttribute("role") === "combobox" ? "combobox" : (el.isContentEditable ? "contenteditable" : (el.type || el.tagName).toLowerCase().replace(/^select-(one|multiple)$/, "select")));
      return {
        el,
        target: highlightTarget(el),
        label,
        required: el.required || el.getAttribute("aria-required") === "true",
        type,
        helpText: helpFor(el),
        options: dropdownOptions(el, type),
        repeated: all.filter(x => labelFor(x).toLowerCase() === label.toLowerCase()).length > 1
      };
    });
  }
  function dropdownOptions(el, type) {
    if (type === "select") return [...el.options].filter(option => option.value !== "" && !option.disabled).map(option => clean(option.textContent)).filter(Boolean).slice(0, 20);
    if (el.list) return [...el.list.options].map(option => clean(option.value || option.textContent)).filter(Boolean).slice(0, 20); // <input list="...">
    if (type !== "combobox") return [];
    const controls = el.getAttribute("aria-controls") || el.getAttribute("aria-owns");
    const list = controls ? document.getElementById(controls) : null;
    return [...(list || el.parentElement || document).querySelectorAll("[role='option'], option")].map(option => clean(option.textContent)).filter(Boolean).slice(0, 20);
  }
  // For a radio group, outline and crop the whole group, not just its first button.
  function highlightTarget(el) {
    if ((el.type || "").toLowerCase() !== "radio" || !el.name) return el;
    const radios = [...document.querySelectorAll(`input[type="radio"][name="${CSS.escape(el.name)}"]`)].filter(isVisible);
    for (let node = el.parentElement; node && node !== document.body; node = node.parentElement) {
      if (radios.every(radio => node.contains(radio))) { const r = node.getBoundingClientRect(); return r.width <= 900 && r.height <= 300 ? node : el; }
    }
    return el;
  }
  function labelFor(el) {
    const labelled = el.getAttribute("aria-label"); if (labelled) return clean(labelled);
    if ((el.type || "").toLowerCase() === "radio") { const legend = el.closest("fieldset")?.querySelector("legend"); if (legend) return clean(legend.textContent); }
    if (el.labels?.[0]) return clean(el.labels[0].textContent);
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return clean(l.textContent); }
    return clean(el.getAttribute("placeholder") || el.name || el.type || "form field");
  }
  function helpFor(el) {
    const ids = (el.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
    const described = ids.map(id => document.getElementById(id)?.textContent || "").join(" ");
    const parent = el.closest("label, fieldset, section, div");
    const nearby = parent?.querySelector("small, .help, [class*='help'], [role='note']")?.textContent || "";
    return clean(`${described} ${nearby}`).slice(0, 240);
  }
  function isVisible(el) { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
  function isComplete(field) { return Boolean(window.SurakshaMitraAdapters?.get(field).isComplete(field)); }
  function updateCompletion() { if (state.active) { const ready = isComplete(state.active); $("#sm-next").disabled = false; if (ready) render("ready_to_continue", "Ready. Select Next when you are satisfied."); } }
  function localGuidance(field) {
    const text = `${field.label} ${field.type} ${field.helpText || ""}`.toLowerCase();
    const key = Object.keys(fallback).find(k => text.includes(k));
    const language = resolveLanguage();
    if (language === "hi") {
      if (field.options.length) return `अपने लिए सही विकल्प चुनें। उपलब्ध विकल्पों में ये शामिल हैं: ${field.options.slice(0, 5).join(", ")}।`;
      return fallback[key] || (field.repeated ? "This label appears more than once. Confirm which information this field requests." : field.helpText || "Enter the information requested by this field. Review the page instructions before continuing.");
    }
    if (field.options.length) return `अपने लिए सही विकल्प चुनें। उपलब्ध विकल्पों में ये शामिल हैं: ${field.options.slice(0, 5).join(", ")}।`;
    return hindiFallback[key] || (field.repeated ? "यह लेबल एक से अधिक बार है। आगे बढ़ने से पहले सही फ़ील्ड की पुष्टि करें।" : "इस फ़ील्ड में मांगी गई जानकारी दर्ज करें। आगे बढ़ने से पहले पेज के निर्देश पढ़ें।");
  }

  const settle = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 120))));
  function hasEnteredValue(el) {
    const type = (el.type || "").toLowerCase();
    if (["checkbox", "radio", "button", "submit"].includes(type)) return false;
    if (type === "file") return el.files?.length > 0;
    if (el.isContentEditable) return Boolean(el.textContent?.trim());
    return Boolean(el.value);
  }

  // Works out the crop for ONLY this field (+label, help, heading, extra padding), then asks the
  // service worker to capture and save it. Our own panel is hidden so it never appears in the crop.
  async function captureContext(field) {
    const G = window.SurakshaMitraGeometry;
    let ctx = G.contextBox(field.target);
    if (ctx.clipped) { // part of the area is off-screen: bring it to the middle, then measure again
      field.target.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
      await settle(); ctx = G.contextBox(field.target);
    }
    if (!ctx.box) return { status: "unavailable", reason: "the field is not visible on screen" };
    const hidden = [orb, panel];
    hidden.forEach(node => { node.style.visibility = "hidden"; });
    try {
      await settle();
      return await chrome.runtime.sendMessage({
        type: "capture-field",
        box: ctx.box,
        field: ctx.field,
        mask: hasEnteredValue(field.el),
        name: field.label,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight
      });
    } catch {
      return { status: "unavailable", reason: "the extension could not contact its service worker" };
    } finally {
      hidden.forEach(node => { node.style.visibility = ""; });
    }
  }

  async function requestGuidance(field, token) {
    const settings = { ...(await chrome.storage.local.get({ language: "hi", speechEnabled: true, elevenLabsEnabled: true, localOnly: false, sensitiveCaptureEnabled: false })), ...state.settings };
    if (settings.localOnly) return { status: "fallback", reason: "local-only mode is enabled" };
    if (isSensitive(field) && !settings.sensitiveCaptureEnabled) return { status: "fallback", reason: "sensitive fields use local guidance" };
    if (settings.sensitiveCaptureEnabled) setNotice("Sensitive capture is enabled: this field crop will be stored in your configured backend and sent to Gemma.");
    render("explaining", "Capturing this field...");
    const shot = await captureContext(field);
    if (token !== state.token) return null;
    if (shot?.status !== "success") return shot || { status: "unavailable", reason: "field crop could not be captured" };
    if (shot.savedAs) setSaved(`Saved crop: ${shot.savedAs}`);
    else if (shot.saveWarning) setSaved(`Crop not saved: ${shot.saveWarning}`);
    render("explaining", "Asking Gemma about this field...");
    return chrome.runtime.sendMessage({ type: "explain-image", image: shot.image, language: resolveLanguage(), options: dropdownChoices(field) })
      .catch(() => ({ status: "unavailable", reason: "the extension could not contact its service worker" }));
  }
  // A closed dropdown only shows its current text in the screenshot, so also tell the model which
  // choices exist. These are the page's option labels, never what the user selected or typed.
  function dropdownChoices(field) {
    return (field.options || []).slice(0, 20);
  }
  // Whole-word matching, so "Company" or "Shipping address" are not mistaken for PAN / PIN.
  function isSensitive(field) {
    const text = `${field.label} ${field.type}`;
    if (/postal|zip|area|residential|pin ?code/i.test(text) && !/password|otp|cvv|atm/i.test(text)) return false;
    return /\b(password|passcode|otp|one[- ]?time|aadhaar|aadhar|pan|bank account|account (number|no)|cvv|secret|pin)\b/i.test(text);
  }
  function render(status, text) { state.status = status; $("#sm-status").textContent = status.replaceAll("_", " "); $("#sm-guidance").textContent = text; $("#sm-next").disabled = !state.active; $("#sm-skip").hidden = !state.active || state.active.required; if (status !== "completed") $("#sm-review").hidden = true; }
  function reviewIncomplete() {
    const field = state.skippedRequired.find(item => !isComplete(item));
    if (!field) return render("completed", "All required fields are complete. Review the form and submit it yourself.");
    state.fields = discoverFields(); state.index = state.fields.findIndex(f => f.el === field.el) - 1; state.active = null; state.status = "waiting_for_input"; advance(false);
  }
  function togglePause() { if (state.status === "paused") { state.status = "waiting_for_input"; render(state.status, $("#sm-guidance").textContent); } else if (state.status !== "idle" && state.status !== "completed") { stopSpeech(); render("paused", "Paused. Resume when you are ready."); state.status = "paused"; } }
  function stop() { stopSpeech(); state.token++; if (state.active) state.active.target.classList.remove("sm-active-field"); state.active = null; state.index = -1; state.status = "idle"; panel.hidden = true; }
  // Priority voices: ElevenLabs (Hindi default, English, Bengali, Punjabi, Gujarati). Browser speech is the fallback.
  const ELEVENLABS_LANGUAGES = ["hi", "bn", "gu", "pa", "en"];
  let currentAudio = null;
  let speechRun = 0;
  function stopSpeech() {
    speechRun++;
    window.speechSynthesis?.cancel();
    if (currentAudio) { currentAudio.pause(); currentAudio.removeAttribute("src"); currentAudio = null; }
  }
  function speak(text) {
    if (!text || (!state.settings.speechEnabled && state.settings.speechEnabled !== undefined)) return;
    stopSpeech();
    const language = resolveLanguage();
    if (state.settings.elevenLabsEnabled && ELEVENLABS_LANGUAGES.includes(language)) return speakWithElevenLabs(text, language);
    speakWithBrowser(text, language);
  }
  async function speakWithElevenLabs(text, language) {
    const run = speechRun;
    let fellBack = false;
    const fallBack = reason => {
      if (fellBack || run !== speechRun || !state.active) return;
      fellBack = true; currentAudio = null;
      const detail = reason ? ` (${reason})` : "";
      speakWithBrowser(text, language, `ElevenLabs ${languageNames[language] || ""} voice unavailable${detail}; using the browser voice.`);
    };
    try {
      const result = await chrome.runtime.sendMessage({ type: "elevenlabs-tts", text, language });
      if (result?.status !== "success") return fallBack(result?.reason || "TTS request failed");
      if (run !== speechRun) return; // user moved on, Pause/Stop was pressed, or newer guidance started
      const audio = new Audio(`data:${result.mimeType};base64,${result.audio}`);
      currentAudio = audio;
      audio.onended = () => { currentAudio = null; if (state.active && state.status === "speaking") render("waiting_for_input", $("#sm-guidance").textContent); };
      audio.onerror = fallBack;
      state.status = "speaking";
      await audio.play();
    } catch (error) { fallBack(error?.message || "TTS request failed"); }
  }
  function speakWithBrowser(text, language, notice) {
    if (!("speechSynthesis" in window)) return setNotice("Spoken output is unavailable in this browser. Read the guidance above.");
    const voice = findVoice(language);
    if (!voice) {
      setNotice("Loading browser speech voices...");
      const retry = () => {
        const loadedVoice = findVoice(language);
        if (loadedVoice) { if ($("#sm-notice").textContent.startsWith("Loading browser speech")) setNotice(notice || ""); speakWithVoice(text, loadedVoice); }
        else setNotice(`Spoken output is unavailable for ${languageNames[language] || "this language"} in this browser. Read the guidance above.`);
      };
      speechSynthesis.addEventListener("voiceschanged", retry, { once: true });
      setTimeout(retry, 1000);
      return;
    }
    if (notice) setNotice(notice);
    speakWithVoice(text, voice);
  }
  function findVoice(language) {
    const voices = speechSynthesis.getVoices();
    const preferred = state.settings.voiceName && voices.find(voice => voice.name === state.settings.voiceName);
    return preferred || voices.find(candidate => candidate.lang.toLowerCase().startsWith(language));
  }
  function speakWithVoice(text, voice) {
    speechSynthesis.cancel();
    state.status = "speaking";
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = voice.lang; utterance.voice = voice;
    utterance.onend = () => { if (state.active && state.status === "speaking") render("waiting_for_input", $("#sm-guidance").textContent); };
    utterance.onerror = () => { if (state.active) setNotice("Spoken output failed. Read the guidance above."); };
    speechSynthesis.speak(utterance);
  }
  function setNotice(text) {
    const notice = $("#sm-notice");
    notice.textContent = text;
    notice.hidden = !text;
  }
  function setSaved(text) {
    const saved = $("#sm-saved");
    saved.textContent = text;
    saved.hidden = !text;
  }
  function resolveLanguage() {
    const configured = state.settings.language;
    if (configured && configured !== "auto") return configured;
    const pageLanguage = document.documentElement.lang || document.documentElement.getAttribute("xml:lang") || navigator.language;
    if (/^hi(?:-|$)/i.test(pageLanguage)) return "hi";
    if (/^bn(?:-|$)/i.test(pageLanguage)) return "bn";
    if (/^gu(?:-|$)/i.test(pageLanguage)) return "gu";
    if (/^pa(?:-|$)/i.test(pageLanguage)) return "pa";
    if (/^en(?:-|$)/i.test(pageLanguage)) return "en";
    return "hi";
  }
  function clean(value) { return String(value || "").replace(/\s+/g, " ").replace(/[<>]/g, "").trim(); }
})();
