import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const ROOT = path.resolve(__dirname, "..");
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), "utf8");

// ============================================================
// PRIVATE SHELL HEADER
// ============================================================
test("PrivateTopBar is a presentational wrapper with no JS observer", () => {
  const source = read("src/modules/shared/PrivateTopBar.tsx");
  assert.ok(!/useState/.test(source), "PrivateTopBar still uses useState");
  assert.ok(!/useRef/.test(source), "PrivateTopBar still uses useRef");
  assert.ok(!/useEffect/.test(source), "PrivateTopBar still uses useEffect");
  assert.ok(
    !/IntersectionObserver/.test(source),
    "PrivateTopBar still uses IntersectionObserver",
  );
  assert.match(source, /className="shell-header private-account-anchor"/);
});

test("(private)/layout.tsx mounts PrivateTopBar", () => {
  const source = read("src/app/(private)/layout.tsx");
  assert.match(source, /import PrivateTopBar from "@\/modules\/shared\/PrivateTopBar"/);
  assert.match(source, /<PrivateTopBar>/);
});

// ============================================================
// PUBLIC SHELL HEADER
// ============================================================
test("PublicShellHeader is a client component using .shell-header base", () => {
  const source = read("src/modules/shared/PublicShellHeader.tsx");
  assert.match(source, /^"use client";/m);
  assert.match(source, /className="shell-header public-shell-header"/);
  assert.match(source, /usePathname/);
});

test("PublicShellHeader filters auth links from NAV_V1_PUBLIC", () => {
  const source = read("src/modules/shared/PublicShellHeader.tsx");
  assert.match(source, /NAV_V1_PUBLIC/);
  assert.match(source, /item\.href !== "\/login"/);
  assert.match(source, /item\.href !== "\/register"/);
});

test("PublicShellHeader renders brand, nav and action controls", () => {
  const source = read("src/modules/shared/PublicShellHeader.tsx");
  assert.match(source, /public-shell-brand/);
  assert.match(source, /public-shell-brand-dot/);
  assert.match(source, /public-shell-nav/);
  assert.match(source, /public-shell-nav-link/);
  assert.match(source, /public-shell-actions/);
  assert.match(source, /<LanguageToggle/);
  assert.match(source, /<ThemeToggle/);
});

test("(public)/layout.tsx mounts PublicShellHeader", () => {
  const source = read("src/app/(public)/layout.tsx");
  assert.match(
    source,
    /import PublicShellHeader from "@\/modules\/shared\/PublicShellHeader"/,
  );
  assert.match(source, /<PublicShellHeader\s*\/>/);
});

// ============================================================
// MORPH VIA CONTAINER SCROLL-STATE
// ============================================================
test("components.css declares .shell-header as the sticky morph base", () => {
  const css = read("src/styles/components.css");
  assert.match(css, /\.shell-header\s*\{[^}]*position:\s*sticky/);
  assert.match(css, /\.shell-header\s*\{[^}]*top:\s*var\(--shell-header-top\)/);
});

test("the inlined shell stylesheet keeps scroll-state progressive enhancement", () => {
  const css = read("src/modules/shared/shellScrollStateCss.ts");
  assert.match(css, /@supports\s+\(container-type:\s*scroll-state\)/);
  assert.match(css, /container-type:\s*scroll-state/);
});

