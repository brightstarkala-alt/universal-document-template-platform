/**
 * Triggers a browser download for a given URL by creating and clicking a
 * temporary anchor element. Pure DOM utility — no file picking or drag &
 * drop, and no knowledge of the API; callers pass in a URL (typically from
 * `signedUrlHelper`).
 */
export function triggerDownload(url: string, filename: string): void {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
