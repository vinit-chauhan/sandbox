import { useState, useEffect, useCallback } from "react";
import { type Doc, getDocuments } from "./api/client";
import FileUpload from "./components/FileUpload";
import DocumentList from "./components/DocumentList";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [checkedIds, setCheckedIds] = useState<string[]>([]);

  useEffect(() => {
    getDocuments().then(setDocs).catch(console.error);
  }, []);

  const handleUploaded = useCallback((doc: Doc) => {
    setDocs((prev) => [...prev, doc]);
    setCheckedIds((prev) => [...prev, doc.id]);
  }, []);

  const handleDeleted = useCallback((id: string) => {
    setDocs((prev) => prev.filter((d) => d.id !== id));
    setCheckedIds((prev) => prev.filter((cid) => cid !== id));
  }, []);

  const handleToggle = useCallback((id: string) => {
    setCheckedIds((prev) =>
      prev.includes(id) ? prev.filter((cid) => cid !== id) : [...prev, id],
    );
  }, []);

  return (
    <div className="flex h-screen">
      <aside className="w-80 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-lg font-semibold text-gray-800">
            Local LLM Chat
          </h1>
        </div>
        <div className="p-4 border-b border-gray-200">
          <FileUpload onUploaded={handleUploaded} />
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <DocumentList
            docs={docs}
            checkedIds={checkedIds}
            onToggle={handleToggle}
            onDeleted={handleDeleted}
          />
        </div>
      </aside>
      <main className="flex-1 flex flex-col bg-gray-50">
        <ChatWindow activeDocIds={checkedIds} />
      </main>
    </div>
  );
}
