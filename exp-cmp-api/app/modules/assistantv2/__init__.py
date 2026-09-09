# Module assistant v2 : moteur d'orchestration multi-tool-call.
#
# NE PAS BRANCHER assistantv2_router sur app.main tant que la phase de test
# manuelle/automatisee n'est pas concluante. Le module `assistant` (v1) reste
# actif en parallele et n'est pas modifie.
#
# L'enregistrement des outils (registry.register) se declenche a l'import de
# app.modules.assistantv2.tools : voir ce sous-package pour la liste des
# modules metier charges.
