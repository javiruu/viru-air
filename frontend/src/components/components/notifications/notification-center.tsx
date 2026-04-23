"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, BellRing, CheckCircle2, CircleAlert, X } from "lucide-react";

export type NotificationTone = "success" | "error" | "warning" | "info";

export type NotificationInput = {
  title: string;
  description?: string;
  tone?: NotificationTone;
  actionLabel?: string;
  onAction?: () => void;
  durationMs?: number;
  sticky?: boolean;
};

type NotificationItem = NotificationInput & {
  id: string;
  tone: NotificationTone;
};

type NotificationCenterContextValue = {
  items: NotificationItem[];
  notify: (input: NotificationInput) => string;
  dismiss: (id: string) => void;
  clear: () => void;
};

const NotificationCenterContext = createContext<NotificationCenterContextValue | null>(null);
const DEFAULT_DURATION_MS = 5200;
const MAX_NOTIFICATIONS = 5;

function toneIcon(tone: NotificationTone) {
  if (tone === "success") return CheckCircle2;
  if (tone === "warning") return AlertTriangle;
  if (tone === "error") return CircleAlert;
  return BellRing;
}

function toneClass(tone: NotificationTone) {
  if (tone === "success") return "notice-success";
  if (tone === "warning") return "notice-warning";
  if (tone === "error") return "notice-error";
  return "notice-info";
}

function toneLiveMode(tone: NotificationTone): { role: "status" | "alert"; live: "polite" | "assertive" } {
  if (tone === "error" || tone === "warning") return { role: "alert", live: "assertive" };
  return { role: "status", live: "polite" };
}

function NotificationCard({
  item,
  onClose,
}: {
  item: NotificationItem;
  onClose: (id: string) => void;
}) {
  const timeoutRef = useRef<number | null>(null);
  const duration = item.durationMs ?? DEFAULT_DURATION_MS;
  const sticky = Boolean(item.sticky) || duration <= 0;
  const Icon = toneIcon(item.tone);
  const live = toneLiveMode(item.tone);

  useEffect(() => {
    if (sticky) return;
    timeoutRef.current = window.setTimeout(() => {
      onClose(item.id);
    }, duration);
    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, [duration, item.id, onClose, sticky]);

  return (
    <motion.article
      className={`notification-card ${toneClass(item.tone)}`}
      role={live.role}
      aria-live={live.live}
      initial={{ opacity: 0, y: -18, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.98 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
    >
      <div className="notification-card-head">
        <span className="notification-card-icon" aria-hidden="true">
          <Icon size={16} />
        </span>
        <div className="notification-card-copy">
          <strong>{item.title}</strong>
          {item.description ? <p>{item.description}</p> : null}
        </div>
        <button
          type="button"
          className="notification-card-dismiss"
          aria-label="Cerrar notificación"
          onClick={() => onClose(item.id)}
        >
          <X size={14} />
        </button>
      </div>

      {item.actionLabel && item.onAction ? (
        <div className="notification-card-actions">
          <button
            type="button"
            className="btn-ghost btn-compact"
            onClick={() => {
              item.onAction?.();
              onClose(item.id);
            }}
          >
            {item.actionLabel}
          </button>
        </div>
      ) : null}
    </motion.article>
  );
}

export function NotificationCenter() {
  const context = useContext(NotificationCenterContext);
  if (!context) return null;

  return (
    <div className="notification-center" aria-label="Centro de notificaciones" aria-live="polite">
      <AnimatePresence initial={false}>
        {context.items.map((item) => (
          <NotificationCard key={item.id} item={item} onClose={context.dismiss} />
        ))}
      </AnimatePresence>
    </div>
  );
}

export function NotificationCenterProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const idSeedRef = useRef(0);

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const clear = useCallback(() => {
    setItems([]);
  }, []);

  const notify = useCallback((input: NotificationInput) => {
    idSeedRef.current += 1;
    const id = `viru-notice-${Date.now()}-${idSeedRef.current}`;
    const tone = input.tone || "info";
    const nextItem: NotificationItem = { ...input, tone, id };
    setItems((prev) => [nextItem, ...prev].slice(0, MAX_NOTIFICATIONS));
    return id;
  }, []);

  return (
    <NotificationCenterContext.Provider value={{ items, notify, dismiss, clear }}>
      {children}
      <NotificationCenter />
    </NotificationCenterContext.Provider>
  );
}

export function useNotificationCenter() {
  const context = useContext(NotificationCenterContext);
  if (!context) {
    throw new Error("useNotificationCenter must be used within NotificationCenterProvider");
  }
  return context;
}
