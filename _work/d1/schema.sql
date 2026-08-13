-- Tabla de leads del formulario de contacto (site/contacto.html).
-- Aplícala con:
--   wrangler d1 execute <nombre-de-tu-db> --remote --file=_work/d1/schema.sql

CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  nombre TEXT NOT NULL,
  contacto TEXT NOT NULL,
  empresa TEXT,
  solucion TEXT NOT NULL,
  preferencia TEXT,
  info TEXT,
  user_agent TEXT,
  ip TEXT
);

CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at);
