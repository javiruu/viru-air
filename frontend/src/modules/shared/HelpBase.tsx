"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

import AirLoader from "@/modules/shared/AirLoader";
import { apiFetch } from "@/modules/shared/api";

export type HelpSection = {
  title: string;
  body: string;
  cta_label?: string;
  cta_href?: string;
};
type HelpPayload = { title: string; status?: { state: string; message: string }; sections: HelpSection[] };

type HelpBaseProps = {
  endpoint: "/public/help" | "/support/help";
  context: "public" | "private";
  title: string;
  subtitle: string;
  loadingLabel: string;
  loadedSubtitle: string;
  systemStatusLabel: string;
  backHref?: string;
  backLabel?: string;
  publicLoginLabel?: string;
  publicRegisterLabel?: string;
  privateFeedbackLabel?: string;
  privateSuggestionsLabel?: string;
};

export default function HelpBase(props: HelpBaseProps) {
  const [help, setHelp] = useState<HelpPayload | null>(null);

  useEffect(() => {
    apiFetch<HelpPayload>(props.endpoint)
      .then(setHelp)
      .catch(() => setHelp(null));
  }, [props.endpoint]);

  if (!help) {
    return (
      <main className="shell" id="main-content">
        <div className="page-header">
          <div className="page-title">
            <h1>{props.title}</h1>
            <p>{props.subtitle}</p>
          </div>
        </div>
        <section className="panel panel-soft air-loader-section">
          <AirLoader size={0.85} />
          <p className="muted">{props.loadingLabel}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell" id="main-content">
      <div className="page-header">
        <div className="page-title">
          <h1>{help.title}</h1>
          <p>{props.loadedSubtitle}</p>
        </div>
        <div className="row-actions">
          {props.backHref && props.backLabel ? (
            <Link className="btn-ghost" href={props.backHref}>
              {props.backLabel}
            </Link>
          ) : null}
          {props.context === "public" ? (
            <>
              <Link className="btn-ghost" href="/login">
                {props.publicLoginLabel ?? "Login"}
              </Link>
              <Link className="btn-primary" href="/register">
                {props.publicRegisterLabel ?? "Register"}
              </Link>
            </>
          ) : (
            <>
              <Link className="btn-ghost" href="/soporte/feedback?type=bug">
                {props.privateFeedbackLabel ?? "Report issue"}
              </Link>
              <Link className="btn-primary" href="/suggestions">
                {props.privateSuggestionsLabel ?? "Suggestions"}
              </Link>
            </>
          )}
        </div>
      </div>

      {help.status ? (
        <section className="panel panel-soft">
          <div className="panel-header">
            <h2>{props.systemStatusLabel}</h2>
            <span className={`status-badge ${help.status.state === "ok" ? "status-ok" : "status-degraded"}`}>
              {help.status.message}
            </span>
          </div>
        </section>
      ) : null}

      <HelpSections sections={help.sections} />
    </main>
  );
}

function sectionCta(section: HelpSection): { label: string; href: string } | null {
  const label = section.cta_label?.trim();
  const href = section.cta_href?.trim();
  if (!label || !href) return null;
  return { label, href };
}

export function HelpSections({ sections }: { sections: HelpSection[] }) {
  return (
    <>
      {sections.map((section, index) => {
        const cta = sectionCta(section);
        return (
          <section key={`${section.title}-${index}`} className="panel">
            <div className="panel-header">
              <h2>{section.title}</h2>
            </div>
            <p className="panel-note">{section.body}</p>
            {cta ? (
              <div className="row-actions">
                <Link className="btn-ghost" href={cta.href}>
                  {cta.label}
                </Link>
              </div>
            ) : null}
          </section>
        );
      })}
    </>
  );
}
