import Link from "next/link";

const tabs = [
  { id: "busqueda", label: "Búsqueda", href: "/preferencias/busqueda", desc: "Cómo quieres buscar por defecto." },
  { id: "puerta-a-puerta", label: "Puerta a puerta", href: "/preferencias/puerta-a-puerta", desc: "Ubicación habitual para rutas completas." },
  { id: "apariencia", label: "Apariencia", href: "/preferencias/apariencia", desc: "Tema, densidad y accesibilidad." },
  { id: "region", label: "Idioma y región", href: "/preferencias/region", desc: "Idioma, moneda y formatos regionales." },
] as const;

type SearchParamsShape = {
  [key: string]: string | string[] | undefined;
};

type PageProps = {
  searchParams?: Promise<SearchParamsShape>;
};

export default async function PreferenciasHubPage({ searchParams }: PageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;

  const selected = typeof resolvedSearchParams?.tab === "string" ? resolvedSearchParams.tab : "busqueda";

  return (
    <main className="shell" id="main-content">
      <div className="page-header">
        <div className="page-title">
          <h1>Preferencias</h1>
          <p>Un único punto para ajustar búsqueda, apariencia y región.</p>
        </div>
      </div>

      <section className="panel panel-soft stack">
        <div className="row-actions" role="tablist" aria-label="Secciones de preferencias">
          {tabs.map((tab) => {
            const isActive = selected === tab.id;
            return (
              <Link
                key={tab.id}
                href={tab.href}
                className={`btn-ghost btn-compact${isActive ? " is-active" : ""}`}
                role="tab"
                aria-selected={isActive}
              >
                {tab.label}
              </Link>
            );
          })}
        </div>

        <div className="stack">
          {tabs.map((tab) => (
            <article key={tab.id} className="panel panel-soft">
              <div className="panel-header">
                <h2>{tab.label}</h2>
                <Link href={tab.href} className="btn-primary btn-compact">
                  Abrir sección
                </Link>
              </div>
              <p className="panel-note">{tab.desc}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
