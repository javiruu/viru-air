import "../styles/globals.css";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Metadata } from "next";
import Script from "next/script";

import { NotificationCenterProvider } from "@/components/components/notifications/notification-center";
import ScrollActivityScrollbar from "@/modules/shared/ScrollActivityScrollbar";

export const metadata: Metadata = {
  title: "Viru",
  description: "Ryanair Tracker",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const gaMeasurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

  return (
    <html lang="es" suppressHydrationWarning data-theme="light">
      <head>
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
        <NotificationCenterProvider>
          <a className="skip-link" href="#main-content">
            Saltar al contenido
          </a>
          <div className="app-root">
            <div className="app-content">{children}</div>
          </div>
        </NotificationCenterProvider>
      </body>
    </html>
  );
}
