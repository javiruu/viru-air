"use client";

import Link from "next/link";
import Image from "next/image";

import { useI18n } from "@/i18n";

type ArticleContent = {
  eyebrow: string;
  title: string;
  dek: string;
  category: string;
  publishedAt: string;
  readTime: string;
  author: string;
  authorRole: string;
  intro: string[];
  pullQuote: string;
  sectionOneTitle: string;
  sectionOneBody: string[];
  sectionTwoTitle: string;
  sectionTwoBody: string[];
  bulletsTitle: string;
  bullets: string[];
  closingTitle: string;
  closingBody: string[];
  ctaLabel: string;
};

const contentEs: ArticleContent = {
  eyebrow: "Product note",
  title: "Ventanas de precio, señales y contexto: así leeremos las próximas oportunidades en Viru.",
  dek:
    "Estamos preparando una lectura más editorial de las oportunidades para que cada alerta importante se entienda rápido, pero con suficiente contexto para decidir de verdad.",
  category: "Actualización de producto",
  publishedAt: "20 abr 2026",
  readTime: "4 min de lectura",
  author: "Equipo Viru",
  authorRole: "Producto y experiencia",
  intro: [
    "Hasta ahora, muchas señales del panel aparecían como piezas sueltas: una búsqueda, un precio, un estado, una pista operativa. Funcionaban, pero no siempre contaban una historia completa.",
    "El cambio que estamos introduciendo busca precisamente eso: cuando aparezca una oportunidad relevante, Viru no debería limitarse a insinuarla. Debería ayudar a leerla.",
  ],
  pullQuote:
    "Una buena oportunidad no solo baja de precio. También llega con el contexto justo para entender por qué importa ahora.",
  sectionOneTitle: "Qué cambia en la lectura",
  sectionOneBody: [
    "Queremos que cada actualización importante combine tres capas: la señal principal, una explicación corta y una guía de interpretación. No se trata de añadir ruido, sino de evitar que el usuario tenga que reconstruir solo el significado del cambio.",
    "Por eso este nuevo formato mezcla densidad operativa con presentación editorial. El objetivo es que puedas escanear rápido, pero también profundizar cuando haga falta.",
  ],
  sectionTwoTitle: "Cómo se verá dentro del producto",
  sectionTwoBody: [
    "En el dashboard, la novedad vive como una pieza lateral: una tarjeta con imagen, titular, extracto y metadata. Esa versión sirve para detectar que hay algo nuevo que merece atención sin romper el ritmo del panel.",
    "Cuando entras a leerla, el contenido ya no se comporta como una tarjeta. Se convierte en un artículo: bloques de texto, intertítulos, cita destacada y estructura de lectura más clara. Esa transición es deliberada.",
  ],
  bulletsTitle: "Qué esperamos conseguir con este formato",
  bullets: [
    "Reducir el tiempo que tarda un usuario en entender si una oportunidad merece atención inmediata.",
    "Dar contexto suficiente sin convertir la actualización en una pared de texto difícil de escanear.",
    "Hacer que novedades de producto y señales operativas compartan una misma voz editorial dentro de Viru.",
  ],
  closingTitle: "Siguiente paso",
  closingBody: [
    "Esta primera iteración todavía usa contenido local y controlado por developers, pero deja la base visual y estructural para que futuras actualizaciones se publiquen con el mismo lenguaje.",
    "La intención no es abrir una sección de blog genérica. Es crear una capa de lectura cuidada dentro del producto, allí donde una actualización realmente cambia cómo decides.",
  ],
  ctaLabel: "Volver al dashboard",
};

