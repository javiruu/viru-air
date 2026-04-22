type Translator = (key: string) => string;

export type SupportAboutMember = {
  name: string;
  role: string;
  summary: string;
  focus: string[];
  accent: "coral" | "sage";
};

export function buildSupportAboutMembers(t: Translator): SupportAboutMember[] {
  return [
    {
      name: t("support.aboutUs.team.members.aria.name"),
      role: t("support.aboutUs.team.members.aria.role"),
      summary: t("support.aboutUs.team.members.aria.summary"),
      focus: [
        t("support.aboutUs.team.members.aria.focus.one"),
        t("support.aboutUs.team.members.aria.focus.two"),
      ],
      accent: "coral",
    },
    {
      name: t("support.aboutUs.team.members.luca.name"),
      role: t("support.aboutUs.team.members.luca.role"),
      summary: t("support.aboutUs.team.members.luca.summary"),
      focus: [
        t("support.aboutUs.team.members.luca.focus.one"),
        t("support.aboutUs.team.members.luca.focus.two"),
      ],
      accent: "sage",
    },
    {
      name: t("support.aboutUs.team.members.sara.name"),
      role: t("support.aboutUs.team.members.sara.role"),
      summary: t("support.aboutUs.team.members.sara.summary"),
      focus: [
        t("support.aboutUs.team.members.sara.focus.one"),
        t("support.aboutUs.team.members.sara.focus.two"),
      ],
      accent: "coral",
    },
    {
      name: t("support.aboutUs.team.members.diego.name"),
      role: t("support.aboutUs.team.members.diego.role"),
      summary: t("support.aboutUs.team.members.diego.summary"),
      focus: [
        t("support.aboutUs.team.members.diego.focus.one"),
        t("support.aboutUs.team.members.diego.focus.two"),
      ],
      accent: "sage",
    },
  ];
}
