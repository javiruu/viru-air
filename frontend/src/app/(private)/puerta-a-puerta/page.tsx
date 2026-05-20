import { Suspense } from "react";

import { DoorToDoorPanel } from "@/modules/door-to-door/DoorToDoorPanel";

export default function PuertaAPuertaPage() {
  return (
    <Suspense fallback={<main className="shell"><section className="panel panel-soft">Cargando Puerta a puerta…</section></main>}>
      <DoorToDoorPanel />
    </Suspense>
  );
}