test("the inlined shell stylesheet keeps the complete stuck morph", () => {
  const css = read("src/modules/shared/shellScrollStateCss.ts");
  assert.match(css, /@container\s+scroll-state\(stuck:\s*top\)/);
  const morph = css.match(/@container\s+scroll-state\(stuck:\s*top\)\s*\{[\s\S]*?\n\}/);
  if (morph === null) assert.fail("morph block not found");
  const morphCss = morph[0];
  assert.match(
    morphCss,
    /padding:\s*var\(--shell-header-stuck-padding/,
  );
  assert.match(
    morphCss,
    /border-radius:\s*var\(--shell-header-stuck-radius/,
  );
  assert.match(morphCss, /box-shadow:\s*var\(--shell-header-stuck-shadow/);
  assert.match(morphCss, /backdrop-filter/);
});

test("root layout inlines scroll-state CSS without sending it through the CSS parser", () => {
  const componentsCss = read("src/styles/components.css");
  const rootLayout = read("src/app/layout.tsx");
  assert.doesNotMatch(componentsCss, /@container\s+scroll-state/);
  assert.match(
    rootLayout,
    /import \{ SHELL_SCROLL_STATE_CSS \} from "@\/modules\/shared\/shellScrollStateCss"/,
  );
  assert.match(rootLayout, /<style>\{SHELL_SCROLL_STATE_CSS\}<\/style>/);
});

test("components.css respects prefers-reduced-motion for the morph", () => {
  const css = read("src/styles/components.css");
  assert.match(css, /@media\s+\(prefers-reduced-motion:\s*reduce\)/);
  assert.match(css, /\.shell-header\s*\{[^}]*transition:\s*none/);
});

test("tokens.css exposes the full shell-header morph token set", () => {
  const tokens = read("src/styles/tokens.css");
  const required = [
    "--shell-header-top",
    "--shell-header-z",
    "--shell-header-resting-padding-block",
    "--shell-header-resting-padding-inline",
    "--shell-header-resting-radius",
    "--shell-header-resting-bg",
    "--shell-header-resting-shadow",
    "--shell-header-stuck-padding-block",
    "--shell-header-stuck-padding-inline",
    "--shell-header-stuck-radius",
    "--shell-header-stuck-bg",
    "--shell-header-stuck-shadow",
    "--shell-header-stuck-backdrop-blur",
    "--shell-header-transition-duration",
    "--shell-header-transition-ease",
  ];
  for (const t of required) {
    assert.match(tokens, new RegExp(`${t}:`), `token ${t} missing`);
  }
});

// ============================================================
// CSS ORPHAN CLEANUP
// ============================================================
test("screens.css no longer carries the removed landing-* rules", () => {
  const css = read("src/styles/screens.css");
  for (const cls of [
    "landing-header",
    "landing-brand",
    "landing-kicker",
    "landing-tagline",
    "landing-actions",
    "landing-prueba-cinema-header",
  ]) {
    assert.ok(!css.includes(cls), `screens.css still references ${cls}`);
  }
});

test("screens.css still defines .landing-dot (used by ViruFooterBlock)", () => {
  const css = read("src/styles/screens.css");
  assert.match(css, /\.landing-dot\s*\{/);
});

test("screens.css no longer has the .is-leaving state", () => {
  const css = read("src/styles/screens.css");
  assert.ok(!/is-leaving/.test(css), "screens.css still references is-leaving");
});

// ============================================================
// HEADER CONSOLIDATION
// ============================================================
test("home page lives at (public)/page.tsx so the shell header applies", () => {
  assert.ok(
    fs.existsSync(path.join(ROOT, "src/app/(public)/page.tsx")),
    "expected src/app/(public)/page.tsx to exist",
  );
  assert.ok(
    !fs.existsSync(path.join(ROOT, "src/app/page.tsx")),
    "expected src/app/page.tsx to be removed",
  );
});

test("home page no longer renders the old landing-header or its duplicates", () => {
  const source = read("src/app/(public)/page.tsx");
  for (const forbidden of [
    "landing-header",
    "landing-brand",
    "landing-actions",
    "landing-tagline",
    "ThemeToggle",
    "ViruFooterBlock",
  ]) {
    assert.ok(!source.includes(forbidden), `home page still references ${forbidden}`);
  }
});

test("auth forms no longer import or render ThemeToggle inside glass-signin-topbar", () => {
  for (const file of [
    "src/app/(public)/login/page.tsx",
    "src/app/(public)/register/page.tsx",
    "src/app/(public)/forgot-password/page.tsx",
  ]) {
    const source = read(file);
    assert.ok(
      !/import ThemeToggle/.test(source),
      `${file} still imports ThemeToggle`,
    );
    const topbar = source.match(
      /<div className="glass-signin-topbar">[\s\S]*?<\/div>/,
    );
    assert.ok(topbar, `${file} missing glass-signin-topbar`);
    assert.ok(
      !/<ThemeToggle/.test(topbar![0]),
      `${file} glass-signin-topbar still renders <ThemeToggle />`,
    );
  }
});

test("/prueba no longer renders the cinema-header or imports ThemeToggle", () => {
  const source = read("src/app/(public)/prueba/page.tsx");
  assert.ok(
    !/import ThemeToggle/.test(source),
    "/prueba still imports ThemeToggle",
  );
  for (const forbidden of [
    "landing-prueba-cinema-header",
    "landing-brand",
    "landing-tagline",
  ]) {
    assert.ok(!source.includes(forbidden), `/prueba still references ${forbidden}`);
  }
});

// ============================================================
// I18N CLEANUP
// ============================================================
test("public.ts dropped brandTagline but kept policies", () => {
  const i18n = read("src/i18n/domains/public.ts");
  assert.ok(!/brandTagline/.test(i18n), "public.ts still has brandTagline");
  assert.ok(/policies:/.test(i18n), "public.ts lost policies key");
});
