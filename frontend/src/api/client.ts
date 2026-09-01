export interface Doc {
  id: string;
  name: string;
}

export interface ChatTiming {
  ttft: number;
  total: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  timing?: ChatTiming;
}

export interface ChatRequest {
  message: string;
  document_ids?: string[];
  history: Message[];
  enable_thinking?: boolean;
}

export async function uploadFile(file: File): Promise<Doc> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function getDocuments(): Promise<Doc[]> {
  const res = await fetch("/api/documents");
  if (!res.ok) throw new Error(`Fetch documents failed: ${res.statusText}`);
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`/api/documents/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete failed: ${res.statusText}`);
}

export async function streamChat(
  req: ChatRequest,
  onToken: (token: string) => void,
  onThinking?: (token: string) => void,
): Promise<ChatTiming> {
  const start = performance.now();
  let ttft = 0;
  let firstContentToken = true;

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;
      const payload = trimmed.slice(6);
      if (payload === "[DONE]") {
        return { ttft, total: performance.now() - start };
      }
      try {
        const parsed = JSON.parse(payload);
        if (parsed.type === "thinking" && parsed.token && onThinking) {
          onThinking(parsed.token);
        } else if (parsed.token) {
          if (firstContentToken) {
            ttft = performance.now() - start;
            firstContentToken = false;
          }
          onToken(parsed.token);
        }
      } catch {
        // skip malformed lines
      }
    }
  }

  return { ttft, total: performance.now() - start };
}

export async function streamRedact(
  text: string,
  onProgress: (step: string, progress: number, chunk?: number, totalChunks?: number) => void,
  onDone: (result: {
    redacted_text: string;
    mapping: Record<string, string>;
    warning?: string | null;
  }) => void,
): Promise<void> {
  const res = await fetch("/api/redact", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) throw new Error(`Redact failed: ${res.statusText}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;
      const payload = trimmed.slice(6);
      try {
        const parsed = JSON.parse(payload);
        if (parsed.step === "done") {
          onDone({
            redacted_text: parsed.redacted_text ?? "",
            mapping: parsed.mapping ?? {},
            warning: parsed.warning ?? null,
          });
          return;
        }
        if (parsed.step != null && parsed.progress != null) {
          onProgress(parsed.step, parsed.progress, parsed.chunk, parsed.total_chunks);
        }
      } catch {
        // skip malformed lines
      }
    }
  }
}
