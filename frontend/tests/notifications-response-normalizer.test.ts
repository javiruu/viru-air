import assert from "node:assert/strict";
import test from "node:test";

import { normalizeNotificationInboxResponse } from "../src/modules/signals/notificationInboxModel";

test("normalizes missing and null inbox collections without sharing fallback objects", () => {
  const first = normalizeNotificationInboxResponse({ items: null, summary: null });
  const second = normalizeNotificationInboxResponse({});

  assert.deepEqual(first.items, []);
  assert.deepEqual(first.summary, {
    total: 0,
    unread: 0,
    price: 0,
    security: 0,
    digest: 0,
    worker: 0,
    community: 0,
  });
  assert.notEqual(first.items, second.items);
  assert.notEqual(first.summary, second.summary);
});

test("accepts a legacy array response and normalizes optional item fields", () => {
  const response = normalizeNotificationInboxResponse([
    {
      id: "alert_event:41",
      source_type: "alert_event",
      source_id: 41,
      category: "price",
      tone: "warning",
      title: "Bajó tu vuelo",
      body: "La tarifa está por debajo de tu objetivo.",
      route_label: null,
      action_href: "  /watchlist/12  ",
      created_at: "2026-07-30T08:00:00Z",
      read_at: null,
    },
  ]);

  assert.equal(response.items.length, 1);
  assert.deepEqual(response.items[0], {
    id: "alert_event:41",
    source_type: "alert_event",
    source_id: "41",
    category: "price",
    tone: "warning",
    title: "Bajó tu vuelo",
    body: "La tarifa está por debajo de tu objetivo.",
    route_label: null,
    action_href: "/watchlist/12",
    created_at: "2026-07-30T08:00:00Z",
    read_at: null,
    is_read: false,
  });
  assert.equal(response.summary.total, 1);
  assert.equal(response.summary.unread, 1);
  assert.equal(response.summary.price, 1);
});

test("drops unsafe rows that cannot preserve exact read-state identifiers", () => {
  const response = normalizeNotificationInboxResponse({
    items: [
      {
        id: "unknown:1",
        source_type: "future_source",
        source_id: "1",
        category: "price",
        tone: "info",
        title: "Future event",
        body: "Unsupported source",
        created_at: "2026-07-30T08:00:00Z",
      },
      {
        id: "alert_event:unsafe-number",
        source_type: "alert_event",
        source_id: Number.MAX_SAFE_INTEGER + 1,
        category: "price",
        tone: "info",
        title: "Unsafe identity",
        body: "Cannot preserve this numeric identifier exactly.",
        created_at: "2026-07-30T08:00:00Z",
        action_href: "/watchlist/1",
      },
      null,
    ],
  });

  assert.deepEqual(response.items, []);
  assert.equal(response.summary.total, 0);
});

test("drops unsafe or external notification action links", () => {
  const baseItem = {
    id: "alert_event:41",
    source_type: "alert_event",
    source_id: "41",
    category: "price",
    tone: "warning",
    title: "Price signal",
    body: "The price changed.",
    created_at: "2026-07-30T08:00:00Z",
  };
  const response = normalizeNotificationInboxResponse([
    { ...baseItem, id: "safe", action_href: "/watchlist/12" },
    { ...baseItem, id: "external", action_href: "https://example.com" },
    { ...baseItem, id: "protocol-relative", action_href: "//example.com" },
    { ...baseItem, id: "script", action_href: "javascript:alert(1)" },
  ]);

  assert.equal(response.items[0]?.action_href, "/watchlist/12");
  assert.equal(response.items[1]?.action_href, null);
  assert.equal(response.items[2]?.action_href, null);
  assert.equal(response.items[3]?.action_href, null);
});

test("drops slash-backslash notification action links that could escape the origin", () => {
  const response = normalizeNotificationInboxResponse([
    {
      id: "alert_event:slash-backslash",
      source_type: "alert_event",
      source_id: "41",
      category: "price",
      tone: "warning",
      title: "Price signal",
      body: "Potential origin escape.",
      created_at: "2026-07-30T08:00:00Z",
      action_href: "/\\evil.example",
    },
  ]);

  assert.equal(response.items[0]?.action_href, null);
});

test("derives a safe category from a known legacy source", () => {
  const response = normalizeNotificationInboxResponse([
    {
      id: "security_activity:1",
      source_type: "security_activity",
      source_id: "1",
      category: "future-category",
      tone: "info",
      title: "Security activity",
      body: "A security event was recorded.",
      created_at: "2026-07-30T08:00:00Z",
    },
  ]);

  assert.equal(response.items[0]?.category, "security");
  assert.equal(response.summary.security, 1);
  assert.equal(response.summary.worker, 0);
});

test("preserves supported community trending signals instead of dropping them", () => {
  const response = normalizeNotificationInboxResponse({
    items: [
      {
        id: "community_trending:2026-08-11:MAD:BCN",
        source_type: "community_trending",
        source_id: "2026-08-11:MAD:BCN",
        category: "community",
        tone: "info",
        title: "La comunidad está mirando esta ruta",
        body: "MAD → BCN es una ruta en tendencia esta semana.",
        route_label: "MAD → BCN",
        action_href: "/dashboard",
        created_at: "2026-08-11T08:00:00Z",
        read_at: null,
      },
    ],
    summary: { total: 1, unread: 1, community: 1 },
  });

  assert.equal(response.items[0]?.source_type, "community_trending");
  assert.equal(response.items[0]?.category, "community");
  assert.equal(response.summary.community, 1);
});
