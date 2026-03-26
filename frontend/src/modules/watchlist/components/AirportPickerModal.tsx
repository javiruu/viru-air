import type { CountryAirports } from "@/modules/shared/airports";
import { COUNTRY_AIRPORTS } from "@/modules/shared/airports";

type PickerField = "origin" | "destination";

type AirportPickerModalProps = {
  activePicker: PickerField | null;
  selectedCountry: CountryAirports | null;
  compatibleOrigins: string[];
  compatibleDestinations: string[];
  onClose: () => void;
  onSelectCountry: (country: CountryAirports) => void;
  onClearSelection: () => void;
  onSelectAirport: (iata: string) => void;
};

export function AirportPickerModal({
  activePicker,
  selectedCountry,
  compatibleOrigins,
  compatibleDestinations,
  onClose,
  onSelectCountry,
  onClearSelection,
  onSelectAirport,
}: AirportPickerModalProps) {
  if (!activePicker) return null;

  return (
    <div className="airport-modal-overlay" onClick={onClose}>
      <section
        className="airport-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Elegir aeropuerto"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="airport-modal-left">
          <h2>{activePicker === "origin" ? "Pais de origen" : "Pais de destino"}</h2>
          <div className="airport-country-grid">
            {COUNTRY_AIRPORTS.map((country) => {
              const isActive = selectedCountry?.code === country.code;
              return (
                <button
                  key={country.code}
                  type="button"
                  className={isActive ? "country-pill active" : "country-pill"}
                  onClick={() => onSelectCountry(country)}
                >
                  {country.name}
                </button>
              );
            })}
          </div>
        </div>

        <div className="airport-modal-right">
          <div className="airport-modal-header">
            <h3>Elegir aeropuerto</h3>
            <div className="airport-modal-tools">
              <button type="button" className="link-reset" onClick={onClearSelection}>
                Borrar seleccion
              </button>
              <button type="button" className="modal-close" aria-label="Cerrar selector de aeropuerto" onClick={onClose}>
                X
              </button>
            </div>
          </div>

          <div className="airport-list">
            {(selectedCountry?.airports || []).map((airport) => {
              const allowed =
                activePicker === "origin"
                  ? compatibleOrigins.length === 0 || compatibleOrigins.includes(airport.iata)
                  : compatibleDestinations.length === 0 || compatibleDestinations.includes(airport.iata);

              return (
                <button key={airport.iata} type="button" onClick={() => onSelectAirport(airport.iata)} disabled={!allowed}>
                  {airport.name} <span>{airport.iata}</span>
                </button>
              );
            })}
          </div>

          <p className="muted section-gap-sm">La compatibilidad se valida en tiempo real segun rutas disponibles.</p>
        </div>
      </section>
    </div>
  );
}
