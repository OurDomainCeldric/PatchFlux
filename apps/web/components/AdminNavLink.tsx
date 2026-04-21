"use client";

import { useEffect, useState } from "react";
import { NavLink } from "@/components/NavLink";

const STORAGE_KEY = "patchflux:functionKey";

/**
 * Renders the Admin nav link only when the user has previously saved a
 * Function-App key in ``localStorage`` via the Admin console. Operators can
 * still reach ``/{locale}/admin`` directly by URL; this component just keeps
 * the entry out of sight for casual visitors. All enforcement still lives
 * server-side on ``/api/ingest`` (FUNCTION-level auth).
 */
export function AdminNavLink({ href, label }: { href: string; label: string }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      setShow(Boolean(localStorage.getItem(STORAGE_KEY)));
    } catch {
      /* ignore */
    }
  }, []);
  if (!show) return null;
  return <NavLink href={href}>{label}</NavLink>;
}
