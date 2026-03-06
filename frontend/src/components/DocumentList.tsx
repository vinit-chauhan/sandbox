import { type Doc, deleteDocument } from "../api/client";

interface Props {
  docs: Doc[];
  checkedIds: string[];
  onToggle: (id: string) => void;
  onDeleted: (id: string) => void;
}

export default function DocumentList({
  docs,
  checkedIds,
  onToggle,
  onDeleted,
}: Props) {
  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      onDeleted(id);
    } catch (err) {
      console.error("Delete error:", err);
    }
  };

  if (docs.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center">No documents yet</p>
    );
  }

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
        Documents
      </p>
      {docs.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center gap-2 group rounded-md px-2 py-1.5 hover:bg-gray-50"
        >
          <input
            type="checkbox"
            checked={checkedIds.includes(doc.id)}
            onChange={() => onToggle(doc.id)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="flex-1 text-sm text-gray-700 truncate">
            {doc.name}
          </span>
          <button
            onClick={() => handleDelete(doc.id)}
            className="shrink-0 rounded p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
            title="Delete"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
