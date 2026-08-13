export const NOTIFICATION_CATEGORIES = ["price", "security", "digest", "worker", "community"] as const;

export type NotificationCategory = (typeof NOTIFICATION_CATEGORIES)[number];
export type NotificationFilter = "all" | "actionable" | "unread" | NotificationCategory;
export type NotificationTone = "success" | "warning" | "error" | "info";
export type NotificationSourceType = "alert_event" | "hotel_alert_event" | "security_activity" | "community_trending";
export type NotificationTimelineGroupKey = "today" | "recent" | "earlier";

export type NotificationInboxItem = {
  id: string;
  source_type: NotificationSourceType;
  source_id: string;
  category: NotificationCategory;
  tone: NotificationTone;
  title: string;
  body: string;
  route_label: string | null;
  action_href: string | null;
  created_at: string;
  read_at: string | null;
  is_read: boolean;
};

export type NotificationInboxSummary = Record<"total" | "unread" | NotificationCategory, number>;

export type NotificationInboxResponse = {
  items: NotificationInboxItem[];
  summary: NotificationInboxSummary;
};

export type NotificationTimelineGroup = {
  key: NotificationTimelineGroupKey;
  items: NotificationInboxItem[];
};

const SOURCE_TYPES = new Set<NotificationSourceType>([
  "alert_event",
  "hotel_alert_event",
  "security_activity",
  "community_trending",
]);
const CATEGORIES = new Set<NotificationCategory>(NOTIFICATION_CATEGORIES);
const TONES = new Set<NotificationTone>(["success", "warning", "error", "info"]);
const FILTERS = new Set<NotificationFilter>(["all", "actionable", "unread", ...NOTIFICATION_CATEGORIES]);

function getProperty(value: object, key: string): unknown {
  return Object.getOwnPropertyDescriptor(value, key)?.value;
}

function getRecord(value: unknown): object | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value : null;
}

function getTrimmedString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function getIdentityString(value: unknown): string | null {
  if (typeof value === "number" && Number.isSafeInteger(value)) return String(value);
  return getTrimmedString(value);
}

function getOptionalString(value: unknown): string | null {
  return getTrimmedString(value);
}

function normalizeActionHref(value: unknown): string | null {
  const href = getTrimmedString(value);
  return href?.startsWith("/") && !href.startsWith("//") && !href.includes("\\") ? href : null;
}

