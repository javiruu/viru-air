const ROUTE_BRIDGES: Record<string, string> = {
  "/history": "/watchlist",
  "/preferences": "/preferencias",
  "/preferencias/busqueda": "/preferencias?tab=busqueda",
  "/preferencias/apariencia": "/preferencias?tab=apariencia",
  "/preferencias/region": "/preferencias?tab=region",
};

export function resolveBridgeRoute(path: string): string {
  return ROUTE_BRIDGES[path] ?? path;
}
