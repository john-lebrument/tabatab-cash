# TABaTAB Cash

Sources de l'application Windows portable : `src/`. Environnement local : `.venv/Scripts/python.exe`.

## Instruction permanente de l'utilisateur

Chaque nouvelle modification du logiciel doit être publiée sur GitHub avec une nouvelle release et une version Windows compilée. La demande autorise les commits, les pushes et la publication des releases de ce logiciel.

Pour chaque nouvelle version :

1. Incrémenter `src/version.py` et `resources/version_info.txt`, sans remplacer une version existante.
2. Documenter le comportement dans `README.md` et `CHANGELOG.md`.
3. Vérifier les changements avec les tests pertinents, puis la suite complète.
4. Compiler avec `.venv/Scripts/python.exe build_portable.py --no-publish`. Les anciennes versions locales restent conservées.
5. Commiter les sources et pousser sur `origin`.
6. Exécuter `.venv/Scripts/python.exe publish_release.py --notes <fichier Markdown des notes de cette version>`.
7. Vérifier sur GitHub le commit, le tag, la release et ses deux fichiers (ZIP compilé et SHA-256). Fournir le lien de la release à l'utilisateur.

Ne jamais envoyer les préférences personnelles (`data/settings.json`), sauvegardes ou anciens exécutables dans Git. L'archive GitHub est créée sans préférences personnelles par `publish_release.py`. Si GitHub est déconnecté, terminer et vérifier le travail local puis demander uniquement la connexion nécessaire, sans annoncer une publication réussie.
