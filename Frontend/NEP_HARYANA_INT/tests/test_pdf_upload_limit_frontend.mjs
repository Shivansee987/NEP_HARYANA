/**
 * test_pdf_upload_limit_frontend.mjs
 * Test suite verifying the 5 MB PDF limit enforcement across frontend validators and forms.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  MAX_PDF_SIZE_BYTES,
  PDF_SIZE_LIMIT_ERROR_MESSAGE,
  validateUploadFile,
} from '../src/utils/fileValidators.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '../src');

// Helper to construct a simulated File object with specified bytes
function createMockFile(sizeBytes, { isPdf = true, name = "evidence.pdf", corruptHeader = false, missingTrailer = false } = {}) {
  let content;
  if (!isPdf || corruptHeader) {
    content = Buffer.alloc(sizeBytes, 0x41); // All 'A's
    if (corruptHeader) {
      content.write("NOTPDF", 0);
    }
  } else {
    content = Buffer.alloc(sizeBytes, 0x20); // space fill
    content.write("%PDF-1.4\n", 0);
    if (!missingTrailer && sizeBytes >= 20) {
      content.write("\n%%EOF", sizeBytes - 6);
    }
  }

  return {
    name,
    size: sizeBytes,
    slice: (start, end) => ({
      arrayBuffer: async () => {
        const sliceBuf = content.subarray(start, end);
        return sliceBuf.buffer.slice(sliceBuf.byteOffset, sliceBuf.byteOffset + sliceBuf.byteLength);
      }
    })
  };
}

describe('Frontend 5 MB PDF Limit Enforcement Suite', () => {

  it('1. Constants are defined: MAX_PDF_SIZE_BYTES is exactly 5,242,880 bytes (5 MB)', () => {
    assert.strictEqual(
      MAX_PDF_SIZE_BYTES,
      5 * 1024 * 1024,
      `Expected 5,242,880 bytes but got ${MAX_PDF_SIZE_BYTES}`
    );
    assert.strictEqual(
      PDF_SIZE_LIMIT_ERROR_MESSAGE,
      "The PDF file must not exceed 5 MB. Please choose a smaller file."
    );
  });

  it('2. Accepts a valid PDF smaller than 5 MB', async () => {
    const file = createMockFile(1024 * 50); // 50 KB
    const err = await validateUploadFile(file, { isPdfOnly: true });
    assert.strictEqual(err, null, `Expected no error, got: ${err}`);
  });

  it('3. Accepts a valid PDF of exactly 5 MB (5,242,880 bytes)', async () => {
    const file = createMockFile(5 * 1024 * 1024);
    assert.strictEqual(file.size, 5242880);
    const err = await validateUploadFile(file, { isPdfOnly: true });
    assert.strictEqual(err, null, `Boundary file of exactly 5 MB was rejected: ${err}`);
  });

  it('4. Strictly rejects a PDF exceeding 5 MB by 1 byte (5,242,881 bytes)', async () => {
    const file = createMockFile(5 * 1024 * 1024 + 1);
    assert.strictEqual(file.size, 5242881);
    const err = await validateUploadFile(file, { isPdfOnly: true });
    assert.strictEqual(err, PDF_SIZE_LIMIT_ERROR_MESSAGE);
  });

  it('5. Strictly rejects a significantly oversized PDF (15 MB)', async () => {
    const file = createMockFile(15 * 1024 * 1024);
    const err = await validateUploadFile(file, { isPdfOnly: true });
    assert.strictEqual(err, PDF_SIZE_LIMIT_ERROR_MESSAGE);
  });

  it('6. Rejects a non-PDF file renamed as .pdf (fails genuine %PDF- magic bytes)', async () => {
    const file = createMockFile(1024 * 100, { corruptHeader: true, name: "malicious.pdf" });
    const err = await validateUploadFile(file, { isPdfOnly: true });
    assert.match(err, /genuine PDF header signature \(%PDF-\)/);
  });

  it('7. Rejects an empty file (0 bytes)', async () => {
    const file = createMockFile(0, { name: "empty.pdf" });
    const err = await validateUploadFile(file, { isPdfOnly: true });
    assert.match(err, /empty \(0 bytes\)/);
  });

  it('8. Rejects a truncated PDF missing %%EOF end-of-file trailer', async () => {
    const file = createMockFile(1024 * 10, { missingTrailer: true, name: "truncated.pdf" });
    const err = await validateUploadFile(file, { isPdfOnly: true });
    assert.match(err, /missing a valid %%EOF termination marker/);
  });

  it('9. Form components (EvidenceUploadModal, NominationWorkspace, StudentStats, AcademicInfo) enforce 5 MB limit', () => {
    const modalContent = fs.readFileSync(
      path.join(srcDir, 'components/Institution/EvidenceUploadModal.jsx'),
      'utf8'
    );
    assert.match(modalContent, /validateUploadFile\(file, \{ allowedFormats, isPdfOnly \}\)/, 'EvidenceUploadModal must use the shared file validator');

    const nominationContent = fs.readFileSync(
      path.join(srcDir, 'pages/CollegeDashboard/NominationWorkspace.jsx'),
      'utf8'
    );
    assert.match(nominationContent, /validateUploadFile/, 'NominationWorkspace must call validateUploadFile');

    const studentStatsContent = fs.readFileSync(
      path.join(srcDir, 'pages/StudentStats/StudentStats.jsx'),
      'utf8'
    );
    assert.match(studentStatsContent, /validateUploadFile/, 'StudentStats must call validateUploadFile');

    const academicInfoContent = fs.readFileSync(
      path.join(srcDir, 'pages/AcademicInfo/AcademicInfo.jsx'),
      'utf8'
    );
    assert.match(academicInfoContent, /validateUploadFile/, 'AcademicInfo must call validateUploadFile');
  });
});
