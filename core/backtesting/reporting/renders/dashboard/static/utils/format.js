function displayValue(v) {
  if (v === null || v === undefined) return "-";
  if (typeof v === "object" && v.display !== undefined) return v.display;
  return String(v);
}

// expose globally (no bundler)
window.displayValue = displayValue;