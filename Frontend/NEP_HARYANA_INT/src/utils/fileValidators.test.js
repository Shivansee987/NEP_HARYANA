import { describe, it, expect } from 'vitest';
import { validateUploadFile, PDF_SIZE_LIMIT_ERROR_MESSAGE } from './fileValidators';

function createDummyPdfFile(sizeBytes, name = "test.pdf") {
  // Construct genuine PDF header and footer
  const header = "%PDF-1.4\n";
  const trailer = "\n%%EOF";
  const headerBytes = new TextEncoder().encode(header);
  const trailerBytes = new TextEncoder().encode(trailer);

  if (sizeBytes < headerBytes.length + trailerBytes.length) {
    const raw = new Uint8Array(sizeBytes);
    return new File([raw], name, { type: "application/pdf" });
  }

  const fillerLength = sizeBytes - headerBytes.length - trailerBytes.length;
  const filler = new Uint8Array(fillerLength);
  filler.fill(65); // fill with 'A'

  const combined = new Uint8Array(sizeBytes);
  combined.set(headerBytes, 0);
  combined.set(filler, headerBytes.length);
  combined.set(trailerBytes, headerBytes.length + fillerLength);

  return new File([combined], name, { type: "application/pdf" });
}

describe('fileValidators - 5 MB PDF Limit Enforcement', () => {
  it('accepts a valid PDF smaller than 5 MB', async () => {
    const file = createDummyPdfFile(1024 * 100); // 100 KB
    const error = await validateUploadFile(file, { isPdfOnly: true });
    expect(error).toBeNull();
  });

  it('accepts a valid PDF exactly 5 MB (5,242,880 bytes)', async () => {
    const file = createDummyPdfFile(5 * 1024 * 1024);
    expect(file.size).toBe(5242880);
    const error = await validateUploadFile(file, { isPdfOnly: true });
    expect(error).toBeNull();
  });

  it('rejects a PDF larger than 5 MB by exactly one byte (5,242,881 bytes)', async () => {
    const file = createDummyPdfFile(5 * 1024 * 1024 + 1);
    expect(file.size).toBe(5242881);
    const error = await validateUploadFile(file, { isPdfOnly: true });
    expect(error).toBe(PDF_SIZE_LIMIT_ERROR_MESSAGE);
  });

  it('rejects a significantly oversized PDF (10 MB)', async () => {
    // Fake File with size property mocked or large buffer
    const largeFile = {
      name: "large.pdf",
      size: 10 * 1024 * 1024,
      slice: () => ({ arrayBuffer: async () => new Uint8Array(0).buffer })
    };
    const error = await validateUploadFile(largeFile, { isPdfOnly: true });
    expect(error).toBe(PDF_SIZE_LIMIT_ERROR_MESSAGE);
  });

  it('rejects a non-PDF file renamed with .pdf extension (invalid header magic bytes)', async () => {
    const dummyExe = new TextEncoder().encode("MZThisIsAnExecutableFileFakePayload");
    const file = new File([dummyExe], "malicious.pdf", { type: "application/pdf" });
    const error = await validateUploadFile(file, { isPdfOnly: true });
    expect(error).toContain("does not have a genuine PDF header");
  });

  it('rejects an empty file (0 bytes)', async () => {
    const file = new File([], "empty.pdf", { type: "application/pdf" });
    const error = await validateUploadFile(file, { isPdfOnly: true });
    expect(error).toContain("empty (0 bytes)");
  });

  it('rejects a PDF missing %%EOF trailer marker', async () => {
    const brokenPdf = new TextEncoder().encode("%PDF-1.4\nSome random content without trailer");
    const file = new File([brokenPdf], "broken.pdf", { type: "application/pdf" });
    const error = await validateUploadFile(file, { isPdfOnly: true });
    expect(error).toContain("missing a valid %%EOF termination marker");
  });
});
