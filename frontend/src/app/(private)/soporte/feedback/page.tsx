import SoporteFeedbackClient from "./SoporteFeedbackClient";

type SearchParamsShape = {
  [key: string]: string | string[] | undefined;
};

type PageProps = {
  searchParams?: Promise<SearchParamsShape>;
};

export default async function SoporteFeedbackPage({ searchParams }: PageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;

  const typeParam = typeof resolvedSearchParams?.type === "string" ? resolvedSearchParams.type : undefined;
  const messageParam = typeof resolvedSearchParams?.message === "string" ? resolvedSearchParams.message : "";
  const attachmentParam = typeof resolvedSearchParams?.attachment === "string" ? resolvedSearchParams.attachment : "";

  const initialFeedbackType =
    typeParam === "bug" || typeParam === "idea" || typeParam === "general"
      ? typeParam
      : "bug";

  return (
    <SoporteFeedbackClient
      initialFeedbackType={initialFeedbackType}
      initialMessage={messageParam}
      initialAttachmentUrl={attachmentParam}
    />
  );
}
