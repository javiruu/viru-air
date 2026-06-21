"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type TocItem = {
  id: string;
  label: string;
};

const tocItems: TocItem[] = [
  { id: "resumen-ejecutivo", label: "Resumen ejecutivo" },
  { id: "indice-navegable", label: "Índice navegable" },
  { id: "uso-responsable", label: "Uso responsable" },
  { id: "alcance-límites", label: "Alcance del servicio y límites" },
  { id: "datos-proveedor", label: "Datos de proveedor y calidad del dato" },
  { id: "alertas-recomendaciones", label: "Alertas, recomendaciones y predicciónes" },
  { id: "privacidad", label: "Privacidad y protección de datos" },
  { id: "conservación", label: "Conservación, borrado y portabilidad" },
  { id: "seguridad-cuenta", label: "Seguridad de cuenta y sesiónes" },
  { id: "cookies-telemetría", label: "Cookies, analítica y telemetría" },
  { id: "políticas-país", label: "Consejos y políticas por país" },
  { id: "deeplink-terceros", label: "Redireccion a Ryanair y terceros" },
  { id: "no-asesoramiento", label: "Exención de responsabilidad" },
  { id: "cambios-política", label: "Cambios de política y versiónes" },
  { id: "contacto-legal", label: "Contacto legal y privacidad" },
  { id: "derechos-simple", label: "Tus derechos, en simple" },
  { id: "faq", label: "FAQ" },
  { id: "cta-final", label: "Acciones finales" },
];

