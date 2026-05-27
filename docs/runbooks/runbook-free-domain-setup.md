# Runbook: Configuración de dominio gratuito con FreeDomain

**Propósito**: Desplegar viru-tracker con un dominio personalizado gratuito usando [DigitalPlat FreeDomain](https://github.com/DigitalPlatDev/FreeDomain).

**Estado**: vivo
**Fuente de verdad**: sí

---

## Resumen

FreeDomain ofrece dominios gratuitos bajo extensiones como `.DPDNS.ORG`, `.US.KG`, `.QZZ.IO`, `.XX.KG` y `.QD.JE`. Estos dominios pueden apuntarse a tu servidor usando un proveedor DNS externo (Cloudflare, FreeDNS, etc.).

viru-tracker soporta dos modos de despliegue con dominio personalizado:

| Modo | Cuándo usarlo | Proxy/Túnel |
|------|---------------|-------------|
| **Cloudflare Tunnel** (laptop) | IP dinámica, sin router/puertos abiertos, portátil | `cloudflared` |
| **Caddy + Docker** (servidor) | Servidor fijo con IP pública y puertos abiertos | `Caddy` |

Ambos modos:
- Proveen HTTPS automático.
- Enrutan `/api/*` → backend (8000) y `/*` → frontend (3000).
- Son soportados por el backend con CORS dinámico vía `DOMAIN`.

---

## Paso 1: Registrar un dominio en FreeDomain

1. Ve al dashboard: [https://dash.domain.digitalplat.org/](https://dash.domain.digitalplat.org/)
2. Busca un nombre disponible para tu tracker (ej: `virutracker`, `viru-flight`, `tracker-viru`).
3. Elige una extensión disponible (`.dpdns.org`, `.us.kg`, `.qzz.io`, `.xx.kG`, `.qd.je`).
4. Regístrate y completa el registro. **No hay API programática**: el registro es manual desde el dashboard.
5. Anota tu dominio completo (ej: `virutracker.dpdns.org`).

---

## Paso 2: Elegir modo de despliegue

### 🌩️ Modo A: Cloudflare Tunnel (recomendado para laptop / IP dinámica)

Ideal si despliegas desde tu portátil con IP cambiante, sin acceso al router o detrás de CGNAT.

**Cómo funciona**: `cloudflared` crea un túnel outbound persistente a Cloudflare. Cloudflare enruta `viruair.dpdns.org` a través de ese túnel hasta `localhost:3000` y `localhost:8000`.

**Ventajas**:
- No necesitas abrir puertos en el router.
- No necesitas IP pública fija.
- HTTPS automático gestionado por Cloudflare.
- Funciona detrás de cualquier NAT/CGNAT.

#### 2A.1 Delegar DNS a Cloudflare

1. Crea una cuenta gratuita en [Cloudflare](https://cloudflare.com).
2. Añade tu dominio FreeDomain como sitio (`viruair.dpdns.org`).
3. Cloudflare te dará dos nameservers (ej: `alice.ns.cloudflare.com`, `bob.ns.cloudflare.com`).
4. Ve al dashboard de FreeDomain y configura los nameservers de tu dominio para que apunten a los de Cloudflare.
5. Espera a que la delegación se propague (puede tardar minutos u horas).

#### 2A.2 Instalar y configurar cloudflared

```powershell
# Desde la raíz del repo:
.
scripts\setup-cloudflared.ps1
```

Este script:
1. Instala `cloudflared` (vía winget o descarga directa).
2. Abre el navegador para autenticarte con Cloudflare.
3. Crea el túnel `viru-tracker`.
4. Configura el DNS (CNAME `viruair.dpdns.org` → `<tunnel-id>.cfargotunnel.com`).
5. Escribe `infra/cloudflared-config.yml` con los IDs reales.

#### 2A.3 Usar desde VIRU_PANEL.bat

```
VIRU_PANEL.bat
  Opción 1: Iniciar VIRU (foreground)
  Opción A: CF TUNNEL START  →  activa el túnel
  Opción B: CF TUNNEL STATUS →  verifica conexión
  Opción C: CF TUNNEL STOP   →  detiene el túnel
  Opción D: Ver logs CF tunnel
```

Una vez iniciado, abre `https://viruair.dpdns.org`.

#### 2A.4 Manual (sin VIRU_PANEL)

```powershell
# Terminal 1: Iniciar VIRU
.\iniciar_viru.ps1 -Foreground

# Terminal 2: Iniciar túnel
cloudflared tunnel --config infra/cloudflared-config.yml run
```

---

### 🐳 Modo B: Caddy + Docker (servidor con IP fija)

Ideal para despliegue en VPS o servidor dedicado con IP pública fija.

#### 2B.1 Delegar DNS y crear registros

1. Añade tu dominio FreeDomain en Cloudflare.
2. Configura los nameservers de FreeDomain para apuntar a Cloudflare.
3. En Cloudflare DNS, crea:
   - **Tipo A**: `@` → IP de tu servidor

> La propagación DNS puede tardar de minutos a 48 horas. Verifica con `nslookup tu-dominio.dpdns.org`.

---

## Paso 3 (Modo B): Configurar servidor con Caddy + Docker

Una vez que tengas el servidor con Docker y el repo clonado:

### 3.1. Crear archivo `.env` de producción

```bash
cp infra/.env.prod.example infra/.env
```

Editar `infra/.env`:

```env
DOMAIN=viruair.dpdns.org
NEXT_PUBLIC_API_URL=/api/v1
JWT_SECRET=<genera-un-valor-seguro>
APP_ENV=production
```

### 3.2. Desplegar con Caddy

```bash
cd infra
DOMAIN=viruair.dpdns.org docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Caddy:
- Escucha en puertos 80 y 443.
- Redirige tráfico a `viru-frontend:3000` (Next.js) y `viru-backend:8000` (API).
- Auto-provisiona certificado TLS con Let's Encrypt.

### 3.3. Verificar

```bash
# API health check
curl https://viruair.dpdns.org/api/v1/health

# Frontend
curl -I https://viruair.dpdns.org/
```

---

## Paso 4: Configurar CORS (solo si API está en dominio separado)

Con el túnel de Cloudflare o Caddy, frontend y API comparten dominio (`viruair.dpdns.org`), así que **no se necesita CORS adicional**.

Si usas dominios separados (ej: `api.viruair.dpdns.org`), configura:

```env
# backend/.env
DOMAIN=api.viruair.dpdns.org
CORS_ALLOW_ORIGINS=https://viruair.dpdns.org
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
| SSL no se genera (Caddy) | Verifica que el dominio resuelva a la IP pública y que los puertos 80/443 estén abiertos |
| Caddy no arranca | `docker compose logs caddy` — error común: puerto 80/443 ya en uso |
| cloudflared no instalado | Ejecuta `scripts/setup-cloudflared.ps1` (instala automáticamente) |
| Tunnel no conecta | Verifica logs con `VIRU_PANEL.bat` opción D; comprueba que VIRU esté corriendo (puertos 3000/8000) |
| `cloudflared tunnel login` falla | Asegúrate de haber añadido el dominio a tu cuenta de Cloudflare primero |
| Dominio suspendido | Contacta a `abusereport@digitalplat.org` |

---

## Referencias

- [FreeDomain GitHub](https://github.com/DigitalPlatDev/FreeDomain)
- [FreeDomain Dashboard](https://dash.domain.digitalplat.org/)
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [cloudflared Downloads](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
- [Caddy Docker Docs](https://caddyserver.com/docs/running#docker)
