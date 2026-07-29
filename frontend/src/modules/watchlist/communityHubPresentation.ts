import type { CommunityPricing } from "@/modules/watchlist/types";

export type CommunityHubIndicator =
  | "available"
  | "public"
  | "pending"
  | "contributed";

export type CommunityHubParticipation =
  | "purchase"
  | "contribute"
  | "review";

export function getCommunityHubIndicator(
  communityPricing: CommunityPricing,
): CommunityHubIndicator {
  if (communityPricing.response) return "contributed";
  if (communityPricing.eligible) return "pending";
  if (communityPricing.aggregate.is_public) return "public";
  return "available";
}

export function getCommunityHubParticipation(
  communityPricing: CommunityPricing,
): CommunityHubParticipation {
  if (communityPricing.response) return "review";
  if (communityPricing.eligible) return "contribute";
  return "purchase";
}
