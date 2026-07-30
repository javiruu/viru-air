import { redirect } from "next/navigation";

type AlertsAliasPageProps = {
  readonly searchParams: Promise<Record<string, string | readonly string[] | undefined>>;
};

export default async function AlertsAliasPage({ searchParams }: AlertsAliasPageProps) {
  const incomingSearchParams = await searchParams;
  const nextSearchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(incomingSearchParams)) {
    if (typeof value === "string") {
      nextSearchParams.append(key, value);
      continue;
    }
    value?.forEach((item) => nextSearchParams.append(key, item));
  }

  nextSearchParams.set("view", "rules");
  redirect(`/notifications?${nextSearchParams.toString()}`);
}
