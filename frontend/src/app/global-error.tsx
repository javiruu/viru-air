"use client";

import { useEffect } from "react";

import { reportClientError } from "@/lib/errorLogging";
import { ErrorFallback } from "@/modules/shared/ErrorFallback";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    void reportClientError("global", error);
  }, [error]);

  return (
    <html>
      <body>
        <main className="shell" id="main-content">
          <ErrorFallback onRetry={reset} />
        </main>
      </body>
    </html>
  );
}
