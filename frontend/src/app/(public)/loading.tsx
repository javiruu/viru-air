import { Skeleton, SkeletonForm, SkeletonPanel } from "@/modules/shared/Skeleton";

export default function PublicLoading() {
  return (
    <main className="shell glass-signin-shell" id="main-content" aria-busy="true">
      <section className="panel panel-soft">
        <div className="glass-signin-topbar" aria-hidden="true">
          <Skeleton variant="pill" width={96} height={30} />
          <Skeleton variant="circle" width={30} height={30} />
        </div>
      </section>

      <SkeletonForm ariaLabel="Cargando vista publica">
        <Skeleton variant="pill" width={170} height={18} />
        <Skeleton variant="line" width="72%" />
        <div className="loading-skeleton-field">
          <Skeleton variant="line" width="34%" />
          <Skeleton variant="block" height={44} />
        </div>
        <div className="loading-skeleton-field">
          <Skeleton variant="line" width="30%" />
          <Skeleton variant="block" height={44} />
        </div>
        <Skeleton variant="pill" width={142} height={36} className="loading-skeleton-cta" />
      </SkeletonForm>

      <SkeletonPanel ariaLabel="Cargando contexto">
        <Skeleton variant="line" width="62%" />
        <Skeleton variant="line" width="48%" />
      </SkeletonPanel>
    </main>
  );
}
