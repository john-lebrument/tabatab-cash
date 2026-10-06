# TABaTAB Cash — version 2.6

Visionneuse et explorateur d’images Windows portable avec onglets, favoris, navigation plein écran et outils de retouche.

**[Télécharger la dernière version Windows](https://github.com/john-lebrument/tabatab-cash/releases/latest)** · **[Historique des versions et nouveautés](CHANGELOG.md)**

## Nouveautés 2.6

- **Glisser-déposer vers les favoris** : déplacer sans Ctrl, copier avec Ctrl. La destination est surlignée et les noms déjà présents ne sont pas écrasés.
- **Croix rouge à droite de chaque favori** : le retirer immédiatement, sans supprimer son dossier.
- **Tri de l’arborescence** : dossiers `_…` avant les noms numériques, avec `2` avant `10`.
- **Informations en haut à gauche du plein écran** : nom du fichier, compteur, images restantes et zoom visible en permanence.
- **Une photo ouverte depuis Windows rejoint une instance déjà lancée.** Pour ouvrir une deuxième instance indépendante, faire un clic du milieu sur l’icône dans la barre des tâches Windows. Un lancement sans photo ou avec `--new-instance` ouvre également une instance indépendante.

## Utilisation

Décompresser l’archive complète, puis lancer `TABaTAB Cash.exe` dans son dossier. Conserver le dossier `_internal` à côté de l’exécutable. Les préférences sont créées dans `data/settings.json` et restent locales.

- Onglets indépendants ; chemins cliquables, arborescence et miniatures.
- Favoris partagés et mémorisés : ajouter un dossier par clic droit, réorganiser par glisser-déposer, exporter/importer en JSON depuis le menu ⋯.
- Copier, couper, coller et déplacer entre dossiers, favoris et onglets ; Ctrl permet de copier pendant un glissement.
- Tri des miniatures par nom, date de modification, date de création, taille ou type, depuis la barre ou le clic droit.
- Retouche : rotations, recadrage, flou elliptique avec plusieurs zones, conversion JPEG/PNG et renommage groupé.
- Images et vidéos : vignettes vidéo lorsque le codec est disponible et lecture dans le lecteur Windows par défaut.
- Associations d’images depuis le bouton de l’application, avec validation finale dans les paramètres Windows.

## Raccourcis

| Touche | Action |
| --- | --- |
| Ctrl+T / Ctrl+W / Ctrl+Tab | Nouvel onglet / fermer / changer d’onglet |
| F2 | Renommer une image ou un dossier |
| F5 | Actualiser le dossier |
| Ctrl+C / Ctrl+X / Ctrl+V | Copier / couper / coller |
| Double-clic / Espace dans la grille | Ouvrir l’image en plein écran |
| Échap | Quitter le plein écran ou annuler l’outil actif |
| Flèches / molette en plein écran | Image précédente ou suivante |
| Début / Fin | Première / dernière image |
| + / − ou Ctrl+molette | Zoom avant / arrière |
| 0 / * | Ajuster à l’écran, affichage 100 % |
| M | Déplacer le plein écran sur l’écran suivant |
| B | Fenêtres flottantes des images sélectionnées |
| C / X | Recadrage |
| F | Flou |
| L / R | Rotation gauche / droite |
| Ctrl+S | Enregistrer une rotation |
| Suppr / Maj+Suppr | Corbeille / suppression définitive |
| Ctrl+Z | Restaurer la dernière image supprimée pendant la session |

Le zoom affiché est relatif à l’image ajustée à l’écran : 100 % au départ, 125 % après `+`, 80 % après `−` depuis le niveau initial.

## Historique

Les nouveautés de **2.6, 2.5, 2.4, 2.3, 2.2, 2.1, 2.0 et 1.9**, puis celles de **1.8 à 1.4** et les fonctionnalités documentées des premières versions figurent dans [CHANGELOG.md](CHANGELOG.md). Les attributions incertaines avant 1.4 sont signalées.

## Développement et compilation

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m src.main
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe build_portable.py
```

Incrémenter `src/version.py` et `resources/version_info.txt` avant chaque nouvelle compilation. Les anciens dossiers compilés dans le projet restent conservés.

La compilation habituelle dépose la version complète dans `OneDrive - unicaen.fr/Setup 1D/__Last version`, vérifie chaque fichier par SHA-256, puis retire les anciennes distributions de TABaTAB de ce dossier. `TABATAB_LATEST_DIRECTORY` permet de choisir un autre dossier. Pour compiler ailleurs sans ce dépôt :

```powershell
python build_portable.py --no-publish --clean-settings
```

## Publier une nouvelle version

Documenter les changements, tester et compiler, puis commiter et pousser les sources. Publier avec un fichier de notes propre à la nouvelle version :

```powershell
.venv/Scripts/python.exe publish_release.py --notes release/notes-v2.6.md
```

La release contient le ZIP Windows x64 complet et son empreinte SHA-256. Les préférences personnelles sont exclues de l’archive GitHub. Les sources, les notes de version, la release compilée et la copie OneDrive doivent être actualisées pour chaque nouvelle version.
