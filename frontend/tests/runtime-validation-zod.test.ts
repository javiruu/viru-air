import assert from "node:assert/strict";
import test from "node:test";
import { validateEnv } from "../src/lib/env";
import { parseStoredAuth, sessionTokenPayloadSchema } from "../src/modules/shared/auth-schema";

test("validateEnv accepts valid environment and provides defaults", () => {
  const env = validateEnv({
    NEXT_PUBLIC_API_URL: "https://api.viru.com",
    NODE_ENV: "production",
  });
  assert.equal(env.NEXT_PUBLIC_API_URL, "https://api.viru.com");
  assert.equal(env.NODE_ENV, "production");
});

test("validateEnv rejects invalid URLs without printing secrets", () => {
  assert.throws(() => {
    validateEnv({
      NEXT_PUBLIC_API_URL: "not-a-valid-url",
    });
  }, /Environment configuration validation failed/);
});

test("parseStoredAuth accepts valid token pair and rejects malformed values", () => {
  const valid = parseStoredAuth({
    access_token: "mock-valid-jwt-token-xyz-12345",
    refresh_token: "mock-refresh-token-xyz-12345",
  });
  assert.ok(valid);
  assert.equal(valid.access_token, "mock-valid-jwt-token-xyz-12345");

  // Reject too short / corrupt token
  const invalidShort = parseStoredAuth({
    access_token: "abc",
  });
  assert.equal(invalidShort, null);

  // Reject non-object
  const invalidPrimitive = parseStoredAuth("random-string-not-object");
  assert.equal(invalidPrimitive, null);
});

test("sessionTokenPayloadSchema parses valid JWT claims and rejects negative expiration", () => {
  const validPayload = sessionTokenPayloadSchema.parse({
    sub: "user-12345",
    exp: Math.floor(Date.now() / 1000) + 3600,
    role: "admin",
    email: "test@viru.com",
  });
  assert.equal(validPayload.sub, "user-12345");
  assert.equal(validPayload.role, "admin");

  const invalid = sessionTokenPayloadSchema.safeParse({
    sub: "",
    exp: -100,
  });
  assert.equal(invalid.success, false);
});
