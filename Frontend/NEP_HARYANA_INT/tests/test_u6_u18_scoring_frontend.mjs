/**
 * NEP Haryana Excellence Awards 2026 - U6 and U18.3 Frontend Taxonomy & Scoring Tests.
 *
 * Verifies:
 * 1. U6.A and U6.B are independently defined in taxonomy with 4 marks maximum each.
 * 2. Combined U6 total calculation is strictly U6.A + U6.B (max 8 marks).
 * 3. U18.3 is defined with 2 marks maximum and EVID_U18_RPL_FORMAT canonical evidence.
 * 4. PDF-only file format restriction enforced for U6.A, U6.B, and U18.3.
 * 5. Other parameters retain their accepted file formats.
 * 6. EvidenceUploadModal enforces client-side magic-byte and %%EOF structural checks.
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");

test("NEP 2026 University Scoring & Evidence — U6 and U18.3 Frontend Suite", async (t) => {
  const taxonomyFile = fs.readFileSync(path.join(ROOT, "src/utils/nepTaxonomy.js"), "utf8");
  const modalFile = fs.readFileSync(path.join(ROOT, "src/components/Institution/EvidenceUploadModal.jsx"), "utf8");
  const schemaFile = fs.readFileSync(path.join(ROOT, "src/utils/nepFrameworkSchema.generated.js"), "utf8");

  await t.test("1. U6.A and U6.B are separate subcriteria with 4 marks each and allowedFileFormats = ['pdf']", () => {
    assert.match(taxonomyFile, /"code":\s*"U6\.A"[\s\S]*?"maxScore":\s*4/);
    assert.match(taxonomyFile, /"code":\s*"U6\.B"[\s\S]*?"maxScore":\s*4/);
    assert.match(taxonomyFile, /"code":\s*"U6\.A"[\s\S]*?"canonicalEvidenceType":\s*"EVID_U6_ORDINANCE_GAZETTE"/);
    assert.match(taxonomyFile, /"code":\s*"U6\.B"[\s\S]*?"canonicalEvidenceType":\s*"EVID_U6_PEDAGOGY_RECORDS"/);
    assert.match(taxonomyFile, /"code":\s*"U6\.A"[\s\S]*?"allowedFileFormats":\s*\[\s*"pdf"\s*\]/);
    assert.match(taxonomyFile, /"code":\s*"U6\.B"[\s\S]*?"allowedFileFormats":\s*\[\s*"pdf"\s*\]/);
  });

  await t.test("2. Combined U6 parameter specifies 8 marks maximum derived from U6.A and U6.B", () => {
    assert.match(taxonomyFile, /"code":\s*"U6"[\s\S]*?"maxMarks":\s*8/);
  });

  await t.test("3. U18.3 specifies 2 marks maximum, EVID_U18_RPL_FORMAT, and allowedFileFormats = ['pdf']", () => {
    assert.match(taxonomyFile, /"code":\s*"U18\.3"[\s\S]*?"maxScore":\s*2/);
    assert.match(taxonomyFile, /"code":\s*"U18\.3"[\s\S]*?"canonicalEvidenceType":\s*"EVID_U18_RPL_FORMAT"/);
    assert.match(taxonomyFile, /"code":\s*"U18\.3"[\s\S]*?"allowedFileFormats":\s*\[\s*"pdf"\s*\]/);
  });

  await t.test("4. nepFrameworkSchema.generated.js exports allowed_file_formats: ['pdf'] for U6 and U18.3", () => {
    assert.match(schemaFile, /"U6\.A":\s*\{[\s\S]*?"allowed_file_formats":\s*\[\s*"pdf"\s*\]/);
    assert.match(schemaFile, /"U6\.B":\s*\{[\s\S]*?"allowed_file_formats":\s*\[\s*"pdf"\s*\]/);
    assert.match(schemaFile, /"U18\.3":\s*\{[\s\S]*?"allowed_file_formats":\s*\[\s*"pdf"\s*\]/);
  });

  await t.test("5. EvidenceUploadModal enforces secure PDF-only validation and %%EOF inspection", () => {
    // Verifies header check
    assert.match(modalFile, /headerStr\.startsWith\("%PDF-"\)/);
    // Verifies trailer check
    assert.match(modalFile, /tailStr\.includes\("%%EOF"\)/);
    // Verifies empty file rejection
    assert.match(modalFile, /file\.size === 0/);
    // Verifies too small file rejection (< 20 bytes)
    assert.match(modalFile, /file\.size < 20/);
    // Verifies restricted accept attribute when isPdfOnly
    assert.match(modalFile, /accept=\{isPdfOnly \? "\.pdf,application\/pdf"/);
  });

  await t.test("6. Non-PDF criteria preserve their allowed formats and are not forced into PDF-only mode", () => {
    // Other subcriteria in generated schema retain the multi-format list
    assert.match(schemaFile, /"allowed_file_formats":\s*\[\s*"pdf",\s*"png",\s*"jpg",\s*"jpeg",\s*"webp",\s*"docx",\s*"xlsx"\s*\]/);
  });
});
