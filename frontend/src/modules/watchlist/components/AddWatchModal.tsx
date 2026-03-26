import type { FormEventHandler } from "react";

type PickerField = "origin" | "destination";

type AddWatchModalProps = {
  isOpen: boolean;
  travelDate: string;
  origin: string;
  destination: string;
  targetPrice: string;
  onClose: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onTravelDateChange: (value: string) => void;
  onOriginChange: (value: string) => void;
  onDestinationChange: (value: string) => void;
  onTargetPriceChange: (value: string) => void;
  onOpenPicker: (field: PickerField) => void;
};

export function AddWatchModal({
  isOpen,
  travelDate,
  origin,
  destination,
  targetPrice,
  onClose,
  onSubmit,
  onTravelDateChange,
  onOriginChange,
  onDestinationChange,
  onTargetPriceChange,
  onOpenPicker,
}: AddWatchModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <section
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-label="Anadir vuelo"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h2 className="panel-title">Anadir vuelo</h2>
            <p className="panel-subtitle">Selecciona fecha y aeropuertos compatibles.</p>
          </div>
          <button className="modal-close" type="button" aria-label="Cerrar modal" onClick={onClose}>
            X
          </button>
        </div>

        <form className="form" onSubmit={onSubmit}>
          <label className="date-field field">
            Fecha
            <input
              type="date"
              name="travel_date"
              autoComplete="off"
              value={travelDate}
              onChange={(e) => onTravelDateChange(e.target.value)}
            />
          </label>

          <div className="airport-row">
            <label className="field">
              Origen (IATA)
              <input
                name="origin_iata"
                autoComplete="off"
                value={origin}
                onChange={(e) => onOriginChange(e.target.value.toUpperCase())}
                placeholder="MAD"
                disabled={!travelDate}
              />
              <small className="hint">
                {travelDate ? "Escribe el codigo o usa el selector." : "Selecciona fecha para habilitar."}
              </small>
            </label>
            <button type="button" className="btn-ghost" onClick={() => onOpenPicker("origin")} disabled={!travelDate}>
              Elegir aeropuerto
            </button>
          </div>

          <div className="airport-row">
            <label className="field">
              Destino (IATA)
              <input
                name="destination_iata"
                autoComplete="off"
                value={destination}
                onChange={(e) => onDestinationChange(e.target.value.toUpperCase())}
                placeholder="DUB"
                disabled={!travelDate}
              />
              <small className="hint">
                {travelDate ? "Escribe el codigo o usa el selector." : "Selecciona fecha para habilitar."}
              </small>
            </label>
            <button type="button" className="btn-ghost" onClick={() => onOpenPicker("destination")} disabled={!travelDate}>
              Elegir aeropuerto
            </button>
          </div>

          <label className="field">
            Precio objetivo (EUR)
            <input
              name="target_price"
              autoComplete="off"
              inputMode="decimal"
              value={targetPrice}
              onChange={(e) => onTargetPriceChange(e.target.value)}
              placeholder="39.99"
            />
          </label>

          <div className="cta-row">
            <button type="submit" className="btn-primary">
              Guardar
            </button>
            <button type="button" className="btn-ghost" onClick={onClose}>
              Cancelar
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
