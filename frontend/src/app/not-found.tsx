import Link from "next/link";

export default function NotFound() {
  return (
    <main className="not-found" id="main-content">
      <section className="sky-door-card">
        <h1 className="door-title">Viru Tracker no encontro esta ruta</h1>
        <p className="door-description">
          La puerta que buscas no existe en el mapa de vuelo. Revisa la ruta o vuelve al panel principal.
        </p>
        <div className="sky-door">
          <div className="door-left">
            <span className="door-handle"></span>
          </div>
          <div className="door-right">
            <span className="door-handle"></span>
          </div>
          <div className="door-content">
            <p className="door-message">Viru no puede aterrizar aqui.</p>
            <div className="action-buttons">
              <Link className="btn" href="/dashboard">Ir al panel</Link>
              <Link className="btn" href="/login">Iniciar sesion</Link>
            </div>
          </div>
        </div>
        <small className="muted">Error 404 · Ruta perdida en seguimiento</small>
      </section>
    </main>
  );
}
