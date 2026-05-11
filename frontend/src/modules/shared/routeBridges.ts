const ROUTE_BRIDGES: Record<string, string> = {
  "/history": "/watchlist",
  "/preferences": "/preferencias",
  "/suggestions": "/soporte/feedback?type=idea",
  "/preferencias/busqueda": "/preferencias?tab=busqueda",
  "/preferencias/apariencia": "/preferencias?tab=apariencia",
  "/preferencias/region": "/preferencias?tab=region",
};

export function resolveBridgeRoute(path: string): string {
  return ROUTE_BRIDGES[path] ?? path;
}
