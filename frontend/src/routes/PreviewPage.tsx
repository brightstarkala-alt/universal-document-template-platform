import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import type { TemplateManifestField, TemplatePreviewResponse } from "@udtp/shared";
import { ApiError } from "@/lib/apiClient";
import { logger } from "@/lib/logger";
import { previewService } from "@/services/previewService";
import { pdfService } from "@/services/pdfService";
import { triggerDownload } from "@/lib/downloadHelper";
import {
  applyFieldOverrides,
  attachAssetErrorHandler,
  attachFieldClickHandler,
  buildPreviewDocument,
  resolveAssetSources,
} from "@/lib/templatePreviewRenderer";
import { FieldInspectorPanel } from "@/components/preview/FieldInspectorPanel";

/**
 * Module 9: Preview Renderer. Renders the `TemplateArtifact` Module 8
 * generated exactly as produced — the artifact's `html`/`css` are never
 * modified, only assembled into one document and injected into a
 * sandboxed iframe for style isolation. Every interaction (hover, click,
 * value override) is DOM manipulation against the neutral `data-*` markers
 * Module 8 already emits; nothing here is a templating engine and nothing
 * a user does on this page is ever persisted.
 *
 * Also hosts the "Download PDF" action (Module 10): triggers server-side
 * generation of the same artifact via the shared `document_renderer`, then
 * downloads the result through a signed URL — reusing the existing
 * `triggerDownload` helper, the same one file downloads already use.
 */
export function PreviewPage() {
  const { fileId } = useParams<{ fileId: string }>();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const retriedAssetIds = useRef<Set<string>>(new Set());

  const [preview, setPreview] = useState<TemplatePreviewResponse | null>(null);
  const [assetUrls, setAssetUrls] = useState<Record<string, string>>({});
  const [srcDoc, setSrcDoc] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isIframeReady, setIsIframeReady] = useState(false);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [selectedField, setSelectedField] = useState<TemplateManifestField | null>(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  useEffect(() => {
    if (!fileId) return;
    let isMounted = true;
    setIsLoading(true);
    setLoadError(null);
    setIsIframeReady(false);

    previewService
      .getLatestPreview(fileId)
      .then((data) => {
        if (!isMounted) return;
        setPreview(data);
        setAssetUrls(data.asset_urls);
        setSrcDoc(buildPreviewDocument(data.artifact.html, data.artifact.css));
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        const message = err instanceof ApiError ? err.message : "Failed to load preview.";
        logger.error("Failed to load preview", { fileId, message });
        setLoadError(message);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [fileId]);

  const handleAssetError = useCallback(
    (assetId: string) => {
      if (!fileId || retriedAssetIds.current.has(assetId)) return;
      retriedAssetIds.current.add(assetId);

      previewService
        .refreshAssetUrl(fileId, assetId)
        .then((signed) => {
          setAssetUrls((prev) => ({ ...prev, [assetId]: signed.url }));
        })
        .catch((err: unknown) => {
          const message = err instanceof ApiError ? err.message : "Failed to refresh asset.";
          logger.warn("Failed to refresh an expired preview asset url", { assetId, message });
        });
    },
    [fileId],
  );

  // Click/error listeners are attached once per artifact load — `preview`
  // only changes when a new artifact is fetched, not on every override edit.
  useEffect(() => {
    if (!isIframeReady || !preview) return;
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;

    const detachClicks = attachFieldClickHandler(doc, preview.artifact.manifest.fields, setSelectedField);
    const detachErrors = attachAssetErrorHandler(doc, handleAssetError);

    return () => {
      detachClicks();
      detachErrors();
    };
  }, [isIframeReady, preview, handleAssetError]);

  // Re-patches displayed text whenever the in-memory override map changes —
  // never touches the stored artifact, never reloads the iframe.
  useEffect(() => {
    if (!isIframeReady || !preview) return;
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    applyFieldOverrides(doc, preview.artifact.manifest.fields, overrides);
  }, [isIframeReady, preview, overrides]);

  // Re-patches image sources whenever asset URLs change (initial load, or
  // after handleAssetError fetches a replacement for an expired one).
  useEffect(() => {
    if (!isIframeReady) return;
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    resolveAssetSources(doc, assetUrls);
  }, [isIframeReady, assetUrls]);

  const handleDownloadPdf = useCallback(async () => {
    if (!fileId) return;
    setIsGeneratingPdf(true);
    setPdfError(null);

    try {
      const pdf = await pdfService.generateLatest(fileId);
      const signed = await pdfService.getSignedUrl(fileId, pdf.version);
      triggerDownload(signed.url, `document-v${pdf.version}.pdf`);
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : "Failed to generate PDF.";
      logger.error("Failed to generate or download PDF", { fileId, message });
      setPdfError(message);
    } finally {
      setIsGeneratingPdf(false);
    }
  }, [fileId]);

  if (!fileId) {
    return <p className="p-6 text-sm text-red-600">No file selected.</p>;
  }

  if (isLoading) {
    return <p className="p-6 text-sm text-gray-500">Loading preview…</p>;
  }

  if (loadError) {
    return <p className="p-6 text-sm text-red-600">{loadError}</p>;
  }

  const overrideValue = selectedField
    ? (overrides[selectedField.field_id] ?? selectedField.sample_value)
    : "";

  return (
    <div className="flex h-full w-full">
      <div className="flex-1 overflow-auto bg-gray-100 p-4">
        <div className="mb-3 flex items-center justify-end gap-2">
          {pdfError && <span className="text-sm text-red-600">{pdfError}</span>}
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={isGeneratingPdf}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isGeneratingPdf ? "Generating PDF…" : "Download PDF"}
          </button>
        </div>
        <iframe
          ref={iframeRef}
          title="Template preview"
          srcDoc={srcDoc}
          onLoad={() => setIsIframeReady(true)}
          sandbox="allow-same-origin"
          className="h-full w-full rounded border border-gray-300 bg-white"
        />
      </div>
      <FieldInspectorPanel
        field={selectedField}
        overrideValue={overrideValue}
        onOverrideChange={(value) => {
          if (!selectedField) return;
          setOverrides((prev) => ({ ...prev, [selectedField.field_id]: value }));
        }}
        onClose={() => setSelectedField(null)}
      />
    </div>
  );
}
