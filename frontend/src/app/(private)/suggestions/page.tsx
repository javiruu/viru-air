import { redirect } from "next/navigation";

export default function SuggestionsLegacyPage() {
  redirect("/soporte/feedback?type=idea");
}
