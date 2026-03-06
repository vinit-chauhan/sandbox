import { NavLink, Outlet } from "react-router-dom";
import { ROUTE_CONFIG } from "../routes/config";

export default function AppLayout() {
  return (
    <div className="flex h-screen flex-col">
      <header className="flex w-full shrink-0 flex-row items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <span className="text-lg font-semibold text-gray-800">Sandbox</span>
        <nav className="flex gap-4">
          {ROUTE_CONFIG.map(({ path, label }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                isActive
                  ? "font-medium text-blue-600 underline"
                  : "text-gray-600 hover:text-gray-900"
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
