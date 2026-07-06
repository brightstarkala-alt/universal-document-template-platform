import type { TemplateManifestField } from "@udtp/shared";

/**
 * Pure DOM-manipulation helpers for the Preview Renderer (Module 9) —
 * framework-free and independent of any templating engine (no Jinja,
 * Handlebars, Mustache). Every function here operates on a plain `Document`
 * (the sandboxed preview iframe's `contentDocument` in practice, but a
 * jsdom `Document` in tests) and reads/writes only the neutral `data-*`
 * markers Module 8 already emits — never coordinate/position data, never
 * anything that would send an edit back to the server. All state produced
 * here (value overrides, resolved asset URLs) is ephemeral and lives only
 * in the caller's memory.
 */

const HOVER_HIGHLIGHT_CSS = `
[data-field-id], [data-repeating-row], [data-asset-id] {
  transition: outline-color 0.1s ease-in-out;
}
[data-field-id]:hover, [data-repeating-row]:hover, [data-asset-id]:hover {
  outline: 2px solid #2563eb;
  outline-offset: 1px;
  cursor: pointer;
}
`.trim();

/**
 * Assembles one standalone HTML document from the artifact's `html` (body
 * markup only) and `css` — the same fixed, trivial concatenation any
 * consumer of a `TemplateArtifact` performs, per Module 8's contract.
 * Adds one extra stylesheet for hover highlighting — a Module 9 UI
 * concern, never stored, never part of the artifact itself.
 */
export function buildPreviewDocument(html: string, css: string): string {
  return (
    "<!doctype html><html><head><meta charset=\"utf-8\" />" +
    `<style>${css}</style><style>${HOVER_HIGHLIGHT_CSS}</style>` +
    `</head><body>${html}</body></html>`
  );
}

function indexByAttribute(elements: NodeListOf<Element>, attribute: string): Map<string, Element[]> {
  const map = new Map<string, Element[]>();
  elements.forEach((element) => {
    const value = element.getAttribute(attribute);
    if (!value) return;
    const existing = map.get(value);
    if (existing) {
      existing.push(element);
    } else {
      map.set(value, [element]);
    }
  });
  return map;
}

/**
 * Replaces the displayed text of every field marker with its override
 * value (falling back to the manifest's original `sample_value` when no
 * override is set) — a purely visual, in-memory substitution. Never
 * touches the stored `TemplateArtifact`.
 */
export function applyFieldOverrides(
  doc: Document,
  fields: TemplateManifestField[],
  overrides: Record<string, string>,
): void {
  const elementsByFieldId = indexByAttribute(doc.querySelectorAll("[data-field-id]"), "data-field-id");
  for (const field of fields) {
    const elements = elementsByFieldId.get(field.field_id);
    if (!elements) continue;
    const value = overrides[field.field_id] ?? field.sample_value;
    elements.forEach((element) => {
      element.textContent = value;
    });
  }
}

/** Patches every `<img data-asset-id>` with its resolved URL, when known. */
export function resolveAssetSources(doc: Document, assetUrls: Record<string, string>): void {
  doc.querySelectorAll<HTMLImageElement>("[data-asset-id]").forEach((image) => {
    const assetId = image.getAttribute("data-asset-id");
    const url = assetId ? assetUrls[assetId] : undefined;
    if (url) {
      image.src = url;
    }
  });
}

/**
 * Attaches a click listener to every field marker, invoking `onFieldClick`
 * with that field's manifest entry (display_label/machine_key/type/
 * confidence) — never with anything read off the DOM element itself, since
 * the DOM only carries `data-field-id`/`data-machine-key`. Returns a
 * cleanup function that removes every listener it attached.
 */
export function attachFieldClickHandler(
  doc: Document,
  fields: TemplateManifestField[],
  onFieldClick: (field: TemplateManifestField) => void,
): () => void {
  const fieldsById = new Map(fields.map((field) => [field.field_id, field]));
  const cleanups: Array<() => void> = [];

  doc.querySelectorAll<HTMLElement>("[data-field-id]").forEach((element) => {
    const fieldId = element.getAttribute("data-field-id");
    const field = fieldId ? fieldsById.get(fieldId) : undefined;
    if (!field) return;

    const handler = (): void => onFieldClick(field);
    element.addEventListener("click", handler);
    cleanups.push(() => element.removeEventListener("click", handler));
  });

  return () => cleanups.forEach((cleanup) => cleanup());
}

/**
 * Attaches an `error` listener to every asset image, invoking
 * `onAssetError` with that image's `asset_id` when it fails to load (most
 * commonly because its signed URL expired) — the caller is expected to
 * fetch a fresh URL and patch `src` again via `resolveAssetSources`,
 * without reloading the preview. Returns a cleanup function.
 */
export function attachAssetErrorHandler(
  doc: Document,
  onAssetError: (assetId: string) => void,
): () => void {
  const cleanups: Array<() => void> = [];

  doc.querySelectorAll<HTMLImageElement>("[data-asset-id]").forEach((image) => {
    const assetId = image.getAttribute("data-asset-id");
    if (!assetId) return;

    const handler = (): void => onAssetError(assetId);
    image.addEventListener("error", handler);
    cleanups.push(() => image.removeEventListener("error", handler));
  });

  return () => cleanups.forEach((cleanup) => cleanup());
}
