import { useState, useEffect } from "react";
import {
  X,
  FileText,
  Download,
  ExternalLink,
  AlertTriangle,
  Loader2,
  Eye,
  ZoomIn,
  ZoomOut,
  RotateCw,
} from "lucide-react";
import { getAccessToken, getEvidenceDocumentBlobUrl } from "../../api/evidence";

export default function DocumentPreviewModal({
  isOpen = false,
  onClose = () => {},
  documentId = "",
  associationId = "",
  filename = "document.pdf",
  mimeType = "",
}) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);

  // Determine file format / category
  const lowerName = (filename || "").toLowerCase();
  const lowerMime = (mimeType || "").toLowerCase();

  const isPdf =
    lowerMime.includes("pdf") ||
    lowerName.endsWith(".pdf");

  const isImage =
    lowerMime.startsWith("image/") ||
    /\.(png|jpe?g|webp|gif|svg|bmp)$/i.test(lowerName);

  // Close on Esc key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Load document blob when modal opens
  useEffect(() => {
    let active = true;
    let createdUrl = null;

    if (isOpen && (documentId || associationId)) {
      setLoading(true);
      setError(null);
      setZoom(100);
      setRotation(0);

      getEvidenceDocumentBlobUrl({ documentId, associationId })
        .then((url) => {
          if (!active) return;
          createdUrl = url;
          setBlobUrl(url);
          setLoading(false);
        })
        .catch((err) => {
          if (!active) return;
          console.error("Document preview load error:", err);
          setError(err?.message || "Failed to load document preview.");
          setLoading(false);
        });
    } else {
      setBlobUrl(null);
      setError(null);
      setLoading(false);
    }

    return () => {
      active = false;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [isOpen, documentId, associationId]);

  if (!isOpen) return null;

  const handleDownload = () => {
    if (!blobUrl) return;
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename || "document";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleOpenInNewTab = () => {
    if (!blobUrl) return;
    window.open(blobUrl, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/70 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div
        className="relative bg-white rounded-2xl shadow-2xl border border-slate-200/90 w-full max-w-5xl h-[88vh] flex flex-col z-10 overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-200/90 bg-slate-50/80 flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center shrink-0 border border-purple-200">
              <FileText size={16} />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-bold text-slate-900 truncate" title={filename}>
                {filename || "Documentary Proof Preview"}
              </h3>
              <p className="text-[11px] text-slate-500 font-medium">
                {mimeType || (isPdf ? "application/pdf" : isImage ? "image" : "Documentary Evidence")}
              </p>
            </div>
          </div>

          {/* Action Controls & Close */}
          <div className="flex items-center gap-2 shrink-0">
            {isImage && blobUrl && !loading && !error && (
              <div className="hidden sm:flex items-center gap-1 mr-2 px-2 py-1 bg-white border border-slate-200 rounded-lg text-xs text-slate-600">
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.max(50, z - 25))}
                  className="p-1 hover:text-slate-900 hover:bg-slate-100 rounded"
                  title="Zoom Out"
                >
                  <ZoomOut size={14} />
                </button>
                <span className="font-mono text-[11px] px-1">{zoom}%</span>
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.min(250, z + 25))}
                  className="p-1 hover:text-slate-900 hover:bg-slate-100 rounded"
                  title="Zoom In"
                >
                  <ZoomIn size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => setRotation((r) => (r + 90) % 360)}
                  className="p-1 hover:text-slate-900 hover:bg-slate-100 rounded ml-1 border-l border-slate-200 pl-1.5"
                  title="Rotate 90°"
                >
                  <RotateCw size={14} />
                </button>
              </div>
            )}

            {blobUrl && (
              <>
                <button
                  type="button"
                  onClick={handleOpenInNewTab}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition-colors"
                  title="Open in new window"
                >
                  <ExternalLink size={13} />
                  <span className="hidden sm:inline">Open in Tab</span>
                </button>

                <button
                  type="button"
                  onClick={handleDownload}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 text-xs font-bold transition-colors"
                  title="Download copy"
                >
                  <Download size={13} />
                  <span className="hidden sm:inline">Download</span>
                </button>
              </>
            )}

            <button
              type="button"
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
              title="Close Preview (Esc)"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content Body / Viewer */}
        <div className="flex-1 bg-slate-100/90 relative overflow-hidden flex items-center justify-center">
          {loading && (
            <div className="flex flex-col items-center justify-center p-8 text-center space-y-3">
              <Loader2 size={32} className="text-purple-600 animate-spin" />
              <p className="text-xs font-semibold text-slate-600">
                Loading documentary proof preview...
              </p>
            </div>
          )}

          {!loading && error && (
            <div className="max-w-md p-6 bg-white rounded-xl border border-red-200 shadow-sm text-center space-y-3 m-4">
              <div className="w-10 h-10 rounded-full bg-red-50 border border-red-200 text-red-600 flex items-center justify-center mx-auto">
                <AlertTriangle size={20} />
              </div>
              <h4 className="text-sm font-bold text-slate-900">Unable to Load Preview</h4>
              <p className="text-xs text-slate-600 leading-relaxed">{error}</p>
              <div className="pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800 transition-colors"
                >
                  Close Modal
                </button>
              </div>
            </div>
          )}

          {!loading && !error && blobUrl && isPdf && (
            <iframe
              src={`${blobUrl}#toolbar=1&navpanes=0`}
              title={filename}
              className="w-full h-full border-none bg-white"
            />
          )}

          {!loading && !error && blobUrl && isImage && (
            <div className="w-full h-full overflow-auto p-4 flex items-center justify-center bg-slate-900/5">
              <img
                src={blobUrl}
                alt={filename}
                style={{
                  transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                  transition: "transform 0.15s ease-out",
                  maxWidth: "95%",
                  maxHeight: "95%",
                }}
                className="object-contain rounded-md shadow-md bg-white select-none"
              />
            </div>
          )}

          {!loading && !error && blobUrl && !isPdf && !isImage && (
            <div className="max-w-md p-6 bg-white rounded-xl border border-slate-200 shadow-sm text-center space-y-4 m-4">
              <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center mx-auto border border-slate-200">
                <FileText size={24} />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">Preview not available for this file type</h4>
                <p className="text-xs text-slate-500 mt-1">
                  This document format cannot be embedded directly in the browser viewer. You can download or open it in a new window.
                </p>
              </div>
              <div className="flex items-center justify-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleDownload}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold transition-colors"
                >
                  <Download size={14} />
                  <span>Download Document</span>
                </button>
                <button
                  type="button"
                  onClick={handleOpenInNewTab}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-200 rounded-lg text-xs font-bold transition-colors"
                >
                  <ExternalLink size={14} />
                  <span>Open in Tab</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer info strip */}
        <div className="px-5 py-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500 shrink-0">
          <span>Authoritative Evidence Repository</span>
          <span className="font-mono text-slate-400">
            {documentId || associationId ? `Ref: ${(documentId || associationId).slice(0, 18)}...` : ""}
          </span>
        </div>
      </div>
    </div>
  );
}
