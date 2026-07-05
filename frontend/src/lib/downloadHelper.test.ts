import { describe, it, expect, vi, afterEach } from "vitest";
import { triggerDownload } from "@/lib/downloadHelper";

describe("triggerDownload", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates, clicks, and removes a temporary anchor element", () => {
    const appendSpy = vi.spyOn(document.body, "appendChild");
    const removeSpy = vi.spyOn(document.body, "removeChild");
    const createSpy = vi.spyOn(document, "createElement");

    triggerDownload("https://example.supabase.co/signed/file-1.pdf", "invoice.pdf");

    expect(createSpy).toHaveBeenCalledWith("a");
    const anchor = createSpy.mock.results[0].value as HTMLAnchorElement;
    expect(anchor.href).toBe("https://example.supabase.co/signed/file-1.pdf");
    expect(anchor.download).toBe("invoice.pdf");
    expect(appendSpy).toHaveBeenCalledWith(anchor);
    expect(removeSpy).toHaveBeenCalledWith(anchor);
  });
});
