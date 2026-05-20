import React from "react";
export function DoorToDoorErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="notice notice-error d2d-error-state" role="alert">
      <div>
        <strong>No hemos podido completar todas las fuentes.</strong>
        <p>{message || "Te mostramos las opciones con datos suficientes cuando estén disponibles."}</p>
      </div>
      <button className="btn-secondary btn-compact" type="button" onClick={onRetry}>Reintentar</button>
    </section>
  );
}
