import assert from "node:assert/strict";
import test from "node:test";

import { t } from "../src/i18n";
import { ABOUT_US_QUOTE_TEXT } from "../src/app/(private)/soporte/about-us/AnimatedQuoteBlock";
import { buildSupportAboutMembers } from "../src/app/(private)/soporte/about-us/content";
import { buildAccountMenuGroups } from "../src/modules/shared/accountMenuConfig";

test("account support menu exposes the about-us route", () => {
  const groups = buildAccountMenuGroups((key) => t("es", key));
  const supportGroup = groups.find((group) => group.title === "Soporte");

  assert.ok(supportGroup);
  assert.equal(supportGroup?.items.some((item) => item.href === "/soporte/about-us"), true);
  assert.equal(supportGroup?.items.at(-1)?.label, "About us");
});

test("about-us content builder returns the expected bilingual team shape", () => {
  const esMembers = buildSupportAboutMembers((key) => t("es", key));
  const enMembers = buildSupportAboutMembers((key) => t("en", key));

  assert.equal(esMembers.length, 4);
  assert.equal(enMembers.length, 4);
  assert.equal(esMembers[0]?.name, "Aria Soler");
  assert.equal(enMembers[3]?.role, "Product liaison");
  assert.deepEqual(
    esMembers.map((member) => member.focus.length),
    [2, 2, 2, 2],
  );
});

test("about-us animated quote keeps the requested vibe-coding copy", () => {
  assert.equal(ABOUT_US_QUOTE_TEXT, "Hecho 100% con vibe-coding y amor");
});
