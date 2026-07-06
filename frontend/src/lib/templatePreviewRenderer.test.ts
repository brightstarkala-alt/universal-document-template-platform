import { describe, it, expect, vi } from "vitest";
import type { TemplateManifestField } from "@udtp/shared";
import {
  buildPreviewDocument,
  applyFieldOverrides,
  resolveAssetSources,
  attachFieldClickHandler,
  attachAssetErrorHandler,
} from "@/lib/templatePreviewRenderer";

function parseDocument(bodyHtml: string): Document {
  return new DOMParser().parseFromString(`<html><body>${bodyHtml}</body></html>`, "text/html");
}

const FIELD: TemplateManifestField = {
  field_id: "f1",
  machine_key: "invoice_number",
  display_label: "Invoice Number",
  type: "identifier",
  sample_value: "INV-1001",
  confidence: 0.9,
  confidence_tier: "high",
  unit_index: 0,
};

describe("buildPreviewDocument", () => {
  it("includes the artifact css and the html body content", () => {
    const result = buildPreviewDocument("<p>hello</p>", "body { margin: 0; }");

    expect(result).toContain("<style>body { margin: 0; }</style>");
    expect(result).toContain("<p>hello</p>");
  });

  it("adds a hover-highlight stylesheet that is never part of the stored artifact", () => {
    const result = buildPreviewDocument("<p>hello</p>", "");

    expect(result).toContain("[data-field-id]:hover");
    expect(result).toContain("cursor: pointer");
  });
});

describe("applyFieldOverrides", () => {
  it("falls back to the manifest sample_value when there is no override", () => {
    const doc = parseDocument('<span data-field-id="f1">INV-1001</span>');

    applyFieldOverrides(doc, [FIELD], {});

    expect(doc.querySelector('[data-field-id="f1"]')?.textContent).toBe("INV-1001");
  });

  it("replaces displayed text with the override value", () => {
    const doc = parseDocument('<span data-field-id="f1">INV-1001</span>');

    applyFieldOverrides(doc, [FIELD], { f1: "INV-9999" });

    expect(doc.querySelector('[data-field-id="f1"]')?.textContent).toBe("INV-9999");
  });

  it("does not touch elements for fields it was not given", () => {
    const doc = parseDocument(
      '<span data-field-id="f1">INV-1001</span><span data-field-id="f2">unchanged</span>',
    );

    applyFieldOverrides(doc, [FIELD], { f1: "INV-9999" });

    expect(doc.querySelector('[data-field-id="f2"]')?.textContent).toBe("unchanged");
  });

  it("only replaces the matched substring's own marker, leaving surrounding label text alone", () => {
    const doc = parseDocument(
      '<p>Invoice Number: <span data-field-id="f1">INV-1001</span></p>',
    );

    applyFieldOverrides(doc, [FIELD], { f1: "INV-9999" });

    expect(doc.body.textContent).toBe("Invoice Number: INV-9999");
  });
});

describe("resolveAssetSources", () => {
  it("patches the src of a matching asset image", () => {
    const doc = parseDocument('<img data-asset-id="asset-1">');

    resolveAssetSources(doc, { "asset-1": "https://signed.example/asset-1.png" });

    expect(doc.querySelector("img")?.getAttribute("src")).toBe(
      "https://signed.example/asset-1.png",
    );
  });

  it("leaves an image unresolved when no url is known for it", () => {
    const doc = parseDocument('<img data-asset-id="asset-1">');

    resolveAssetSources(doc, {});

    expect(doc.querySelector("img")?.getAttribute("src")).toBeNull();
  });
});

describe("attachFieldClickHandler", () => {
  it("invokes onFieldClick with the matched manifest field", () => {
    const doc = parseDocument('<span data-field-id="f1">INV-1001</span>');
    const onFieldClick = vi.fn();

    attachFieldClickHandler(doc, [FIELD], onFieldClick);
    doc.querySelector('[data-field-id="f1"]')?.dispatchEvent(new Event("click", { bubbles: true }));

    expect(onFieldClick).toHaveBeenCalledWith(FIELD);
  });

  it("does not attach a handler for a marker with no matching manifest field", () => {
    const doc = parseDocument('<span data-field-id="unknown">x</span>');
    const onFieldClick = vi.fn();

    attachFieldClickHandler(doc, [FIELD], onFieldClick);
    doc
      .querySelector('[data-field-id="unknown"]')
      ?.dispatchEvent(new Event("click", { bubbles: true }));

    expect(onFieldClick).not.toHaveBeenCalled();
  });

  it("cleanup removes the listener", () => {
    const doc = parseDocument('<span data-field-id="f1">INV-1001</span>');
    const onFieldClick = vi.fn();

    const cleanup = attachFieldClickHandler(doc, [FIELD], onFieldClick);
    cleanup();
    doc.querySelector('[data-field-id="f1"]')?.dispatchEvent(new Event("click", { bubbles: true }));

    expect(onFieldClick).not.toHaveBeenCalled();
  });
});

describe("attachAssetErrorHandler", () => {
  it("invokes onAssetError with the failing image's asset_id", () => {
    const doc = parseDocument('<img data-asset-id="asset-1">');
    const onAssetError = vi.fn();

    attachAssetErrorHandler(doc, onAssetError);
    doc.querySelector("img")?.dispatchEvent(new Event("error"));

    expect(onAssetError).toHaveBeenCalledWith("asset-1");
  });

  it("cleanup removes the listener", () => {
    const doc = parseDocument('<img data-asset-id="asset-1">');
    const onAssetError = vi.fn();

    const cleanup = attachAssetErrorHandler(doc, onAssetError);
    cleanup();
    doc.querySelector("img")?.dispatchEvent(new Event("error"));

    expect(onAssetError).not.toHaveBeenCalled();
  });
});
