# Module assistant v2 : moteur d'orchestration multi-tool-call.
#
# Branche sur app.main : voir /api/assistantv2/chat et /api/assistantv2/tools.
# Le module `assistant` (v1) reste actif en parallele, inchange, sur
# /api/assistant/*.
#
# L'enregistrement des outils (registry.register) se declenche a l'import de
# app.modules.assistantv2.tools : voir ce sous-package pour la liste des
# modules metier charges.
