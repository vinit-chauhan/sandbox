import { useState, useRef, type DragEvent } from "react";
import { streamRedact } from "../api/client";

const ACCEPTED =
  ".log,.txt,.json,.csv,.yml,.yaml,.conf,.config,.ini,.xml,.md,.text";

function downloadFilename(originalName: string): string {
  const lastDot = originalName.lastIndexOf(".");
  if (lastDot <= 0) return `${originalName}.clean`;
  return `${originalName.slice(0, lastDot)}.clean${originalName.slice(lastDot)}`;
}

interface Span {
  start: number;
  end: number;
  repl: string;
  origs: string[];
}

function buildHighlightSpans(
  text: string,
  mapping: Record<string, string>,
): Span[] {
  const rev = new Map<string, string[]>();
  for (const [orig, repl] of Object.entries(mapping)) {
    if (!rev.has(repl)) rev.set(repl, []);
    rev.get(repl)!.push(orig);
  }
  const replacements = [...new Set(Object.values(mapping))].sort(
    (a, b) => b.length - a.length,
  );
  const spans: Span[] = [];
  for (const repl of replacements) {
    if (!repl) continue;
    let pos = 0;
    while ((pos = text.indexOf(repl, pos)) >= 0) {
      spans.push({
        start: pos,
        end: pos + repl.length,
        repl,
        origs: rev.get(repl) ?? [],
      });
      pos += repl.length;
    }
  }
  spans.sort((a, b) => b.repl.length - a.repl.length);
  const filtered: Span[] = [];
  for (const s of spans) {
    const overlaps = filtered.some((f) => s.start < f.end && s.end > f.start);
    if (!overlaps) filtered.push(s);
  }
  return filtered.sort((a, b) => a.start - b.start);
}

type PiiType = "email" | "ip" | "hostname" | "username" | "path" | "other";

function inferPiiType(repl: string): PiiType {
  if (/user-\d+@example\.com/.test(repl)) return "email";
  if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(repl)) return "ip";
  if (/^[0-9a-f:]+$/i.test(repl) && repl.includes(":")) return "ip";
  if (/^(server|node|worker)-[a-z0-9-]+\.example\.com$/i.test(repl)) return "hostname";
  if (/^[a-z]+\.[a-z]+$/i.test(repl) && repl.length < 30) return "username";
  if (repl.includes("/")) return "path";
  return "other";
}

function countPiiByType(mapping: Record<string, string>): Record<PiiType, number> {
  const counts: Record<PiiType, number> = {
    email: 0,
    ip: 0,
    hostname: 0,
    username: 0,
    path: 0,
    other: 0,
  };
  for (const repl of Object.values(mapping)) {
    counts[inferPiiType(repl)]++;
  }
  return counts;
}

function renderHighlightedPreview(text: string, mapping: Record<string, string>) {
  const spans = buildHighlightSpans(text, mapping);
  if (spans.length === 0) return text;
  const segments: Array<{ type: "plain" | "mark"; start: number; end: number; repl?: string; origs?: string[] }> = [];
  let pos = 0;
  for (const s of spans) {
    if (s.start > pos) {
      segments.push({ type: "plain", start: pos, end: s.start });
    }
    segments.push({ type: "mark", start: s.start, end: s.end, repl: s.repl, origs: s.origs });
    pos = s.end;
  }
  if (pos < text.length) {
    segments.push({ type: "plain", start: pos, end: text.length });
  }
  return segments.map((seg) => {
    if (seg.type === "plain") {
      return text.slice(seg.start, seg.end);
    }
    const title = seg.origs?.length ? `Was: ${seg.origs.join(", ")}` : "";
    return (
      <mark key={seg.start} title={title} className="bg-yellow-200">
        {seg.repl}
      </mark>
    );
  });
}

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
  const [copied, setCopied] = useState(false);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
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
    setCopied(false);
    setSummaryExpanded(false);
  };

  const handleDownload = () => {
    const blob = new Blob([redactedText]);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadFilename(originalFilename ?? "output.txt");
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(redactedText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  };

  if (viewMode === "preview") {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-gray-800">Clean Logs</h1>
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleDownload}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Download
            </button>
            <button
              type="button"
              onClick={handleCopy}
              className="rounded bg-gray-200 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-300"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
            <button
              type="button"
              onClick={handleBackToInput}
              className="rounded bg-gray-200 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-300"
            >
              Back to input
            </button>
          </div>
          {warning && (
            <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              {warning}
            </div>
          )}
          <div className="rounded border border-gray-200 bg-gray-50">
            <button
              type="button"
              onClick={() => setSummaryExpanded((v) => !v)}
              className="flex w-full items-center justify-between px-4 py-2 text-left text-sm font-medium text-gray-700 hover:bg-gray-100"
            >
              Redaction summary ({Object.keys(mapping).length} changes)
            </button>
            {summaryExpanded && (
              <dl className="border-t border-gray-200 px-4 py-3 text-sm">
                {Object.entries(countPiiByType(mapping))
                  .filter(([, n]) => n > 0)
                  .map(([type, n]) => (
                    <div key={type} className="flex gap-2">
                      <dt className="font-medium capitalize text-gray-600">{type}:</dt>
                      <dd>{n}</dd>
                    </div>
                  ))}
              </dl>
            )}
          </div>
          <pre className="whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-4 text-sm">
            {renderHighlightedPreview(redactedText, mapping)}
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
