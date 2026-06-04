"use client";

import { useCallback, useState } from "react";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import {
  createHotelAlertRule,
  deleteHotelAlertRule,
  listHotelAlertEvents,
  listHotelAlertRules,
  updateHotelAlertRule,
} from "../api";
import type { HotelAlertEventOut, HotelAlertRuleOut, HotelAlertRuleType } from "../types";
import { resolveHotelMessage } from "./useHotelSearch";

export function useHotelAlerts() {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();

  const [alertRules, setAlertRules] = useState<HotelAlertRuleOut[]>([]);
  const [alertRulesLoading, setAlertRulesLoading] = useState(false);
  const [alertRulesError, setAlertRulesError] = useState<string | null>(null);
  const [alertEvents, setAlertEvents] = useState<HotelAlertEventOut[]>([]);
  const [alertEventsLoading, setAlertEventsLoading] = useState(false);
  const [alertEventsError, setAlertEventsError] = useState<string | null>(null);
  const [alertCreateBusy, setAlertCreateBusy] = useState(false);
  const [alertBusyRuleIds, setAlertBusyRuleIds] = useState<string[]>([]);

  const refreshAlertRules = useCallback(async () => {
    setAlertRulesLoading(true);
    setAlertRulesError(null);
    try {
      const items = await listHotelAlertRules();
      setAlertRules(items);
    } catch (error) {
      setAlertRulesError(
        resolveHotelMessage(error, t) || t("hotels.alerts.loadRulesError"),
      );
    } finally {
      setAlertRulesLoading(false);
    }
  }, [t]);

  const refreshAlertEvents = useCallback(
    async (hotelId?: string | null) => {
      setAlertEventsLoading(true);
      setAlertEventsError(null);
      try {
        if (!hotelId) {
          setAlertEvents([]);
          return;
        }
        const items = await listHotelAlertEvents({ hotel_id: hotelId, limit: 50 });
        setAlertEvents(items);
      } catch (error) {
        setAlertEventsError(
          resolveHotelMessage(error, t) || t("hotels.alerts.loadEventsError"),
        );
      } finally {
        setAlertEventsLoading(false);
      }
    },
    [t],
  );

  const markAlertRuleBusy = useCallback((ruleId: string, isBusy: boolean) => {
    setAlertBusyRuleIds((current) => {
      if (isBusy) return current.includes(ruleId) ? current : [...current, ruleId];
      return current.filter((item) => item !== ruleId);
    });
  }, []);

  const handleCreateAlertRule = useCallback(
    async (payload: {
      hotel_id: string;
      tracked_offer_id?: string | null;
      rule_type: HotelAlertRuleType;
      threshold_amount: number | null;
      threshold_percent: number | null;
      compare_against?: string;
      is_active: boolean;
    }): Promise<boolean> => {
      setAlertCreateBusy(true);
      try {
        await createHotelAlertRule(payload);
        await refreshAlertRules();
        notify({ tone: "success", title: t("hotels.messages.alertCreated") });
        return true;
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
        return false;
      } finally {
        setAlertCreateBusy(false);
      }
    },
    [refreshAlertRules, notify, t],
  );

  const handleToggleAlertRule = useCallback(
    async (ruleId: string, isActive: boolean) => {
      markAlertRuleBusy(ruleId, true);
      try {
        await updateHotelAlertRule(ruleId, { is_active: isActive });
        await refreshAlertRules();
        notify({ tone: "success", title: t("hotels.messages.alertUpdated") });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
      } finally {
        markAlertRuleBusy(ruleId, false);
      }
    },
    [refreshAlertRules, markAlertRuleBusy, notify, t],
  );

  const handleDeleteAlertRule = useCallback(
    async (ruleId: string) => {
      markAlertRuleBusy(ruleId, true);
      try {
        await deleteHotelAlertRule(ruleId);
        await refreshAlertRules();
        notify({ tone: "success", title: t("hotels.messages.alertDeleted") });
      } catch (error) {
        const message = resolveHotelMessage(error, t);
        notify({ tone: "error", title: message });
      } finally {
        markAlertRuleBusy(ruleId, false);
      }
    },
    [refreshAlertRules, markAlertRuleBusy, notify, t],
  );

  return {
    alertRules,
    alertRulesLoading,
    alertRulesError,
    alertEvents,
    alertEventsLoading,
    alertEventsError,
    alertCreateBusy,
    alertBusyRuleIds,
    refreshAlertRules,
    refreshAlertEvents,
    handleCreateAlertRule,
    handleToggleAlertRule,
    handleDeleteAlertRule,
  };
}
