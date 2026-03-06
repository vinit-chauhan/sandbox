import { useState, useRef, type DragEvent } from "react";
import { streamRedact } from "../api/client";

const ACCEPTED =
  ".log,.txt,.json,.csv,.yml,.yaml,.conf,.config,.ini,.xml,.md,.text";

export default function RedactPage() {
  const [inputText, setInputText] = useState("");
  const [dragging, setDragging] = useState(false);
  const [viewMode, setViewMode] = useState<"input" | "preview">("input");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [redactedText, setRedactedText] = useState("");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [warning, setWarning] = useState<string | null>(null);
  const [originalFilename, setOriginalFilename] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      try {
        const text = await file.text();
        setInputText(text);
        setOriginalFilename(file.name);
      } catch (err) {
        setError("Failed to read file");
      }
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      try {
        const text = await file.text();
        setInputText(text);
        setOriginalFilename(file.name);
      } catch (err) {
        setError("Failed to read file");
      }
    }
    e.target.value = "";
  };

  const handleClean = async () => {
    if (!inputText.trim()) return;
    setError(null);
    setStatus("Cleaning... 0%");
    try {
      await streamRedact(
        inputText,
        (step, progress) => setStatus(`Cleaning... ${step} ${progress}%`),
        (result) => {
          setRedactedText(result.redacted_text);
          setMapping(result.mapping ?? {});
          setWarning(result.warning ?? null);
          setViewMode("preview");
          setStatus(null);
        },
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Redact failed");
      setStatus(null);
    }
  };

  const handleBackToInput = () => {
    setViewMode("input");
    setRedactedText("");
    setMapping({});
    setWarning(null);
    setStatus(null);
  };

  if (viewMode === "preview") {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-gray-800">Clean Logs</h1>
        <div className="mt-4 space-y-4">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleBackToInput}
              className="rounded bg-gray-200 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-300"
            >
              Back to input
            </button>
          </div>
          <pre className="whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-4 text-sm">
            {redactedText}
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-gray-800">Clean Logs</h1>
      <div className="mt-4 space-y-4">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`rounded-lg border-2 border-dashed p-4 transition-colors ${
            dragging ? "border-blue-500 bg-blue-50" : "border-gray-300"
          }`}
        >
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onFocus={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
            placeholder="Drop a file or paste log text..."
            className="h-48 w-full resize-none rounded border-0 bg-transparent p-2 text-gray-800 focus:outline-none"
            aria-label="Log text input"
          />
          {!inputText && (
            <p className="text-sm text-gray-500">Drop a file or paste to get started</p>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={handleFileSelect}
        />
        <button
          type="button"
          onClick={handleClean}
          disabled={!inputText.trim()}
          className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Clean
        </button>
        {status && (
          <div className="text-sm text-gray-600" role="status">
            {status}
          </div>
        )}
        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
