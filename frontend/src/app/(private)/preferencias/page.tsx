import Link from "next/link";

const tabs = [
  { id: "busqueda", label: "Búsqueda", href: "/preferencias/busqueda", desc: "Tu base para Búsqueda rápida." },
  { id: "puerta-a-puerta", label: "Puerta a puerta", href: "/preferencias/puerta-a-puerta", desc: "Origen habitual." },
  { id: "apariencia", label: "Apariencia", href: "/preferencias/apariencia", desc: "Tema y densidad." },
  { id: "region", label: "Idioma y región", href: "/preferencias/region", desc: "Idioma, moneda y formatos." },
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
          <p>Ajusta búsqueda, apariencia y región en un solo lugar.</p>
        </div>
      </div>

      <section className="panel panel-soft stack prefs-hub-tabs">
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

        <div className="stack prefs-hub-stack">
          <article className="panel prefs-hub-primary">
            <div className="panel-header">
              <div>
                <p className="prefs-kicker">Base de búsqueda</p>
                <h2>Búsqueda</h2>
              </div>
              <Link href="/preferencias/busqueda" className="btn-primary btn-compact">
                Abrir sección
              </Link>
            </div>
            <p className="panel-note">Tu base para Búsqueda rápida.</p>
          </article>

          <div className="prefs-hub-secondary-grid">
            {tabs.filter((tab) => tab.id !== "busqueda").map((tab) => (
              <article key={tab.id} className="panel panel-soft prefs-hub-secondary">
                <div className="panel-header">
                  <h2>{tab.label}</h2>
                  <Link href={tab.href} className="btn-ghost btn-compact">
                    Abrir
                  </Link>
                </div>
                <p className="panel-note">{tab.desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
