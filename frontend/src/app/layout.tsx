import "../styles/globals.css";
import { MotionConfig } from "framer-motion";
import type { Metadata } from "next";
import Script from "next/script";
import QueryProvider from "@/app/providers/QueryProvider";
import { NotificationCenterProvider } from "@/components/components/notifications/notification-center";
import ScrollActivityScrollbar from "@/modules/shared/ScrollActivityScrollbar";
import { SHELL_SCROLL_STATE_CSS } from "@/modules/shared/shellScrollStateCss";
import { EXTENSION_ATTRIBUTE_CLEANUP_SCRIPT } from "@/modules/shared/hydrationGuard";

export const metadata: Metadata = {
  title: "Viru Air",
  description: "Viru Air",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const gaMeasurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

  return (
    <html lang="es" suppressHydrationWarning data-theme="light" data-scroll-behavior="smooth">
      <head>
        <style>{SHELL_SCROLL_STATE_CSS}</style>
        {/*
          Runs synchronously before hydration to strip attributes injected by
          browser extensions (Bitdefender's bis_* markers), which otherwise
          cause false-positive hydration mismatches across the whole tree.
        */}
        <script dangerouslySetInnerHTML={{ __html: EXTENSION_ATTRIBUTE_CLEANUP_SCRIPT }} />
        {gaMeasurementId ? (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${gaMeasurementId}`}
              strategy="afterInteractive"
            />
            <Script id="ga-init" strategy="afterInteractive">
              {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
window.gtag = gtag;
gtag('js', new Date());
gtag('config', '${gaMeasurementId}');`}
            </Script>
          </>
        ) : null}
      </head>
      <body>
        <ScrollActivityScrollbar />
        <MotionConfig reducedMotion="user">
          <QueryProvider>
            <NotificationCenterProvider>
              <a className="skip-link" href="#main-content">
                Saltar al contenido
              </a>
              <div className="app-root">
                <div className="app-content">{children}</div>
              </div>
            </NotificationCenterProvider>
          </QueryProvider>
        </MotionConfig>
      </body>
    </html>
  );
}
