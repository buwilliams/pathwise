// Tiny safe markdown renderer for plan output.
// Supports: H1-H3, paragraphs, ul/ol, **bold**, *italic*, blockquotes, inline links.
// Plans are model-generated, but we still escape HTML defensively.

const md = (() => {
  function escape(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function inline(s) {
    let out = escape(s);
    // Links [text](url) — only allow http(s)
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, t, u) =>
      `<a href="${u}" target="_blank" rel="noopener noreferrer">${t}</a>`
    );
    // Inline code `x`
    out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Bold **x**
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    // Italics *x*  (after bold so ** doesn't trigger)
    out = out.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    return out;
  }

  function render(src) {
    if (!src) return "";
    const lines = src.replace(/\r\n/g, "\n").split("\n");
    const out = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Heading
      const h = line.match(/^(#{1,3})\s+(.*)$/);
      if (h) {
        const lvl = h[1].length;
        out.push(`<h${lvl}>${inline(h[2].trim())}</h${lvl}>`);
        i++; continue;
      }

      // Blockquote
      if (line.startsWith("> ")) {
        const buf = [];
        while (i < lines.length && lines[i].startsWith("> ")) {
          buf.push(lines[i].slice(2));
          i++;
        }
        out.push(`<blockquote>${inline(buf.join(" "))}</blockquote>`);
        continue;
      }

      // Unordered list
      if (/^[-*]\s+/.test(line)) {
        const items = [];
        while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
          items.push(`<li>${inline(lines[i].replace(/^[-*]\s+/, ""))}</li>`);
          i++;
        }
        out.push(`<ul>${items.join("")}</ul>`);
        continue;
      }

      // Ordered list
      if (/^\d+\.\s+/.test(line)) {
        const items = [];
        while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
          items.push(`<li>${inline(lines[i].replace(/^\d+\.\s+/, ""))}</li>`);
          i++;
        }
        out.push(`<ol>${items.join("")}</ol>`);
        continue;
      }

      // Horizontal rule
      if (/^---+$/.test(line.trim())) { out.push("<hr>"); i++; continue; }

      // Blank line
      if (!line.trim()) { i++; continue; }

      // Paragraph: gather contiguous non-empty, non-special lines
      const buf = [];
      while (
        i < lines.length &&
        lines[i].trim() &&
        !/^(#{1,3})\s+/.test(lines[i]) &&
        !lines[i].startsWith("> ") &&
        !/^[-*]\s+/.test(lines[i]) &&
        !/^\d+\.\s+/.test(lines[i]) &&
        !/^---+$/.test(lines[i].trim())
      ) {
        buf.push(lines[i]);
        i++;
      }
      out.push(`<p>${inline(buf.join(" "))}</p>`);
    }

    return out.join("\n");
  }

  return { render };
})();