export default function PoliciesPage() {
  const [activeId, setActiveId] = useState<string>(tocItems[0]?.id ?? "");
  const [isIndexOpen, setIsIndexOpen] = useState(false);

  const observerIds = useMemo(() => tocItems.map((item) => item.id), []);

  useEffect(() => {
    const headings = observerIds
      .map((id) => document.getElementById(id))
      .filter((node): node is HTMLElement => Boolean(node));

    if (!headings.length) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (visible[0]?.target?.id) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: [0, 0.2, 0.6] },
    );

    headings.forEach((heading) => observer.observe(heading));

    return () => observer.disconnect();
  }, [observerIds]);

  return (
    <main className="shell policies-shell cycle4-page policies-page" id="main-content">
      <header className="policies-hero" id="policies-top">
        <div className="policies-hero-header">
          <Link href="/" className="btn-ghost">Atrás</Link>
          <div className="policies-hero-actions">
            <Link href="/dashboard" className="btn-ghost">Volver al panel</Link>
          </div>
        </div>
        <div className="policies-hero-copy">
          <h1>Políticas y Transparencia</h1>
          <p>
            En Viru priorizamos la claridad, el control del usuario y límites honestos sobre lo que podemos y
            no podemos garantizar.
          </p>
          <div className="policies-meta">
            <span><strong>Ultima actualización:</strong> 17 Feb 2026</span>
            <span><strong>Version:</strong> 1.0</span>
            <span><strong>Idioma:</strong> ES</span>
            <span><strong>Tiempo de lectura:</strong> 12 min</span>
          </div>
        </div>
      </header>

      <div className="notice notice-info policies-context-note" role="status" aria-live="polite">
        Esta política resume el estado operativo actual y se actualiza cuando cambian procesos relevantes.
      </div>

      <section id="resumen-ejecutivo" className="policies-tldr">
        <div className="policies-tldr-header">
          <div>
            <h2>Resumen ejecutivo (TL;DR)</h2>
            <p>Lo esencial, sin tecnicismos.</p>
          </div>
          <span className="badge badge-transparency">Transparencia</span>
        </div>
        <ul>
          <li>Viru es una herramienta informativa de seguimiento, no una garantía de precio final.</li>
          <li>Las fuentes externas pueden fallar o cambiar sin aviso; mostramos el ultimo dato confirmado.</li>
          <li>Guardamos datos necesarios para operar tu watchlist, alertas y preferencias.</li>
          <li>Las alertas y recomendaciones son orientativas, nunca asesoramiento financiero.</li>
          <li>Puedes solicitar eliminación, portabilidad y acceso desde tu cuenta o soporte.</li>
          <li>No compartimos credenciales ni tokens con terceros.</li>
          <li>Si el proveedor falla, reducimos consultas y mostramos cuando se comprobo el ultimo dato.</li>
          <li>El contenido de políticas se revisa periodicamente y refleja el estado operativo documentado.</li>
        </ul>
      </section>

      <section id="indice-navegable" className="policies-index">
        <div className="policies-index-header">
          <h2>Índice navegable</h2>
          <button
            type="button"
            className="btn-ghost policies-index-toggle"
            aria-expanded={isIndexOpen}
            aria-controls="policies-toc"
            onClick={() => setIsIndexOpen((value) => !value)}
          >
            {isIndexOpen ? "Cerrar indice" : "Abrir indice"}
          </button>
        </div>
        <nav id="policies-toc" className={`policies-toc ${isIndexOpen ? "open" : ""}`} aria-label="Índice de políticas">
          {tocItems.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className={`policies-toc-item ${activeId === item.id ? "active" : ""}`}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </section>

      <div className="policies-layout">
        <div className="policies-content">
          <section id="uso-responsable" className="policies-section">
            <div className="policies-section-header">
              <h2>Uso responsable</h2>
              <span className="badge badge-important">Importante</span>
            </div>
            <p>
              Viru existe para ayudarte a tomar decisiones informadas. No sustituye la verificacion final en la
              web del proveedor. Si ves una oportunidad, confirma siempre el precio y las condiciones antes de
              comprar.
            </p>
            <p>
              Ejemplo: si el proveedor no responde en un momento puntual, mostramos el ultimo dato confirmado con
              la hora de su ultima comprobacion. Esto evita datos inventados o silencios confusos.
            </p>
          </section>

          <section id="alcance-límites" className="policies-section">
            <div className="policies-section-header">
              <h2>Alcance del servicio y límites</h2>
              <span className="badge badge-limitation">Limitación</span>
            </div>
            <p>
              Viru cubre seguimiento, comparativas y alertas sobre precios observados. No procesa pagos ni
              controla inventario. Tampoco garantiza disponibilidad, cupos o precio final en el checkout.
            </p>
            <p>
              Cuando solo podemos ofrecer resultados parciales reducimos llamadas al proveedor y priorizamos
              estabilidad. En ese estado veras cuando se comprobo el ultimo dato y posibles retrasos de actualizacion.
            </p>
          </section>

          <section id="datos-proveedor" className="policies-section">
            <div className="policies-section-header">
              <h2>Datos de proveedor y calidad del dato</h2>
              <span className="badge badge-transparency">Transparencia</span>
            </div>
            <p>
              Las fuentes externas pueden cambiar, fallar o responder con variaciones. Diferenciamos entre dato
              observado, dato estimado y predicción:
            </p>
            <ul className="policies-list">
              <li><strong>Observado:</strong> precio recibido directamente del proveedor.</li>
              <li><strong>Estimado:</strong> valor derivado por reglas internas cuando falta granularidad.</li>
              <li><strong>Prediccion:</strong> proyeccion con nivel de confianza variable.</li>
            </ul>
            <p>
              Si el proveedor no responde, mostramos el ultimo dato confirmado con su ultima comprobacion y evitamos
              mezclarlo con valores nuevos.
            </p>
          </section>

          <section id="alertas-recomendaciones" className="policies-section">
            <div className="policies-section-header">
              <h2>Alertas, recomendaciones y predicciónes</h2>
              <span className="badge badge-control">Tu control</span>
            </div>
            <p>
              Las alertas se configuran por umbral, cambios bruscos o ventanas de tiempo. Si activas una alerta por
              umbral, Viru compara contra el ultimo precio observado y te notifica cuando se cumple.
            </p>
            <p>
              Las recomendaciones son orientativas y no equivalen a asesoramiento financiero. Cuando una
              recomendacion tiene baja confianza, lo indicamos de forma visible para que decidas con criterio.
            </p>
          </section>

          <section id="privacidad" className="policies-section">
            <div className="policies-section-header">
              <h2>Privacidad y protección de datos</h2>
              <span className="badge badge-important">Importante</span>
            </div>
            <p>
              Guardamos los datos necesarios para operar: cuenta, rutas observadas, alertas, preferencias de
              idioma y ajustes de interfaz. No compartimos credenciales ni tokens con terceros.
            </p>
            <p>
              Registramos eventos técnicos para calidad y seguridad: intentos de acceso, errores de proveedor,
              tiempos de respuesta y acciones criticas (por ejemplo, crear una alerta o cambiar preferencias).
              Nunca usamos estos eventos para perfilado publicitario.
            </p>
          </section>

          <section id="conservación" className="policies-section">
            <div className="policies-section-header">
              <h2>Conservación, borrado y portabilidad</h2>
              <span className="badge badge-control">Tu control</span>
            </div>
            <p>
              Puedes solicitar eliminación de datos desde tu cuenta o escribiendo a soporte. La portabilidad
              aplica a datos que has generado: watchlists, alertas y preferencias.
            </p>
            <div className="policies-table">
              <div className="policies-table-row header">
                <div>Etapa</div>
                <div>Detalle</div>
                <div>Plazo</div>
              </div>
              <div className="policies-table-row">
                <div>Solicitud</div>
                <div>Formulario en cuenta o email a soporte.</div>
                <div>Al recibirla</div>
              </div>
              <div className="policies-table-row">
                <div>Verificacion</div>
                <div>Confirmamos identidad para evitar borrados accidentales.</div>
                <div>Segun complejidad</div>
              </div>
              <div className="policies-table-row">
                <div>Ejecucion</div>
                <div>Eliminamos datos personales y desvinculamos historicos cuando aplica.</div>
                <div>Segun proceso operativo</div>
              </div>
              <div className="policies-table-row">
                <div>Confirmacion</div>
                <div>Recibes una notificacion con el estado final.</div>
                <div>Tras finalizar el proceso</div>
              </div>
            </div>
          </section>

          <section id="seguridad-cuenta" className="policies-section">
            <div className="policies-section-header">
              <h2>Seguridad de cuenta y sesiónes</h2>
              <span className="badge badge-important">Importante</span>
            </div>
            <p>
              Mantienes el control total de tus sesiónes. Si detectas actividad sospechosa, cierra sesión desde
              el panel y cambia tu password. No compartas credenciales ni tokens con terceros.
            </p>
            <p>
              Usamos sesiónes con expiración y controles de invalidación de acceso. Si un dispositivo queda inactivo,
              la sesión puede invalidarse para reducir riesgo.
            </p>
          </section>

          <section id="cookies-telemetría" className="policies-section">
            <div className="policies-section-header">
              <h2>Cookies, analítica y telemetría</h2>
              <span className="badge badge-transparency">Transparencia</span>
            </div>
            <p>
              Usamos cookies estrictamente necesarias para mantener tu sesión y preferencias. La telemetría se
              limita a calidad de servicio: tiempos de respuesta, errores y rendimiento.
            </p>
            <p>
              Si en tu entorno existe ajuste de analítica, podrás modificarlo desde preferencias. En ese caso, Viru
              mantiene las funciones esenciales y puede reducir la visibilidad diagnóstica para mejorar la experiencia.
            </p>
          </section>

          <section id="políticas-país" className="policies-section">
            <div className="policies-section-header">
              <h2>Consejos y políticas por país</h2>
              <span className="badge badge-transparency">Transparencia</span>
            </div>
            <p>
              Viru puede mostrar contenido contextual por país (moneda, idioma y recomendaciones operativas).
              Cuando haya cambios relevantes, se actualizan en esta política con fecha de revisión.
            </p>
            <p>
              Esto permite i18n futuro sin reescribir la política completa. Si tu país requiere informacion
              adicional, la veras en esta misma sección.
            </p>
          </section>

          <section id="deeplink-terceros" className="policies-section">
            <div className="policies-section-header">
              <h2>Redireccion a Ryanair (deep-link) y terceros</h2>
              <span className="badge badge-limitation">Limitación</span>
            </div>
            <p>
              Viru genera deep-links para facilitar el acceso al proveedor. Al hacer clic, sales de Viru y pasas
              a un entorno de terceros, con sus propias condiciones y políticas.
            </p>
            <p>
              Si el deep-link falla, mostramos un enlace alternativo y avisamos. No controlamos cambios de precio
              ni disponibilidad una vez fuera de Viru.
            </p>
          </section>

          <section id="no-asesoramiento" className="policies-section">
            <div className="policies-section-header">
              <h2>Exención de responsabilidad y no asesoramiento financiero</h2>
              <span className="badge badge-limitation">Limitación</span>
            </div>
            <p>
              Viru no ofrece asesoramiento financiero, legal ni fiscal. Las alertas y recomendaciones son guias
              informativas basadas en datos observados.
            </p>
            <p>
              La compra final depende del proveedor. No garantizamos precios, condiciones ni disponibilidad.
            </p>
          </section>

          <section id="cambios-política" className="policies-section">
            <div className="policies-section-header">
              <h2>Cambios de política y control de versiónes</h2>
              <span className="badge badge-transparency">Transparencia</span>
            </div>
            <p>
              Cualquier cambio relevante se comunica en el panel y queda reflejado con versión y fecha de
              actualización en esta página. Algunos módulos pueden tener documentación adicional cuando aplique.
            </p>
            <p>
              Puedes consultar el resumen de cambios en esta misma pagina y decidir si deseas continuar usando
              Viru o solicitar la eliminación de datos.
            </p>
          </section>

          <section id="contacto-legal" className="policies-section">
            <div className="policies-section-header">
              <h2>Contacto legal / soporte privacidad</h2>
              <span className="badge badge-control">Tu control</span>
            </div>
            <p>
              Para consultas legales o privacidad puedes escribir a soporte. Responderemos en el menor tiempo
              posible con un lenguaje claro.
            </p>
            <p>
              Email: <a className="linkInline" href="mailto:privacidad@viru.app">privacidad@viru.app</a>
            </p>
          </section>

          <section id="derechos-simple" className="policies-section">
            <div className="policies-section-header">
              <h2>Tus derechos, en simple</h2>
              <span className="badge badge-control">Tu control</span>
            </div>
            <div className="policies-rights">
              <details>
                <summary>Acceso</summary>
                <p>Puedes pedir copia de los datos que tenemos sobre tu cuenta y actividad.</p>
              </details>
              <details>
                <summary>Rectificación</summary>
                <p>Si algo no es correcto, lo ajustamos tras verificar tu identidad.</p>
              </details>
              <details>
                <summary>Eliminacion</summary>
                <p>Solicita borrado total desde tu cuenta o vía soporte.</p>
              </details>
              <details>
                <summary>Limitación u oposicion</summary>
                <p>Reducimos el tratamiento de datos cuando existe un motivo legítimo.</p>
              </details>
              <details>
                <summary>Portabilidad</summary>
                <p>Te entregamos tus datos en formato exportable cuando aplique.</p>
              </details>
              <details>
                <summary>Retirada de consentimiento</summary>
                <p>Puedes cambiar ajustes de analítica o notificaciones en preferencias.</p>
              </details>
            </div>
          </section>

          <section id="faq" className="policies-section">
            <div className="policies-section-header">
              <h2>FAQ</h2>
              <span className="badge badge-transparency">Transparencia</span>
            </div>
            <div className="policies-faq">
              <details>
                <summary>¿Viru garantiza el precio que veo?</summary>
                <p>No. Es un dato informativo; el precio final se confirma en el proveedor.</p>
              </details>
              <details>
                <summary>¿Por que veo precios desactualizados?</summary>
                <p>Si el proveedor no responde, mostramos el ultimo dato confirmado con la hora de su ultima comprobacion.</p>
              </details>
              <details>
                <summary>¿Que significa que veas resultados parciales?</summary>
                <p>Que el proveedor no ha respondido del todo. Mantenemos lo ya confirmado y te avisamos en la interfaz.</p>
              </details>
              <details>
                <summary>¿Puedo borrar mi cuenta?</summary>
                <p>Si. Puedes solicitarlo desde tu cuenta o soporte.</p>
              </details>
              <details>
                <summary>¿Viru comparte mis credenciales?</summary>
                <p>No. Tus credenciales y tokens no se comparten con terceros.</p>
              </details>
              <details>
                <summary>¿Las alertas son automáticas?</summary>
                <p>Se activan segun tus reglas. Tu decides umbrales y condiciones.</p>
              </details>
              <details>
                <summary>¿Que datos se guardan?</summary>
                <p>Cuenta, rutas observadas, alertas y preferencias. Nada de perfilado publicitario.</p>
              </details>
              <details>
                <summary>¿Puedo exportar mis datos?</summary>
                <p>Si. Ofrecemos portabilidad para tus datos generados.</p>
              </details>
              <details>
                <summary>¿Viru ofrece recomendaciones financieras?</summary>
                <p>No. Las recomendaciones son informativas y no asesoramiento financiero.</p>
              </details>
              <details>
                <summary>¿Hay políticas distintas por país?</summary>
                <p>Puede haber contenido contextual por región; cuando aplique, se documenta en esta política.</p>
              </details>
              <details>
                <summary>¿Puedo desactivar analítica?</summary>
                <p>Depende de la configuración activa de tu entorno. Si está disponible, lo verás en preferencias.</p>
              </details>
              <details>
                <summary>¿Cómo reporto un error en un dato?</summary>
                <p>Contacta soporte e indica ruta, fecha y captura si es posible.</p>
              </details>
            </div>
          </section>

          <section id="cta-final" className="policies-section policies-cta">
            <h2>Acciones finales</h2>
            <p>Si necesitas volver al panel o gestionar privacidad, aquí tienes accesos directos.</p>
            <div className="policies-cta-actions">
              <Link href="/dashboard" className="btn-primary">Volver al panel</Link>
              <a href="mailto:soporte@viru.app" className="btn-ghost">Contactar soporte</a>
              <a href="mailto:privacidad@viru.app" className="btn-ghost">Solicitar eliminación de datos</a>
            </div>
          </section>
        </div>

        <aside className="policies-quick" aria-label="Resumen rápido">
          <div className="policies-quick-card">
            <h3>Resumen rápido</h3>
            <p className="muted">
              Pensado para lectura rapida. Si necesitas detalle legal, consulta las secciónes completas.
            </p>
            <ul>
              <li>Herramienta informativa, sin garantía de precio.</li>
              <li>Indicacion visible de cuando se comprobo el ultimo dato si falta proveedor.</li>
              <li>Alertas orientativas y configurables.</li>
              <li>Derecho a borrado y portabilidad.</li>
              <li>Eventos técnicos para seguridad.</li>
            </ul>
          </div>
        </aside>
      </div>

      <div className="policies-floating">
        <a href="#policies-top" className="btn-ghost" aria-label="Subir al inicio">Subir</a>
        <a href="#indice-navegable" className="btn-ghost" aria-label="Ir al indice">Índice</a>
      </div>
    </main>
  );
}


