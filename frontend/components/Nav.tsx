"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, setToken } from "../lib/api";
import type { UserSettings } from "../lib/types";

export default function Nav() {
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean>(false);
  const [settings, setSettings] = useState<UserSettings | null>(null);

  useEffect(() => {
    setAuthed(!!getToken());
  }, []);

  useEffect(() => {
    if (!authed) return;
    api.get<UserSettings>("/settings").then(setSettings).catch(() => setSettings(null));
  }, [authed]);

  function logout() {
    setToken(null);
    setAuthed(false);
    router.push("/login");
  }

  return (
    <nav className="topnav">
      <Link href="/" className="brand" aria-label="Go to home">
        ⚓ Kraken Trading Agent
      </Link>
      {authed && (
        <>
          <Link href="/">Trade</Link>
          <Link href="/balances">Balances</Link>
          <Link href="/orders">Open Orders</Link>
          <Link href="/history">History</Link>
          <Link href="/audit">Audit</Link>
          <Link href="/settings">Settings</Link>
          <Link href="/connect">Connect Kraken</Link>
        </>
      )}
      <div className="spacer" />
      {settings && (
        <>
          <span className={`badge ${settings.dry_run ? "dry" : "live"}`}>
            {settings.dry_run ? "DRY-RUN" : "LIVE"}
          </span>
          {!settings.trading_enabled && <span className="badge kill">KILL SWITCH</span>}
        </>
      )}
      {authed ? (
        <button className="ghost" onClick={logout}>Log out</button>
      ) : (
        <>
          <Link href="/login">Login</Link>
          <Link href="/register">Register</Link>
        </>
      )}
    </nav>
  );
}
