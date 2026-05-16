import type { CountryAirports, AirportMeta } from "@/modules/shared/airports";
import { COUNTRY_AIRPORTS, searchAirportsAsync } from "@/modules/shared/airports";
import { useState, useEffect } from "react";

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
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<AirportMeta[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchAirportsAsync(searchQuery);
        setSearchResults(results);
      } catch (err) {
        console.error("Search failed:", err);
      } finally {
        setIsSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  if (!activePicker) return null;

  const displayAirports = searchQuery.trim().length >= 2 
    ? searchResults 
    : (selectedCountry?.airports || []);

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
              {activePicker === "destination" && (
                <button type="button" className="link-reset" onClick={() => onSelectAirport("ANY")}>
                  A cualquier lugar
                </button>
              )}
              <button type="button" className="modal-close" aria-label="Cerrar selector de aeropuerto" onClick={onClose}>
                X
              </button>
            </div>
          </div>

          <div className="airport-list">
            <input 
              type="text" 
              className="ui-input" 
              placeholder="Buscar aeropuerto o ciudad..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ marginBottom: "1rem" }}
            />
            {isSearching && <p className="muted">Buscando...</p>}
            {!isSearching && displayAirports.length === 0 && searchQuery.trim().length >= 2 && (
              <p className="muted">No se encontraron aeropuertos.</p>
            )}
            {!isSearching && displayAirports.map((airport) => {
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
