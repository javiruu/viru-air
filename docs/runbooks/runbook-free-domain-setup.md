# Runbook: Configuración de dominio gratuito con FreeDomain

**Propósito**: Desplegar viru-tracker con un dominio personalizado gratuito usando [DigitalPlat FreeDomain](https://github.com/DigitalPlatDev/FreeDomain).

**Estado**: vivo
**Fuente de verdad**: sí

---

## Resumen

FreeDomain ofrece dominios gratuitos bajo extensiones como `.DPDNS.ORG`, `.US.KG`, `.QZZ.IO`, `.XX.KG` y `.QD.JE`. Estos dominios pueden apuntarse a tu servidor usando un proveedor DNS externo (Cloudflare, FreeDNS, etc.).

viru-tracker ya está preparado para funcionar con cualquier dominio personalizado gracias a:
- Reverse proxy **Caddy** con auto-HTTPS (Let's Encrypt).
- Backend con CORS dinámico que acepta el dominio configurado vía `DOMAIN`.
- Frontend configurable con `NEXT_PUBLIC_API_URL`.

---

## Paso 1: Registrar un dominio en FreeDomain

1. Ve al dashboard: [https://dash.domain.digitalplat.org/](https://dash.domain.digitalplat.org/)
2. Busca un nombre disponible para tu tracker (ej: `virutracker`, `viru-flight`, `tracker-viru`).
3. Elige una extensión disponible (`.dpdns.org`, `.us.kg`, `.qzz.io`, `.xx.kG`, `.qd.je`).
4. Regístrate y completa el registro. **No hay API programática**: el registro es manual desde el dashboard.
5. Anota tu dominio completo (ej: `virutracker.dpdns.org`).

---

## Paso 2: Configurar DNS

FreeDomain **no gestiona DNS directamente**. Debes delegar el dominio a un proveedor DNS externo.

### Opción A: Cloudflare (recomendado)

1. Crea una cuenta gratuita en [Cloudflare](https://cloudflare.com).
2. Añade tu dominio FreeDomain como sitio.
3. Cloudflare te dará dos nameservers. Vuelve al dashboard de FreeDomain y configura esos nameservers para tu dominio.
4. En Cloudflare, crea estos registros DNS:
   - **Tipo A**: `@` → IP de tu servidor (`45.136.18.49` u otra)
   - **Tipo A**: `api` → IP de tu servidor (si usas subdominio separado para API)

### Opción B: FreeDNS (Afraid.org)

1. Ve a [freedns.afraid.org](https://freedns.afraid.org) y crea cuenta.
2. Añade tu dominio FreeDomain.
3. Configura los nameservers de FreeDNS en el dashboard de FreeDomain.
4. Crea un registro **A** apuntando a la IP de tu servidor.

> **Nota**: La propagación DNS puede tardar de minutos a 48 horas. Verifica con `nslookup tu-dominio.dpdns.org`.

---

## Paso 3: Configurar el servidor

Una vez que tengas el servidor con Docker y el repo clonado:

### 3.1. Crear archivo `.env` de producción

```bash
cp infra/.env.prod.example infra/.env
```

Editar `infra/.env`:

```env
DOMAIN=virutracker.dpdns.org
NEXT_PUBLIC_API_URL=/api/v1
JWT_SECRET=<genera-un-valor-seguro>
APP_ENV=production
```

### 3.2. Desplegar con Caddy

```bash
cd infra
DOMAIN=virutracker.dpdns.org docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Caddy:
- Escucha en puertos 80 y 443.
- Redirige tráfico a `viru-frontend:3000` (Next.js) y `viru-backend:8000` (API).
- Auto-provisiona certificado TLS con Let's Encrypt.

### 3.3. Verificar

```bash
# API health check
curl https://virutracker.dpdns.org/api/v1/health

# Frontend
curl -I https://virutracker.dpdns.org/
```

---

## Paso 4: Configurar CORS (si la API está en otro dominio)

Si el frontend y la API comparten dominio (configuración recomendada con Caddy), **no se necesita CORS adicional**.

Si usas dominios separados (ej: `api.virutracker.dpdns.org`), configura:

```env
# backend/.env
DOMAIN=api.virutracker.dpdns.org
CORS_ALLOW_ORIGINS=https://virutracker.dpdns.org
```

---

## Limitaciones de FreeDomain

1. **Sin SLA**: FreeDomain es un proyecto sin ánimo de lucro. No garantiza uptime.
2. **Dominios de segundo nivel**: Los dominios son subdominios de TLDs controlados por terceros.
3. **Registro manual**: No hay API. El registro se hace vía dashboard web.
4. **Política de abuso**: El uso malicioso resulta en suspensión del dominio. Contacto: `abusereport@digitalplat.org`.
5. **Let's Encrypt**: Debería funcionar con la mayoría de extensiones, pero `.us.kG` y `.xx.kG` pueden tener restricciones de rate-limiting.

### Alternativas gratuitas

Si FreeDomain no funciona para tu caso:
- **Duck DNS**: `*.duckdns.org` (con API, recomendado para servers domésticos).
- **No-IP**: `*.ddns.net`, `*.hopto.org` (3 dominios gratis, renovación mensual).
- **EU.org**: Dominios gratuitos `.eu.org` (proceso de verificación manual).

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| DNS no resuelve | Espera 1-48h o verifica nameservers en el dashboard de FreeDomain |
| CORS error en navegador | Añade el dominio a `CORS_ALLOW_ORIGINS` en backend `.env` |
| SSL no se genera | Verifica que el dominio resuelva a la IP pública del servidor y que los puertos 80/443 estén abiertos |
| Caddy no arranca | `docker compose logs caddy` — error común: puerto 80/443 ya en uso |
| Dominio suspendido | Contacta a `abusereport@digitalplat.org` |

---

## Referencias

- [FreeDomain GitHub](https://github.com/DigitalPlatDev/FreeDomain)
- [FreeDomain Dashboard](https://dash.domain.digitalplat.org/)
- [Caddy Docker Docs](https://caddyserver.com/docs/running#docker)
