import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const root = new URL("../src/", import.meta.url);

function read(path: string): string {
  return readFileSync(new URL(path, root), "utf8");
}

test("the application shell exposes the accessible keyboard and motion contract", () => {
  const layout = read("app/layout.tsx");
  const baseStyles = read("styles/base.css");
  const screenStyles = read("styles/screens.css");

  assert.match(layout, /skip-link/);
  assert.match(layout, /MotionConfig/);
  assert.match(baseStyles, /focus-visible/);
  assert.match(baseStyles, /prefers-reduced-motion/);
  assert.match(baseStyles, /forced-colors/);
  assert.match(baseStyles, /min-height:\s*44px/);
  assert.match(screenStyles, /\.skip-link:focus-visible/);
  assert.match(screenStyles, /\.glass-signin-social-btn[\s\S]*min-height:\s*44px/);
});

test("authentication fields expose explicit labels and validation relationships", () => {
  const signIn = read("../src/components/components/forms/glass-sign-in.tsx");
  const forgotPassword = read("../src/components/components/forms/glass-forgot-password.tsx");

  assert.match(signIn, /htmlFor="auth-email"/);
  assert.match(signIn, /id="auth-email"/);
  assert.match(signIn, /aria-describedby=\{fieldError\.email \? "auth-email-error" : undefined\}/);
  assert.match(signIn, /aria-invalid=\{Boolean\(fieldError\.email\)\}/);
  assert.match(signIn, /role="alert"/);
  assert.match(forgotPassword, /htmlFor="forgot-email"/);
  assert.match(forgotPassword, /id="forgot-email"/);
  assert.match(forgotPassword, /role="alert"/);
});
