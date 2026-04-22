export type AccountMenuItem = {
  label: string;
  href: string;
  icon: string;
};

export type AccountMenuGroup = {
  title: string;
  hint: string;
  items: AccountMenuItem[];
};

export function buildAccountMenuGroups(t: (key: string) => string): AccountMenuGroup[] {
  return [
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
        { label: t("account.menu.aboutUs"), href: "/soporte/about-us", icon: "fa-people-group" },
      ],
    },
  ];
}
