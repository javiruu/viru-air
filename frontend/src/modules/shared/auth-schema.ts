import { z } from "zod";

/**
 * Zod schema for validating user session tokens and payloads stored in browser storage.
 * Prevents corrupted or malicious local storage data from causing runtime crashes.
 * Follows viru-modernization-codex/07_ZOD.md.
 */
export const sessionTokenPayloadSchema = z.object({
  sub: z.string().min(1, "Subject (user ID) cannot be empty"),
  exp: z.number().int().positive("Expiration timestamp must be positive"),
  role: z.enum(["user", "admin", "moderator"]).default("user"),
  email: z.string().email().optional(),
});

export type SessionTokenPayload = z.infer<typeof sessionTokenPayloadSchema>;

export const authStorageSchema = z.object({
  access_token: z.string().min(10, "Token too short to be valid"),
  refresh_token: z.string().min(10).optional(),
});

export type AuthStorage = z.infer<typeof authStorageSchema>;

export function parseStoredAuth(raw: unknown): AuthStorage | null {
  const result = authStorageSchema.safeParse(raw);
  if (!result.success) {
    return null;
  }
  return result.data;
}
