import { notFound } from "next/navigation";

import {
  BoneyardForm,
  BoneyardInline,
  BoneyardList,
  BoneyardLoad,
  BoneyardOverlay,
  BoneyardPanel,
  LoadReference,
} from "@/modules/shared/BoneyardLoad";

const panelLoads = [
  "app-root-load",
  "public-context-load",
  "landing-session-load",
  "landing-preview-session-load",
  "private-module-load",
  "private-summary-load",
  "watchlist-map-load",
  "auth-guard-load",
  "admin-access-load",
  "admin-product-health-load",
  "hotel-observability-access-load",
  "help-page-load",
] as const;

const formLoads = [
  "public-route-load",
  "register-session-load",
  "login-session-load",
  "forgot-password-session-load",
  "preferences-region-load",
  "preferences-appearance-load",
  "preferences-search-load",
] as const;

const listLoads = ["private-list-load", "admin-checks-load", "watchlist-compare-load"] as const;

const compactLoads = [
  "public-topbar-load",
  "admin-metrics-load",
  "hotel-observability-load",
  "door-to-door-preferences-load",
  "account-security-activity-load",
  "account-profile-load",
  "watch-live-flight-load",
  "watch-detail-history-load",
  "watchlist-list-load",
  "watch-history-load",
  "quick-search-progress-load",
  "door-to-door-results-load",
  "community-popular-destinations-load",
  "community-corridors-load",
] as const;

function CardReferences({ count, lines = 3 }: { count: number; lines?: number }) {
  return (
    <div className="boneyard-reference-row">
      {Array.from({ length: count }).map((_, cardIndex) => (
        <div className="boneyard-stack" key={`capture-card-${cardIndex}`}>
          {Array.from({ length: lines }).map((__, lineIndex) => (
            <LoadReference key={`capture-card-${cardIndex}-line-${lineIndex}`} width={`${76 - lineIndex * 14}%`} />
          ))}
        </div>
      ))}
    </div>
  );
}

function ListReferences({ rows, badge = true }: { rows: number; badge?: boolean }) {
  return (
    <div className="boneyard-list-reference">
      {Array.from({ length: rows }).map((_, index) => (
        <article className="boneyard-list-reference-row" key={`capture-list-row-${index}`}>
          <div className="boneyard-list-reference-main">
            <LoadReference width="58%" />
            <LoadReference width="42%" />
          </div>
          {badge ? <LoadReference shape="chip" width={74} height={22} /> : null}
        </article>
      ))}
    </div>
  );
}

function CompactReference({ name }: { name: (typeof compactLoads)[number] }) {
  switch (name) {
    case "public-topbar-load":
      return (
        <div className="boneyard-reference-row">
          <LoadReference shape="round" width={36} height={36} />
          <LoadReference shape="chip" width={164} height={28} />
        </div>
      );
    case "admin-metrics-load":
      return <CardReferences count={6} lines={2} />;
    case "hotel-observability-load":
      return (
        <div className="boneyard-stack">
          <CardReferences count={4} lines={2} />
          <LoadReference shape="card" height={124} />
        </div>
      );
    case "door-to-door-preferences-load":
      return <LoadReference width="64%" />;
    case "account-security-activity-load":
      return <ListReferences rows={3} />;
    case "account-profile-load":
      return (
        <div className="boneyard-stack">
          <LoadReference shape="round" width={64} height={64} />
          <LoadReference width="48%" />
          <LoadReference width="72%" />
          <LoadReference shape="chip" width={132} height={36} />
        </div>
      );
    case "watch-live-flight-load":
      return (
        <div className="boneyard-reference-row">
          <LoadReference shape="round" width={42} height={42} />
          <div className="boneyard-stack">
            <LoadReference width="68%" />
            <LoadReference width="42%" />
          </div>
        </div>
      );
    case "watch-detail-history-load":
      return <ListReferences rows={3} badge={false} />;
    case "watchlist-list-load":
      return <ListReferences rows={3} />;
    case "watch-history-load":
      return (
        <div className="boneyard-stack">
          <div className="boneyard-reference-row">
            <LoadReference shape="chip" width={116} height={28} />
            <LoadReference shape="chip" width={92} height={28} />
          </div>
          <LoadReference shape="card" height={148} />
          <ListReferences rows={3} badge={false} />
        </div>
      );
    case "quick-search-progress-load":
      return <CardReferences count={4} lines={4} />;
    case "door-to-door-results-load":
      return <CardReferences count={3} lines={3} />;
    case "community-popular-destinations-load":
      return (
        <div className="boneyard-reference-row">
          {Array.from({ length: 3 }).map((_, index) => (
            <LoadReference key={`capture-destination-${index}`} shape="chip" width={72} height={30} />
          ))}
        </div>
      );
    case "community-corridors-load":
      return (
        <div className="boneyard-stack">
          <div className="boneyard-reference-row">
            {Array.from({ length: 10 }).map((_, index) => (
              <LoadReference key={`capture-corridor-heat-${index}`} shape="block" height={17} />
            ))}
          </div>
          <ListReferences rows={5} badge={false} />
        </div>
      );
  }
}

type BoneyardCapturePageProps = {
  searchParams: Promise<{ review?: string | string[]; theme?: string | string[] }>;
};

export default async function BoneyardCapturePage({ searchParams }: BoneyardCapturePageProps) {
  if (process.env.NODE_ENV === "production") notFound();

  const { review, theme } = await searchParams;
  const isVisualReview = review === "1";
  const isDarkPreview = theme === "dark";

  return (
    <main className={`shell section-gap-lg${isDarkPreview ? " dark" : ""}`} aria-label="Boneyard capture fixtures">
      <section className="page-header">
        <p className="panel-subtitle">Captura de desarrollo para los estados de carga de Viru.</p>
        <h1 className="panel-title">Boneyard</h1>
      </section>

      <section className="split section-gap" aria-label="Paneles de carga">
        {panelLoads.map((name) => <BoneyardPanel key={name} name={name} ariaLabel="Cargando contenido" />)}
      </section>

      <section className="split section-gap" aria-label="Formularios de carga">
        {formLoads.map((name) => <BoneyardForm key={name} name={name} ariaLabel="Cargando formulario" />)}
      </section>

      <section className="split section-gap" aria-label="Listas de carga">
        {listLoads.map((name) => <BoneyardList key={name} name={name} ariaLabel="Cargando lista" rows={3} />)}
      </section>

      <section className="split section-gap" aria-label="Muestras compactas">
        {compactLoads.map((name) => (
          <BoneyardLoad key={name} name={name} className="panel panel-soft boneyard-panel" ariaLabel="Cargando módulo">
            <CompactReference name={name} />
          </BoneyardLoad>
        ))}
      </section>

      <BoneyardInline name="watch-detail-title-load" shape="chip" width={112} height={18} ariaLabel="Cargando detalle" />
      {!isVisualReview ? <BoneyardOverlay name="navigation-pending-load" ariaLabel="Cargando navegación" /> : null}
    </main>
  );
}