function getNonNegativeInteger(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

function normalizeItem(value: unknown): NotificationInboxItem | null {
  const record = getRecord(value);
  if (!record) return null;

  const id = getIdentityString(getProperty(record, "id"));
  const sourceTypeValue = getProperty(record, "source_type");
  const sourceId = getIdentityString(getProperty(record, "source_id"));
  const title = getTrimmedString(getProperty(record, "title"));
  const body = getTrimmedString(getProperty(record, "body"));
  const createdAt = getTrimmedString(getProperty(record, "created_at"));

  if (
    !id ||
    typeof sourceTypeValue !== "string" ||
    !SOURCE_TYPES.has(sourceTypeValue as NotificationSourceType) ||
    !sourceId ||
    !title ||
    !body ||
    !createdAt
  ) {
    return null;
  }
  const sourceType = sourceTypeValue as NotificationSourceType;

  const categoryValue = getProperty(record, "category");
  const toneValue = getProperty(record, "tone");
  const readAt = getOptionalString(getProperty(record, "read_at"));
  const explicitRead = getProperty(record, "is_read");

  return {
    id,
    source_type: sourceType,
    source_id: sourceId,
    category:
      typeof categoryValue === "string" && CATEGORIES.has(categoryValue as NotificationCategory)
        ? (categoryValue as NotificationCategory)
        : sourceType === "security_activity" ? "security" : sourceType === "community_trending" ? "community" : "price",
    tone:
      typeof toneValue === "string" && TONES.has(toneValue as NotificationTone)
        ? (toneValue as NotificationTone)
        : "info",
    title,
    body,
    route_label: getOptionalString(getProperty(record, "route_label")),
    action_href: normalizeActionHref(getProperty(record, "action_href")),
    created_at: createdAt,
    read_at: readAt,
    is_read: typeof explicitRead === "boolean" ? explicitRead : readAt !== null,
  };
}

function deriveSummary(items: readonly NotificationInboxItem[]): NotificationInboxSummary {
  const summary: NotificationInboxSummary = {
    total: items.length,
    unread: 0,
    price: 0,
    security: 0,
    digest: 0,
    worker: 0,
    community: 0,
  };

  for (const item of items) {
    if (!item.is_read) summary.unread += 1;
    summary[item.category] += 1;
  }

  return summary;
}

function normalizeSummary(value: unknown, derived: NotificationInboxSummary): NotificationInboxSummary {
  const record = getRecord(value);
  if (!record) return { ...derived };

  return {
    total: getNonNegativeInteger(getProperty(record, "total")) ?? derived.total,
    unread: getNonNegativeInteger(getProperty(record, "unread")) ?? derived.unread,
    price: getNonNegativeInteger(getProperty(record, "price")) ?? derived.price,
    security: getNonNegativeInteger(getProperty(record, "security")) ?? derived.security,
    digest: getNonNegativeInteger(getProperty(record, "digest")) ?? derived.digest,
    worker: getNonNegativeInteger(getProperty(record, "worker")) ?? derived.worker,
    community: getNonNegativeInteger(getProperty(record, "community")) ?? derived.community,
  };
}

export function normalizeNotificationInboxResponse(value: unknown): NotificationInboxResponse {
  const record = getRecord(value);
  const rawItems = Array.isArray(value)
    ? value
    : record && Array.isArray(getProperty(record, "items"))
      ? getProperty(record, "items")
      : record && Array.isArray(getProperty(record, "notifications"))
        ? getProperty(record, "notifications")
        : [];
  const items = Array.isArray(rawItems)
    ? rawItems.flatMap((item) => {
        const normalized = normalizeItem(item);
        return normalized ? [normalized] : [];
      })
    : [];
  const derivedSummary = deriveSummary(items);

  return {
    items,
    summary: normalizeSummary(record ? getProperty(record, "summary") : null, derivedSummary),
  };
}

export function normalizeNotificationFilter(value: string | null): NotificationFilter {
  return value && FILTERS.has(value as NotificationFilter) ? (value as NotificationFilter) : "all";
}

export function filterNotificationItems(
  items: readonly NotificationInboxItem[],
  filter: NotificationFilter,
): NotificationInboxItem[] {
  if (filter === "all") return [...items];
  if (filter === "actionable") {
    return items.filter((item) => !item.is_read && Boolean(item.action_href?.trim()));
  }
  if (filter === "unread") return items.filter((item) => !item.is_read);
  return items.filter((item) => item.category === filter);
}

function localDayOrdinal(value: Date): number {
  return Date.UTC(value.getFullYear(), value.getMonth(), value.getDate());
}

export function groupNotificationItems(
  items: readonly NotificationInboxItem[],
  now = new Date(),
): NotificationTimelineGroup[] {
  const today = localDayOrdinal(now);
  const oneDay = 24 * 60 * 60 * 1000;
  const groups = new Map<NotificationTimelineGroupKey, NotificationInboxItem[]>([
    ["today", []],
    ["recent", []],
    ["earlier", []],
  ]);

  for (const item of items) {
    const createdAt = new Date(item.created_at);
    const itemDay = Number.isNaN(createdAt.getTime()) ? Number.NEGATIVE_INFINITY : localDayOrdinal(createdAt);
    const ageInDays = Math.floor((today - itemDay) / oneDay);
    const key: NotificationTimelineGroupKey = ageInDays <= 0 ? "today" : ageInDays <= 7 ? "recent" : "earlier";
    groups.get(key)?.push(item);
  }

  return [...groups.entries()]
    .filter((entry) => entry[1].length > 0)
    .map(([key, groupedItems]) => ({ key, items: groupedItems }));
}
