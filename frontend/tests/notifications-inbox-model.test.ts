import assert from "node:assert/strict";
import test from "node:test";

import {
  filterNotificationItems,
  groupNotificationItems,
  normalizeNotificationFilter,
  type NotificationInboxItem,
} from "../src/modules/signals/notificationInboxModel";

const BASE_ITEM: NotificationInboxItem = {
  id: "alert_event:1",
  source_type: "alert_event",
  source_id: "1",
  category: "price",
  tone: "info",
  title: "Signal",
  body: "Body",
  route_label: "MAD → BCN",
  action_href: "/watchlist/1",
  created_at: "2026-07-30T09:00:00Z",
  read_at: null,
  is_read: false,
};

test("actionable filter keeps only unread rows with a real action", () => {
  const items = [
    BASE_ITEM,
    { ...BASE_ITEM, id: "alert_event:2", action_href: null },
    { ...BASE_ITEM, id: "alert_event:3", action_href: "   " },
    { ...BASE_ITEM, id: "alert_event:4", is_read: true, read_at: "2026-07-30T10:00:00Z" },
  ];

  assert.deepEqual(
    filterNotificationItems(items, "actionable").map((item) => item.id),
    ["alert_event:1"],
  );
});

test("keeps existing all, unread and category filters compatible", () => {
  const items = [
    BASE_ITEM,
    { ...BASE_ITEM, id: "security_activity:2", category: "security" as const, is_read: true },
  ];

  assert.equal(filterNotificationItems(items, "all").length, 2);
  assert.deepEqual(filterNotificationItems(items, "unread"), [BASE_ITEM]);
  assert.equal(filterNotificationItems(items, "security")[0]?.id, "security_activity:2");
  assert.equal(normalizeNotificationFilter("actionable"), "actionable");
  assert.equal(normalizeNotificationFilter("future-filter"), "all");
});

test("groups recent signals for presentation without collapsing source rows", () => {
  const items = [
    BASE_ITEM,
    { ...BASE_ITEM, id: "alert_event:2", created_at: "2026-07-29T18:00:00Z" },
    { ...BASE_ITEM, id: "alert_event:3", created_at: "2026-07-18T18:00:00Z" },
  ];

  const groups = groupNotificationItems(items, new Date("2026-07-30T12:00:00Z"));

  assert.deepEqual(
    groups.map((group) => [group.key, group.items.map((item) => item.id)]),
    [
      ["today", ["alert_event:1"]],
      ["recent", ["alert_event:2"]],
      ["earlier", ["alert_event:3"]],
    ],
  );
});

test("counts calendar days consistently across daylight-saving transitions", () => {
  const groups = groupNotificationItems(
    [{ ...BASE_ITEM, created_at: "2026-03-21T12:00:00-04:00" }],
    new Date("2026-03-29T12:00:00-04:00"),
  );

  assert.equal(groups[0]?.key, "earlier");
});
