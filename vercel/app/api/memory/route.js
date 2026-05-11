/**
 * Zuki Cloud-Gedächtnis — Vercel API Route
 * ─────────────────────────────────────────
 * Pfad in deinem Next.js-Projekt:  app/api/memory/route.js
 *
 * Setup:
 *   1. npm install @vercel/kv
 *   2. Vercel Dashboard → Storage → KV erstellen → mit Projekt verknüpfen
 *   3. Environment Variables in Vercel setzen:
 *        CLOUD_MEMORY_TOKEN = dein-geheimer-token   (selbst wählen)
 *      (KV_URL etc. werden automatisch von Vercel gesetzt)
 *   4. Selben Token in D:\Zuki\.env eintragen:
 *        CLOUD_MEMORY_TOKEN = dein-geheimer-token
 *
 * Endpunkte:
 *   POST /api/memory   → Eintrag speichern
 *   GET  /api/memory   → Letzte Einträge abrufen (?limit=20&session=...)
 */

import { NextResponse } from "next/server";
import { kv } from "@vercel/kv";

const KV_KEY_ALL      = "zuki:memories";       // globale Liste (alle Sessions)
const KV_KEY_SESSION  = (id) => `zuki:session:${id}`;
const MAX_ENTRIES     = 200;                    // globales Maximum im KV
const SESSION_TTL_SEC = 60 * 60 * 24 * 7;      // 7 Tage TTL pro Session

// ── Auth-Helper ─────────────────────────────────────────────────────────────

function isAuthorized(request) {
  const token = request.headers.get("x-zuki-token");
  return token === process.env.CLOUD_MEMORY_TOKEN;
}

// ── POST — Eintrag speichern ─────────────────────────────────────────────────

export async function POST(request) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { text, source, session_id, timestamp, save_nr } = body;

  if (!text || typeof text !== "string") {
    return NextResponse.json({ error: "'text' field required" }, { status: 400 });
  }

  const entry = {
    text:       text.slice(0, 8000),     // max 8000 Zeichen pro Eintrag
    source:     source     || "manual",
    session_id: session_id || "unknown",
    timestamp:  timestamp  || new Date().toISOString(),
    save_nr:    save_nr    || null,
    saved_at:   new Date().toISOString(),
  };

  const serialized = JSON.stringify(entry);

  // In globale Liste (neueste zuerst) + auf MAX_ENTRIES kürzen
  await kv.lpush(KV_KEY_ALL, serialized);
  await kv.ltrim(KV_KEY_ALL, 0, MAX_ENTRIES - 1);

  // Session-spezifische Liste mit TTL
  if (session_id) {
    const sessionKey = KV_KEY_SESSION(session_id);
    await kv.lpush(sessionKey, serialized);
    await kv.expire(sessionKey, SESSION_TTL_SEC);
  }

  const total = await kv.llen(KV_KEY_ALL);

  return NextResponse.json({
    status:     "saved",
    session_id: entry.session_id,
    total,
  });
}

// ── GET — Einträge abrufen ───────────────────────────────────────────────────

export async function GET(request) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const limit     = Math.min(parseInt(searchParams.get("limit") || "20"), 100);
  const sessionId = searchParams.get("session");

  let raw;
  if (sessionId) {
    // Nur Einträge dieser Session
    raw = await kv.lrange(KV_KEY_SESSION(sessionId), 0, limit - 1);
  } else {
    // Alle Einträge global
    raw = await kv.lrange(KV_KEY_ALL, 0, limit - 1);
  }

  const memories = raw.map((item) => {
    try {
      return typeof item === "string" ? JSON.parse(item) : item;
    } catch {
      return { raw: item };
    }
  });

  const total = await kv.llen(sessionId ? KV_KEY_SESSION(sessionId) : KV_KEY_ALL);

  return NextResponse.json({ memories, total, returned: memories.length });
}
