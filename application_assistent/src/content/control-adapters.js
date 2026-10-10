(() => {
  // A native <select> that the user has not touched may still report a real value (the browser
  // pre-selects the first option), so "has a value" alone must not count as "answered".
  const touched = new WeakSet();
  const initialText = new WeakMap();
  const markTouched = event => {
    const t = event.target;
    if (t && t.tagName === "SELECT") touched.add(t);
    const owner = t?.closest?.("[role='combobox']");
    if (owner) touched.add(owner);
  };
  document.addEventListener("change", markTouched, true);
  document.addEventListener("input", markTouched, true);
  // Custom dropdowns rarely fire "change": clicking an [role=option] means the user picked something.
  document.addEventListener("click", event => {
    const option = event.target?.closest?.("[role='option']");
    if (!option) return;
    const list = option.closest("[role='listbox']");
    document.querySelectorAll("[role='combobox']").forEach(box => {
      const owned = (box.getAttribute("aria-controls") || box.getAttribute("aria-owns") || "").split(/\s+/);
      if (list && list.id && owned.includes(list.id)) touched.add(box);
    });
    const active = document.activeElement;
    if (active?.getAttribute?.("role") === "combobox") touched.add(active);
  }, true);
  const shownText = el => (el.value ?? "").toString().trim() || el.textContent?.trim() || "";

  const adapters = {
    radio: {
      isComplete(field) {
        const name = field.el.name;
        if (!name) return field.el.checked;
        return [...document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`)].some(input => input.checked);
      },
      description: "Select one option from this group."
    },
    checkbox: {
      isComplete(field) {
        return field.el.checked;
      },
      description: "Select this option if it applies to you."
    },
    select: {
      isComplete(field) {
        const el = field.el;
        if (el.selectedIndex < 0 || el.value === "") return false;     // nothing / placeholder chosen
        if (el.multiple) return [...el.selectedOptions].some(o => o.value !== "");
        // Real value: counts only if the page pre-selected it on purpose or the user changed it.
        return touched.has(el) || el.options[el.selectedIndex].defaultSelected || el.options[el.selectedIndex].hasAttribute("selected");
      },
      description: "Choose the option that best matches your information."
    },
    file: {
      isComplete(field) {
        return field.el.files?.length > 0;
      },
      description: "Choose the requested document from your device."
    },
    contenteditable: {
      isComplete(field) {
        return Boolean(field.el.textContent?.trim());
      },
      description: "Enter the information requested by this editable area."
    },
    combobox: {
      isComplete(field) {
        const el = field.el;
        if (el.tagName === "SELECT") return adapters.select.isComplete(field);
        if (el.value !== undefined && el.tagName !== "BUTTON" && el.tagName !== "LI") {
          if (el.value.trim() !== "") return true;                      // <input role=combobox> with text
        }
        if (el.getAttribute("aria-valuetext")) return true;
        // Div/button comboboxes show their placeholder as text, so compare with what we first saw.
        if (!initialText.has(el)) initialText.set(el, shownText(el));
        if (touched.has(el) && shownText(el) !== "") return true;
        return shownText(el) !== "" && shownText(el) !== initialText.get(el);
      },
      description: "Choose an option from this custom list."
    }
  };

  window.SurakshaMitraAdapters = {
    get(field) {
      return adapters[field.type] || {
        isComplete: current => Boolean(current.el.value?.trim()) && (!current.el.validity || current.el.validity.valid),
        description: "Enter the information requested by this field."
      };
    },
    supports(field) {
      return ["radio", "checkbox", "select", "file", "contenteditable", "combobox", "textarea",
        "text", "email", "tel", "number", "date", "time", "datetime-local", "month", "week", "url", "search"].includes(field.type);
    }
  };
})();
