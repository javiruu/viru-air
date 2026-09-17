import assert from "node:assert/strict";
import test from "node:test";

import { resolveSupabaseConfig } from "../src/lib/supabase/client";

type EnvKey = "NEXT_PUBLIC_SUPABASE_URL" | "NEXT_PUBLIC_SUPABASE_ANON_KEY" | "NODE_ENV";

function withEnv(env: Partial<Record<EnvKey, string>>, fn: () => void): void {
  const mutableEnv = process.env as Record<string, string | undefined>;
  const snapshot: Partial<Record<EnvKey, string | undefined>> = {};
  for (const key of Object.keys(env) as EnvKey[]) {
    snapshot[key] = mutableEnv[key];
    if (env[key] === undefined) {
      delete mutableEnv[key];
    } else {
      mutableEnv[key] = env[key];
    }
  }
  try {
    fn();
  } finally {
    for (const key of Object.keys(snapshot) as EnvKey[]) {
      const value = snapshot[key];
      if (value === undefined) {
        delete mutableEnv[key];
      } else {
        mutableEnv[key] = value;
      }
    }
  }
}

test("production without Supabase env vars fails fast instead of mocking", () => {
  withEnv({ NODE_ENV: "production" }, () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    assert.throws(() => resolveSupabaseConfig(), /Supabase client is not configured/);
  });
});

test("development keeps a mock fallback so tests run without credentials", () => {
  withEnv({ NODE_ENV: "development" }, () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    const config = resolveSupabaseConfig();
    assert.equal(config.url, "https://mock.supabase.co");
    assert.equal(config.key, "mock-anon-key");
  });
});

test("production with real env vars uses them verbatim", () => {
  withEnv(
    {
      NODE_ENV: "production",
      NEXT_PUBLIC_SUPABASE_URL: "https://real-project.supabase.co",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "real-anon-key",
    },
    () => {
      const config = resolveSupabaseConfig();
      assert.equal(config.url, "https://real-project.supabase.co");
      assert.equal(config.key, "real-anon-key");
    },
  );
});
