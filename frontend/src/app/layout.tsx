import "../styles/globals.css";
import "../styles/signals.css";
import "../styles/community-routes.css";
import type { Metadata } from "next";
import Script from "next/script";
import { MotionConfig } from "framer-motion";

import { NotificationCenterProvider } from "@/components/components/notifications/notification-center";
import ScrollActivityScrollbar from "@/modules/shared/ScrollActivityScrollbar";
import { SHELL_SCROLL_STATE_CSS } from "@/modules/shared/shellScrollStateCss";

export const metadata: Metadata = {
  title: "Viru Air",
  description: "Viru Air",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const gaMeasurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

  return (
    <html lang="es" suppressHydrationWarning data-theme="light">
      <head>
        <style>{SHELL_SCROLL_STATE_CSS}</style>
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
          <NotificationCenterProvider>
            <a className="skip-link" href="#main-content">
              Saltar al contenido
            </a>
            <div className="app-root">
              <div className="app-content">{children}</div>
            </div>
          </NotificationCenterProvider>
        </MotionConfig>
      </body>
    </html>
  );
}
