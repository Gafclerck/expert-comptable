# Sous-package du canal Telegram pour l'assistant v2 (long polling, zero
# dependance ajoutee - httpx seulement).
#
# Phase 0 (ce commit) : config TELEGRAM_* + diagnostic get_me + garde-fou du
# worker (sortie explicite sans token valide). Rien n'est branche sur
# app.main : le module ne se charge qu'a la main via
# `python -m app.modules.assistantv2.telegram`.
#
# Le worker complet (get_updates + chat, journal d'idempotence, endpoint de
# liaison) arrive en Phase 1 -- voir docs/TELEGRAM_INTEGRATION.md.