const contentEn: ArticleContent = {
  eyebrow: "Product note",
  title: "Price windows, signals, and context: how Viru will frame the next opportunities.",
  dek:
    "We are building a more editorial reading layer for key opportunities so each important update becomes clear quickly, while still carrying enough context to support a real decision.",
  category: "Product update",
  publishedAt: "Apr 20, 2026",
  readTime: "4 min read",
  author: "Viru team",
  authorRole: "Product and experience",
  intro: [
    "Until now, many dashboard signals appeared as separate pieces: a search, a price, a state, an operational hint. They worked, but they did not always tell a complete story.",
    "This change is meant to fix exactly that. When an opportunity matters, Viru should not just hint at it. It should help users read it.",
  ],
  pullQuote:
    "A good opportunity is not only cheaper. It also arrives with enough context to explain why it matters now.",
  sectionOneTitle: "What changes in the reading layer",
  sectionOneBody: [
    "We want every meaningful update to combine three layers: the main signal, a short explanation, and a reading guide. The goal is not to add more noise, but to avoid forcing users to reconstruct the meaning of a change on their own.",
    "That is why this format blends operational density with editorial presentation. You should be able to scan fast, but also go deeper when needed.",
  ],
  sectionTwoTitle: "How this will live in the product",
  sectionTwoBody: [
    "In the dashboard, the update lives as a lateral teaser: image, headline, excerpt, and metadata. That version is there to signal that something worth reading has happened without breaking the panel rhythm.",
    "Once you open it, the content stops behaving like a card. It becomes an article: text blocks, section headings, a pull quote, and a clearer reading structure. That transition is intentional.",
  ],
  bulletsTitle: "What this format is meant to improve",
  bullets: [
    "Reduce the time it takes to understand whether an opportunity deserves immediate attention.",
    "Add enough context without turning the update into a dense wall of text.",
    "Give product notes and operational signals a shared editorial voice inside Viru.",
  ],
  closingTitle: "What comes next",
  closingBody: [
    "This first iteration still uses controlled local content, but it already establishes the visual and structural base for future updates to be published with the same language.",
    "The goal is not to create a generic blog section. It is to create a careful reading layer inside the product, where an update truly changes how a decision is made.",
  ],
  ctaLabel: "Back to dashboard",
};

export default function SupportNewsPriceWindowsPage() {
  const { localeTag } = useI18n();
  const content = localeTag.toLowerCase().startsWith("es") ? contentEs : contentEn;

  return (
    <main className="shell support-article-page" id="main-content">
      <div className="page-header">
        <div className="page-title">
          <h1>{content.category}</h1>
          <p>{content.dek}</p>
        </div>
        <div className="row-actions">
          <Link className="btn-ghost" href="/dashboard">
            {content.ctaLabel}
          </Link>
        </div>
      </div>

      <article className="support-article">
        <header className="support-article-hero panel">
          <div className="support-article-hero-copy">
            <span className="support-article-eyebrow">{content.eyebrow}</span>
            <h2>{content.title}</h2>
            <p>{content.dek}</p>
          </div>

          <div className="support-article-hero-media">
            <Image
              src="/images/dashboard-news-flight-window.svg"
              alt=""
              fill
              sizes="(max-width: 980px) 100vw, 38vw"
              className="support-article-hero-image"
            />
          </div>
        </header>

        <div className="support-article-layout">
          <aside className="support-article-meta">
            <div className="support-article-meta-card">
              <span className="support-article-meta-label">{content.category}</span>
              <strong>{content.author}</strong>
              <p>{content.authorRole}</p>
              <p>
                {content.publishedAt}
                <span aria-hidden="true"> · </span>
                {content.readTime}
              </p>
            </div>
          </aside>

          <div className="support-article-body">
            <section className="support-article-prose">
              {content.intro.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}

              <blockquote>{content.pullQuote}</blockquote>

              <h3>{content.sectionOneTitle}</h3>
              {content.sectionOneBody.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}

              <h3>{content.sectionTwoTitle}</h3>
              {content.sectionTwoBody.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}

              <div className="support-article-highlight">
                <span>{content.bulletsTitle}</span>
                <ul>
                  {content.bullets.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <h3>{content.closingTitle}</h3>
              {content.closingBody.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </section>

            <footer className="support-article-footer">
              <Link className="btn-primary" href="/dashboard">
                {content.ctaLabel}
              </Link>
              <Link className="btn-ghost" href="/soporte/about-us">
                About Viru
              </Link>
            </footer>
          </div>
        </div>
      </article>
    </main>
  );
}
