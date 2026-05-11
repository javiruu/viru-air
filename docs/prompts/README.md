# Prompts y Contexto IA

**Estado:** vivo  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** sí  
**Área:** contexto IA

## Resumen

Esta carpeta separa el material operativo de agentes del histórico de prompts sueltos.

## Regla principal

- `AGENTS.md` es el contrato operativo principal para agentes dentro de este repo.
- `docs/reference/codex-operating-contract.md` actúa como referencia persistente complementaria.
- `skills/viru-tracker-context/` contiene contexto reusable para reentrada.
- Los prompts antiguos o de una sesión concreta deben vivir en `legacy/`.

## Contenido actual

- `legacy/prompt-root-legacy.txt`: prompt antiguo movido desde la raíz.

## Qué no hacer

- No dupliques reglas activas de `AGENTS.md` aquí.
- No conviertas prompts viejos en fuente de verdad del proyecto.
- No guardes secretos ni datos reales de usuario.

## Relacionado

- [AGENTS.md](../../AGENTS.md)
- [Codex operating contract](../reference/codex-operating-contract.md)
- [Archive prompts](../archive/prompts/README.md)
