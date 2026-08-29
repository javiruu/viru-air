import { BoneyardList, BoneyardPanel, LoadReference } from "@/modules/shared/BoneyardLoad";

export default function PrivateLoading() {
  return (
    <main className="shell section-gap-lg" id="main-content" aria-busy="true">
      <BoneyardPanel name="private-module-load" ariaLabel="Cargando modulo privado">
        <LoadReference shape="chip" width={180} height={18} />
        <LoadReference width="64%" />
        <LoadReference width="46%" />
      </BoneyardPanel>

      <section className="split section-gap">
        <BoneyardList name="private-list-load" rows={4} ariaLabel="Cargando datos de lista" />
        <BoneyardPanel name="private-summary-load" ariaLabel="Cargando resumen">
          <LoadReference shape="chip" width={150} height={18} />
          <LoadReference width="82%" />
          <LoadReference width="58%" />
          <LoadReference shape="card" />
        </BoneyardPanel>
      </section>
    </main>
  );
}
