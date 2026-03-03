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
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity text-xs"
            title="Delete"
          >
            &#x2715;
          </button>
        </div>
      ))}
    </div>
  );
}
