# Module assistant v3 : meme moteur que v2 (boucle multi-tool-call, plan
# persiste, confirmation deterministe), restructure autour d'un port
# FieldType pour que connecter un business ne touche plus jamais
# orchestrator.py / resolvers.py / parsing.py.
#
# Ni v1 (`assistant`) ni v2 (`assistantv2`) ne sont modifies ou supprimes.
# Ce module n'est volontairement PAS branche sur app.main tant qu'il n'est
# pas teste (voir la meme methode que pour v2).
#
# Voir /docs ou la conversation d'architecture pour le detail du port
# FieldType (resolve/fill/validate/coerce) et du manifeste BusinessModule
# (code, aliases, indice de contexte pour le system prompt).
