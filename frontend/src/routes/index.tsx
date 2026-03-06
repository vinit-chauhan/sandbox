import { useRoutes } from "react-router-dom";
import AppLayout from "../layouts/AppLayout";
import { ROUTE_CONFIG } from "./config";

export { ROUTE_CONFIG } from "./config";

export function AppRoutes() {
  const routes = useRoutes([
    {
      path: "/",
      element: <AppLayout />,
      children: [
        { index: true, element: ROUTE_CONFIG[0].element },
        { path: "redact", element: ROUTE_CONFIG[1].element },
      ],
    },
  ]);
  return routes;
}
