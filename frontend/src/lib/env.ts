import { z } from "zod";

/**
 * Runtime environment schema validation.
 * Fails fast with clear error messages without exposing secret values.
 * Follows viru-modernization-codex/07_ZOD.md.
 */
export const clientEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
  NEXT_PUBLIC_GA_MEASUREMENT_ID: z.string().min(1).optional(),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
});

export type ClientEnv = z.infer<typeof clientEnvSchema>;

export function validateEnv(rawEnv: Record<string, unknown> = process.env): ClientEnv {
  const result = clientEnvSchema.safeParse(rawEnv);
  if (!result.success) {
    const errorDetails = result.error.issues
      .map((issue) => `${issue.path.join(".")}: ${issue.message}`)
      .join(", ");
    throw new Error(`Environment configuration validation failed: ${errorDetails}`);
  }
  return result.data;
}
