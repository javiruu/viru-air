import { Skeleton, SkeletonList, SkeletonPanel } from "@/modules/shared/Skeleton";

export default function PrivateLoading() {
  return (
    <main className="shell section-gap-lg" id="main-content" aria-busy="true">
      <SkeletonPanel ariaLabel="Cargando modulo privado">
        <Skeleton variant="pill" width={180} height={18} />
        <Skeleton variant="line" width="64%" />
        <Skeleton variant="line" width="46%" />
      </SkeletonPanel>

      <section className="split section-gap">
        <SkeletonList rows={4} ariaLabel="Cargando datos de lista" />
        <SkeletonPanel ariaLabel="Cargando resumen">
          <Skeleton variant="pill" width={150} height={18} />
          <Skeleton variant="line" width="82%" />
          <Skeleton variant="line" width="58%" />
          <Skeleton variant="card" className="loading-skeleton-card" />
        </SkeletonPanel>
      </section>
    </main>
  );
}
