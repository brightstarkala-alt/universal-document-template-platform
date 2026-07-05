import { fileApi } from "@/services/fileApi";

/** Fetches a fresh, short-lived signed URL for downloading a stored file. */
export async function getSignedDownloadUrl(fileId: string): Promise<string> {
  const { url } = await fileApi.getSignedUrl(fileId);
  return url;
}
