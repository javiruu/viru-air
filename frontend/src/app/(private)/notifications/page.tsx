"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AlertRulesWorkspace } from "@/modules/signals/AlertRulesWorkspace";
import { SignalsInbox } from "@/modules/signals/SignalsInbox";

export default function NotificationsPage() {
  return (
    <Suspense>
      <NotificationsView />
    </Suspense>
  );
}

function NotificationsView() {
  const searchParams = useSearchParams();

  if (searchParams.get("view") === "rules") {
    return <AlertRulesWorkspace requestedWatchId={searchParams.get("watch_id")} />;
  }

  return <SignalsInbox requestedFilter={searchParams.get("filter")} />;
}
