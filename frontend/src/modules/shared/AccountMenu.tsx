"use client";

import Link from "next/link";
import { type KeyboardEvent as ReactKeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetchWithStatus } from "@/modules/shared/api";
import { clearToken } from "@/modules/shared/auth";
import { persistLocale, useI18n } from "@/i18n";

type Me = { id: string; email: string; locale: string; is_admin: boolean };

function getInitials(value: string): string {
  const clean = value.trim();
  if (!clean) return "US";
  const [first, second] = clean.split(/[\s.@_-]+/).filter(Boolean);
  if (!first) return "US";
  if (!second) return first.slice(0, 2).toUpperCase();
  return `${first[0]}${second[0]}`.toUpperCase();
}

export default function AccountMenu() {
  const router = useRouter();
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    apiFetchWithStatus<Me>("/auth/me").then((result) => {
      if (!result.ok) {
        if (result.status === 401) {
          clearToken();
        }
        setMe(null);
        return;
      }
      const data = result.data;
      setMe(data);
      if (data?.locale) {
        persistLocale(data.locale === "en" ? "en" : "es");
      }
    });
  }, []);

  useEffect(() => {
    function onDocPointerDown(event: PointerEvent) {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onDocKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onDocPointerDown);
    document.addEventListener("keydown", onDocKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onDocPointerDown);
      document.removeEventListener("keydown", onDocKeyDown);
    };
  }, []);

  useEffect(() => {
    if (!open || !menuRef.current) return;
    const firstItem = menuRef.current.querySelector<HTMLElement>("[data-menu-item='true']");
    firstItem?.focus();
  }, [open]);

  const initials = useMemo(() => getInitials(me?.email || me?.id || t("account.menu.label")), [me?.email, me?.id, t]);
  const accountLabel = me?.email || t("account.menu.label");

  const menuGroups = useMemo(
    () => [
      {
        title: t("account.menu.accountGroup"),
        hint: t("account.menu.hints.accountGroup"),
        items: [
          { label: t("account.menu.profile"), href: "/cuenta/perfil", icon: "fa-id-card-clip" },
          { label: t("account.menu.security"), href: "/cuenta/seguridad", icon: "fa-shield-lock" },
        ],
      },
      {
        title: t("account.menu.preferencesGroup"),
        hint: t("account.menu.hints.preferencesGroup"),
        items: [{ label: t("account.menu.preferencesHub"), href: "/preferencias", icon: "fa-sliders" }],
      },
      {
        title: t("account.menu.supportGroup"),
        hint: t("account.menu.hints.supportGroup"),
        items: [
          { label: t("account.menu.help"), href: "/soporte/ayuda", icon: "fa-headset" },
          { label: t("account.menu.contact"), href: "/soporte/contacto", icon: "fa-paper-plane" },
        ],
      },
    ],
    [t],
  );

  function onTriggerKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setOpen((prev) => !prev);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
    }
  }

  function onLogout() {
    clearToken();
    window.localStorage.setItem("viru-logout-notice", "true");
    router.push("/");
  }

  return (
    <div className="account-menu" ref={menuRef}>
      <button
        type="button"
        className="account-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("shared.a11y.openAccountMenu")}
        onClick={() => setOpen((prev) => !prev)}
        onKeyDown={onTriggerKeyDown}
        ref={triggerRef}
      >
        <span className="account-avatar" aria-hidden="true">{initials}</span>
        <span className="account-meta">
          <strong>{accountLabel}</strong>
          <small>{t("account.menu.status")}</small>
        </span>
        <span className="account-caret" aria-hidden="true">v</span>
      </button>

      {open ? (
        <div className="account-dropdown" role="menu" aria-label={t("shared.a11y.accountMenu")}>
          <div className="account-status-panel">
            <div className="account-status-top">
              <strong>{accountLabel}</strong>
              <span className={`status-badge status-ok`}>{t("account.menu.status")}</span>
            </div>
            <p>{t("account.menu.statusHint")}</p>
          </div>

          <div className="account-group-grid">
            {menuGroups.map((group) => (
              <div key={group.title} className="account-group-card">
                <div className="account-group-card-header">
                  <span>{group.title}</span>
                  <small>{group.hint}</small>
                </div>
                <div className="account-group-items">
                  {group.items.map((item) => (
                    <Link
                      key={item.label}
                      data-menu-item="true"
                      href={item.href}
                      role="menuitem"
                      className="account-link"
                      onClick={() => setOpen(false)}
                    >
                      <span className="account-link-icon" aria-hidden="true">
                        <i className={`fa-solid ${item.icon}`}></i>
                      </span>
                      <span>{item.label}</span>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {me?.is_admin ? (
            <Link
              data-menu-item="true"
              href="/admin"
              role="menuitem"
              className="account-link account-link-admin"
              onClick={() => setOpen(false)}
            >
              <span className="account-link-icon" aria-hidden="true">
                <i className="fa-solid fa-crown"></i>
              </span>
              <span>{t("account.menu.admin")}</span>
            </Link>
          ) : null}

          <div className="account-divider" role="separator" />
          <button
            data-menu-item="true"
            type="button"
            className="btn-danger account-logout"
            role="menuitem"
            onClick={onLogout}
          >
            <span className="account-link-icon" aria-hidden="true">
              <i className="fa-solid fa-right-from-bracket"></i>
            </span>
            <span>{t("account.menu.logout")}</span>
            <small>{t("account.menu.logoutHint")}</small>
          </button>
        </div>
      ) : null}
    </div>
  );
}
