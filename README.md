# TABaTAB Cash — version 2.11

Visionneuse et explorateur d’images Windows portable avec onglets, favoris, navigation plein écran et outils de retouche.

**[Télécharger la dernière version Windows](https://github.com/john-lebrument/tabatab-cash/releases/latest)** · **[Historique des versions et nouveautés](CHANGELOG.md)**

## Nouveautés 2.11

- **Google Lens corrigé** : l’image est envoyée par le navigateur par défaut, qui conserve la session d’importation et affiche les résultats. L’application ne lui transmet plus une adresse de résultats issue d’une session Python distincte, cause du message « Recherche visuelle expirée » en 2.10.
- **Clic droit en plein écran ou en fenêtre flottante** : ouvre uniquement les outils. Utiliser le bouton « Images similaires (S) » pour rechercher sur Yandex.com et Google Lens. Dans les petites fenêtres flottantes, cette commande figure dans le menu contextuel. La touche **S** lance toujours directement la recherche ; **Ctrl+S** conserve sa fonction d’enregistrement.
- L’aperçu JPEG sans EXIF est transmis au navigateur par une page temporaire sur `127.0.0.1`, puis envoyé directement à Google Lens. Cette page ne donne accès à aucun dossier : elle contient uniquement l’aperçu de la recherche, reste disponible dix minutes et nécessite que TABaTAB reste ouvert jusqu’à l’envoi. Aucun fichier de transfert n’est écrit sur disque. Yandex conserve son envoi en arrière-plan.

## Nouveautés 2.10

- Le renommage par F2 reste lisible en plein écran et en fenêtre flottante, avec les thèmes clair et sombre. Le fond noir de l’image ne se propage plus aux boîtes de dialogue.
- **Images similaires (S)** : recherche de la photo courante sur Yandex.com et Google Lens, en ouvrant deux pages de résultats dans le navigateur par défaut. Disponible dans la grille, en plein écran et en fenêtre flottante. Ctrl+S conserve sa fonction d’enregistrement.
- En plein écran et en fenêtre flottante, un clic droit lance directement les deux recherches. Dans la grille, le menu contextuel propose « Images similaires sur Yandex et Google Lens (S) » pour l’image cliquée.
- Une copie JPEG de recherche, limitée à 1600 pixels de côté et sans métadonnées EXIF, est envoyée directement à chaque moteur lorsque la commande est utilisée. Le fichier original reste intact ; la recherche porte sur le fichier enregistré. Internet est nécessaire. Les envois sont indépendants et effectués en arrière-plan ; les erreurs réseau sont signalées. Le navigateur choisit l’ouverture en fenêtres ou en onglets selon ses réglages.

## Nouveautés 2.9

- Le menu contextuel des favoris propose maintenant l’ouverture du dossier dans l’Explorateur Windows.
- L’arborescence peint une bande de couleur vive et une teinte visible sur les dossiers colorés ; les couleurs proposées sont plus vives.
- Le plein écran décode HEIC/HEIF avec Pillow-Heif pour afficher correctement les pixels.
- Les résultats des doublons sont présentés dans une fenêtre française, avec aperçu des images et détails en lignes distinctes et en gras.
- Les boutons Vidéos et ZIP partagent le même style vert lorsqu’ils sont activés.
- Les commandes de tri sont renforcées visuellement.

## Nouveautés 2.8

- Clic droit sur un dossier de l’arborescence ou de la grille : ouvrir directement dans l’Explorateur Windows.
- Clic droit sur un dossier de l’arborescence : choisir une couleur prédéfinie ou personnalisée ; le choix est mémorisé.
- Après génération d’une vignette vidéo, le lecteur multimédia libère explicitement sa source afin de faciliter la suppression du fichier sous Windows.
- Les images HEIC et HEIF peuvent être affichées ; le support repose sur Pillow-Heif inclus dans la version portable.
- Les boutons latéraux 4 et 5 de la souris parcourent l’historique précédent/suivant dans l’arborescence et la grille.
- La fenêtre des doublons affiche les groupes avec les fichiers conservés et à supprimer, leur taille, leur date de modification et leur chemin. Le calcul et le choix des fichiers conservés sont inchangés.
- Le double-clic sur une archive ZIP ouvre son application Windows par défaut.

## Nouveautés 2.7

- **Miroir horizontal (H)** : inverse la gauche et la droite des images sélectionnées depuis la grille ou le menu de rotation. En plein écran, H et le bouton Miroir prévisualisent le résultat ; Ctrl+S permet de sauvegarder ou de créer une copie. Le miroir reste compatible avec les rotations, le recadrage et le floutage.
- **Début / Fin dans les miniatures** : rejoint la première ou la dernière image et fait défiler la grille jusqu’à elle.
- **Actualisation automatique** : surveillance du dossier, relecture au retour sur un onglet ou dans la fenêtre. Les nouveaux fichiers sont triés selon le réglage courant, avec conservation de la sélection et de la position de défilement. Les miniatures modifiées sont invalidées. F5 reste disponible.
- **Bouton ZIP** : affiche ou masque les archives ZIP, avec choix mémorisé. Double-cliquer ouvre l’archive avec Windows ; les ZIP ne font pas partie du diaporama.
- **Doublons du dossier affiché** : recherche en arrière-plan, annulable, de tous les fichiers ordinaires de contenu identique par SHA-256, indépendamment de leur nom et de leur extension. Les sous-dossiers et les liens sont exclus. La liste indique les fichiers conservés et les copies à supprimer. Le premier nom par ordre alphabétique est conservé ; les autres peuvent être envoyés à la corbeille avec le bouton Supprimer les doublons. Les empreintes sont revérifiées avant suppression et les fichiers sont conservés si la corbeille est indisponible.
- **Glisser-déposer renforcé** : suppression du transfert de secours utilisant une ancienne destination survolée ; dépôt dans une zone vide de la barre d’onglets refusé. Les transferts depuis la grille vers un onglet sont différés jusqu’à la fin du glisser-déposer Windows. Cette correction retire des comportements ambigus ; elle ne prétend pas établir la cause de l’incident observé en 2.6.


## Utilisation

Décompresser l’archive complète, puis lancer `TABaTAB Cash.exe` dans son dossier. Conserver le dossier `_internal` à côté de l’exécutable. Les préférences sont créées dans `data/settings.json` et restent locales.

- Onglets indépendants ; chemins cliquables, arborescence et miniatures.
- Favoris partagés et mémorisés : ajouter un dossier par clic droit, réorganiser par glisser-déposer, exporter/importer en JSON depuis le menu ⋯.
- Copier, couper, coller et déplacer entre dossiers, favoris et onglets ; Ctrl permet de copier pendant un glissement.
- Tri des miniatures par nom, date de modification, date de création, taille ou type, depuis la barre ou le clic droit.
- Retouche : rotations, recadrage, flou elliptique avec plusieurs zones, conversion JPEG/PNG et renommage groupé.
- Images et vidéos : vignettes vidéo lorsque le codec est disponible et lecture dans le lecteur Windows par défaut.
- Images HEIC/HEIF prises en charge dans la visionneuse.
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
| H | Miroir horizontal gauche-droite |
| S | Rechercher l’image sur Yandex.com et Google Lens |
| Clic droit dans la visionneuse | Ouvrir les outils, dont « Images similaires (S) » |
| Ctrl+S | Enregistrer une rotation |
| Suppr / Maj+Suppr | Corbeille / suppression définitive |
| Ctrl+Z | Restaurer la dernière image supprimée pendant la session |

Le zoom affiché est relatif à l’image ajustée à l’écran : 100 % au départ, 125 % après `+`, 80 % après `−` depuis le niveau initial.

## Historique

Les nouveautés de **2.11, 2.10, 2.9, 2.8, 2.7, 2.6, 2.5, 2.4, 2.3, 2.2, 2.1, 2.0 et 1.9**, puis celles de **1.8 à 1.4** et les fonctionnalités documentées des premières versions figurent dans [CHANGELOG.md](CHANGELOG.md). Les attributions incertaines avant 1.4 sont signalées.

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
