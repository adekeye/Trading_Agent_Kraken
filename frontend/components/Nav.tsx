"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, setToken } from "../lib/api";
import type { UserSettings } from "../lib/types";
import {
  TerminalIcon,
  WalletIcon,
  ListIcon,
  HistoryIcon,
  ShieldIcon,
  SettingsIcon,
  KeyIcon,
  LogOutIcon,
  UserIcon,
  PowerIcon,
} from "./Icons";

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
        <span className="mark" aria-hidden="true" />
        Kraken Terminal
      </Link>
      {authed && (
        <>
          <Link href="/"><TerminalIcon /> Trade</Link>
          <Link href="/balances"><WalletIcon /> Balances</Link>
          <Link href="/orders"><ListIcon /> Orders</Link>
          <Link href="/history"><HistoryIcon /> History</Link>
          <Link href="/audit"><ShieldIcon /> Audit</Link>
          <Link href="/settings"><SettingsIcon /> Settings</Link>
          <Link href="/connect"><KeyIcon /> API</Link>
        </>
      )}
      <div className="spacer" />
      {settings && (
        <>
          <span className={`badge ${settings.dry_run ? "dry" : "live"}`}>
            <span className={`dot ${settings.dry_run ? "warn" : "gain"}`} />
            {settings.dry_run ? "Dry-run" : "Live"}
          </span>
          {!settings.trading_enabled && (
            <span className="badge kill"><PowerIcon /> Kill switch</span>
          )}
        </>
      )}
      {authed ? (
        <button className="ghost" onClick={logout} aria-label="Log out">
          <LogOutIcon /> Log out
        </button>
      ) : (
        <>
          <Link href="/login"><UserIcon /> Login</Link>
          <Link href="/register">Register</Link>
        </>
      )}
    </nav>
  );
}
