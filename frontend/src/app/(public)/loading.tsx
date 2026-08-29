import { BoneyardForm, BoneyardLoad, BoneyardPanel, LoadReference } from "@/modules/shared/BoneyardLoad";

export default function PublicLoading() {
  return (
    <main className="shell glass-signin-shell" id="main-content" aria-busy="true">
      <BoneyardLoad name="public-topbar-load" className="panel panel-soft" ariaLabel="Cargando cabecera publica">
        <div className="glass-signin-topbar" aria-hidden="true">
          <LoadReference shape="chip" width={96} height={30} />
          <LoadReference shape="round" width={30} height={30} />
        </div>
      </BoneyardLoad>

      <BoneyardForm name="public-route-load" ariaLabel="Cargando vista publica">
        <LoadReference shape="chip" width={170} height={18} />
        <LoadReference width="72%" />
        <div className="boneyard-field-reference">
          <LoadReference width="34%" />
          <LoadReference shape="block" height={44} />
        </div>
        <div className="boneyard-field-reference">
          <LoadReference width="30%" />
          <LoadReference shape="block" height={44} />
        </div>
        <LoadReference shape="chip" width={142} height={36} className="boneyard-action-reference" />
      </BoneyardForm>

      <BoneyardPanel name="public-context-load" ariaLabel="Cargando contexto">
        <LoadReference width="62%" />
        <LoadReference width="48%" />
      </BoneyardPanel>
    </main>
  );
}
