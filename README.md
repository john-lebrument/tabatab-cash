# TABaTAB Cash — version 1.8

TABaTAB Cash (anciennement XNViewTab) est une application Windows **100% portable** pour visualiser, organiser et retoucher vos images avec plusieurs onglets.

---

## Fonctionnalités Principales

### Nouveautés 1.8
- Bouton **Vidéos** dans la barre de tri : afficher ou masquer MP4, MKV, AVI, MOV, WebM et d'autres formats courants. Le choix est mémorisé. Une image de la vidéo sert de miniature lorsque le codec est pris en charge ; sinon une vignette « VIDÉO » reste disponible. Un clic ouvre le fichier dans le lecteur vidéo par défaut de Windows. Les vidéos ne sont pas incluses dans la navigation photo en plein écran.
- En plein écran, **M** passe à l'écran suivant, sans changer de photo. La commande **Écran suivant (M)** est aussi dans la barre d'outils affichée par clic droit. Le plein écran s'ouvre initialement sur l'écran de la fenêtre principale.
- Nom et version visibles en haut : **TABaTAB Cash — version 1.8**. L'exécutable s'appelle désormais **TABaTAB Cash.exe**.
- Pour utiliser l'application par défaut, associer les extensions d'image souhaitées au nouvel exécutable via Windows. L'image transmise par Windows est ouverte directement en plein écran, avec les autres photos du même répertoire pour la navigation. Échap revient à la grille sur cette image. Cette version ne modifie pas automatiquement vos associations de fichiers.
- Lanceur : **Lancer_TABaTAB_Cash.bat**. L'ancien lanceur reste compatible. Les préférences de la version précédente sont reprises.

### Nouveautés 1.7
- Clic droit → **Nouveau dossier…** dans la grille : créer un dossier dans le répertoire affiché. Dans l'arborescence, le nouveau dossier est créé à l'intérieur du dossier sur lequel on a fait un clic droit.
- Supprimer des dossiers par clic droit ou **Suppr**, dans la grille et dans l'arborescence : une confirmation indique que les dossiers et tout leur contenu seront envoyés à la **corbeille**. Les images seules conservent leur suppression sans confirmation.
- Déposer un fichier ou un dossier sur un autre onglet conserve **l'onglet d'origine**, pendant le survol et après le dépôt. Le surlignage indique la destination ; Ctrl permet toujours de copier.

### Nouveautés 1.6
- Déplacer les dossiers par glisser-déposer depuis la grille ou l'arborescence, vers un autre dossier ou onglet. Maintenir **Ctrl** pour les copier avec leur contenu. Les dépôts d'un dossier dans lui-même ou un de ses sous-dossiers sont refusés.
- **F2** ou clic droit → **Renommer le dossier** dans la grille. Les onglets ouverts et les favoris suivent le nouveau chemin lors d'un renommage ou déplacement.
- Les symboles **+** (copie) et **flèche** (déplacement) du curseur sont agrandis à 48 pixels.
- Réordonner les favoris par glisser-déposer dans la liste de gauche. L'ordre est conservé au redémarrage et partagé entre onglets.
- Le renommage groupé utilise au moins **trois chiffres** : `Image 001`, `Image 002`, `Image 003`… Une image seule conserve le nom saisi, sans numéro ajouté.
- Chaque dossier du chemin est cliquable. Le bouton **…** donne accès à tous les ancêtres lorsque le chemin est long ; **Chemin** ou **Alt+D** permet de saisir ou copier l'adresse complète, et **Échap** revient aux boutons.

### Nouveautés 1.5
- **F2** renomme une image en conservant son extension. Sur plusieurs images, saisir le nom de la première ; la numérotation utilise maintenant au moins trois chiffres (voir 1.6). L'ordre est celui affiché dans la grille. Un nom déjà occupé bloque le renommage sans écrasement.
- Clic droit → **Convertir → JPEG / PNG** : conserver les images initiales ou supprimer le format initial après conversion réussie. Fonctionne sur toute la sélection et préserve les autres fichiers déjà présents.
- Le dossier de destination est surligné en **bleu** pendant le glissement, dans la grille et sur toute la ligne de l'arborescence. Les onglets sont également surlignés.
- **Ctrl+glisser** copie, même dans le dossier courant ; relâcher Ctrl pendant le glissement revient au déplacement. Ctrl seul reste la touche de sélection multiple, comme dans Windows.
- Fenêtres **B** : uniquement au survol, croix rouge sur fond noir en haut à droite, commande de déplacement en haut et poignée de redimensionnement en bas à droite. Tout disparaît lorsque la souris quitte la fenêtre.

### Nouveautés 1.4
- Maintenir **Ctrl et glisser** une ou plusieurs images copie les fichiers, même dans le dossier courant. Sans Ctrl, le dépôt dans un autre dossier les déplace. Le dépôt fonctionne sur les dossiers de la grille, l'arborescence et les onglets.
- **F** en plein écran : sélectionner une zone avec les poignées, régler le flou de 0 à 100 % avec aperçu, puis enregistrer une copie ou remplacer l'original. **Échap** annule sans modifier le fichier.
- **Suppr** envoie les images à la corbeille sans confirmation. **Maj+Suppr** les efface définitivement. **Ctrl+Z** restaure la dernière image mise à la corbeille pendant la session, avec un message de restauration. Répéter Ctrl+Z pour restaurer plusieurs suppressions. La suppression définitive n'est pas annulable.
- Après suppression de la dernière image, le plein écran reste ouvert pour permettre Ctrl+Z. Échap revient à l'explorateur.
- **Début / Fin** : première / dernière image. La navigation s'arrête aux extrémités et affiche « Fin du répertoire » à la fin.
- À la sortie du plein écran, la dernière image affichée est sélectionnée et rendue visible dans l'explorateur.
- Clic droit sur un favori : le retirer de la liste (sans supprimer le dossier). Clic droit sur un dossier : nouvel onglet. Clic droit sur un onglet : fermer tous les onglets.
- **B** ouvre chaque image sélectionnée dans sa propre fenêtre, adaptée à l'écran, sans compteur ni ascenseur. Les commandes apparaissent uniquement au survol (voir 1.5). **Alt+glisser** déplace aussi la fenêtre ; ses bords permettent de la redimensionner. Le clic droit donne accès aux outils.

### 📑 Gestion des Onglets (Style Windows 11)
- **Onglets indépendants** : Chaque onglet conserve son propre dossier, son arborescence et sa grille d'images.
- **Nouvel onglet** : Cliquez sur le bouton `+` ou utilisez le raccourci `Ctrl + T`.
- **Fermer un onglet** : Cliquez sur la croix de l'onglet ou utilisez `Ctrl + W`.
- **Basculer d'onglet** : `Ctrl + Tab` ou clic direct.
- **Glisser-Déposer inter-onglets (Drag & Drop)** :
  - Sélectionnez une ou plusieurs images dans un onglet.
  - Glissez-les sur l'en-tête d'un autre onglet pour les **déplacer** (ou maintenez la touche `Ctrl` pour les **copier**).
  - Au survol et après le dépôt sur un autre onglet, l'onglet d'origine reste actif. Le surlignage indique la destination.
  - Compatible avec le glisser-déposer depuis ou vers l'Explorateur Windows.

### 🖼️ Visionneuse Plein Écran Sans Bord
- **Double-clic** ou touche **Espace** sur n'importe quelle vignette pour ouvrir instantanément l'image en plein écran immersif sans bordure.
- **Sortie du plein écran** : Touche `Échap` ou double-clic.
- **Navigation séquentielle** :
  - Flèche `Gauche` / `Retour arrière` / `Page Précédente` : Image précédente.
  - Flèche `Droite` / `Espace` / `Page Suivante` : Image suivante.

### 🔍 Zoom Réactif aux Touches `+` et `-`
- Touche `+` (ou pavé numérique `+`) : Zoom avant.
- Touche `-` (ou pavé numérique `-`) : Zoom arrière.
- Molette de la souris : Zoom avant / arrière fluide centré sur le curseur.
- Touche `0` ou `*` : Réinitialiser le zoom (ajuster à l'écran).
- Clic gauche enfoncé glissé : Déplacement panoramique (*Pan*) dans l'image zoomée.

### ✂️ Recadrage Ultra-Facile en Plein Écran
- Appuyez sur la touche `C` ou cliquez sur le bouton `✂ Recadrer` de la barre d'outils flottante.
- Un rectangle interactif de recadrage apparaît avec 8 poignées de redimensionnement et une grille des tiers.
- Affiche en temps réel la résolution de la découpe en pixels.
- Appuyez sur `Entrée` ou cliquez sur `✔ Valider Recadrage` :
  - Choix instantané : **"Enregistrer une copie"** (ajoute `_crop` au nom) ou **"Écraser l'original"**.
- Appuyez sur `Échap` pour annuler le recadrage à tout moment.

### 🚀 Application 100% Portable
- Aucun installateur requis, aucun droit administrateur nécessaire.
- Les associations Windows sont enregistrées uniquement via le bouton « Visionneuse par défaut… ».
- Les préférences et derniers onglets ouverts sont sauvegardés localement dans le sous-dossier `./data/settings.json`.

---

## Raccourcis Clavier Rapides

| Raccourci | Action |
| :--- | :--- |
| `Ctrl + T` | Ouvrir un nouvel onglet |
| `Ctrl + W` | Fermer l'onglet actif |
| `Ctrl + Tab` | Basculer vers l'onglet suivant |
| `F5` | Actualiser le dossier courant |
| `Double-clic` / `Espace` | Ouvrir l'image en plein écran sans bord |
| `Échap` | Quitter le plein écran / Annuler le recadrage |
| `+` / `-` | Zoom avant / Zoom arrière |
| `0` / `*` | Réinitialiser le zoom (adapter à l'écran) |
| `C` / `R` | Activer / Désactiver l'outil de recadrage |
| `Entrée` | Valider le recadrage |
| `Suppr` | Supprimer l'image sélectionnée |

---

## Exécution & Compilation

### Lancer depuis les sources
```powershell
python src/main.py
```

### Compiler en version portable autonome (.exe)
```powershell
python build_portable.py
```
La compilation crée un nouveau dossier `TABaTAB_Cash_Portable_v<version>` contenant `TABaTAB Cash.exe`, sans remplacer les versions précédentes.

## Version 1.9

Ctrl + glisser dans le même dossier crée une copie renommée. Les images et vidéos disposent de Copier, Couper (Ctrl+X), Coller, Renommer et Supprimer. La conversion reste réservée aux images. Le bouton Vidéos est vert quand il est activé. La navigation après rotation propose Enregistrer, Ignorer ou Annuler.

Sans corbeille disponible, les fichiers sont supprimés avec une sauvegarde temporaire permettant Ctrl+Z pendant la session. Cette sauvegarde est nettoyée à la fermeture.

## Version 2.0

La confirmation d'enregistrement d'une rotation reste lisible en plein écran. Les images sélectionnées peuvent être tournées ensemble à gauche ou à droite depuis leur menu contextuel. Un simple clic sélectionne une vidéo et seul le double-clic lance le lecteur externe. Le Ctrl+glisser interne dispose aussi d'un traitement de secours pour les versions de Windows/Qt qui n'envoient pas l'événement de dépôt à la grille.

## Version 2.1

Le dépôt d'un fichier sur la vignette d'un dossier mémorise désormais la destination pendant tout le glissement, y compris lorsque Windows ne transmet pas l'événement final. L'outil de flou démarre sans zone présélectionnée, dessine des zones ovales et permet d'en cumuler plusieurs avant un seul enregistrement. Le bouton « Effacer la dernière zone » permet de corriger la sélection en cours.

## Version 2.3

Le dépôt est activé sur la surface des vignettes : glisser sur un dossier déplace les fichiers, maintenir Ctrl au dépôt les copie. Dans l'arborescence, un survol de 700 ms déplie le dossier ; maintenir la souris près du bord supérieur ou inférieur fait défiler la liste. Le dépôt ou la sortie de l'arborescence arrête ces actions. Ctrl+C, Ctrl+X et Ctrl+V restent disponibles.

## Version 2.2

Après avoir copié ou coupé des fichiers, sélectionner une vignette de dossier puis utiliser Ctrl+V les colle directement dans ce dossier. Son menu contextuel propose également « Coller dans ce dossier ». Le bouton « Associer toutes les images… » enregistre en une fois JPEG, JFIF, PNG, GIF, BMP, TIFF, WebP, AVIF et ICO, puis ouvre directement la page Windows de TABaTAB Cash pour la validation système obligatoire.

Avant une nouvelle compilation, incrémenter src/version.py et resources/version_info.txt. build_portable.py conserve les anciennes versions locales, actualise les lanceurs et publie le dossier portable complet dans %USERPROFILE%\OneDrive - unicaen.fr\Setup 1D\__Last version. Après vérification SHA-256, seules les anciennes distributions de cette application dans ce dernier dossier sont supprimées.

## Version 2.4

F2 renomme les images dans la grille et en plein écran, et les dossiers dans la grille et l'arborescence. Les extensions sont conservées, les collisions refusées, les onglets et favoris suivent les dossiers renommés.

Clic droit sur un dossier dans la grille ou l'arborescence → Ajouter aux favoris. Les favoris sont conservés au redémarrage et partagés entre onglets.

Le zoom reste visible en haut à droite du plein écran, même avec la barre d'outils masquée. L'image ajustée à l'écran vaut 100 %, + donne 125 %, - revient à 100 %, et 0 ou * réinitialise à 100 %. Ce pourcentage est relatif à l'ajustement à l'écran.

### Publier une nouvelle version sur GitHub

Incrémenter les deux fichiers de version, tester, compiler, puis commiter et pousser les sources. Publier avec :

```powershell
.venv/Scripts/python.exe publish_release.py --notes CHANGELOG.md
```

La release contient le ZIP Windows x64 complet et son empreinte SHA-256. Les préférences personnelles sont exclues de l'archive. Pour compiler ailleurs sans copie vers le dossier OneDrive local :

```powershell
python build_portable.py --no-publish --clean-settings
```

## Version 2.5

- Clic droit dans la grille, sur une miniature ou dans un espace vide → **Trier les miniatures** : nom, date de modification, date de création, taille ou type, avec ordre croissant/décroissant. Le menu et la barre de tri restent synchronisés ; le choix est mémorisé.
- Bouton **⋯** à côté de FAVORIS, ou clic droit dans la liste → **Exporter les favoris… / Importer les favoris…**. Le fichier JSON contient les chemins, leur ordre et les raccourcis masqués, sans copier le contenu des dossiers. L’import ajoute les favoris sans doublons et conserve les chemins temporairement inaccessibles.
- Clic droit sur une image → **Copier dans un dossier favori**. Clic droit sur un favori → **Copier les images sélectionnées dans ce dossier** ou **Coller dans ce dossier (Ctrl+V)**. Ctrl+V fonctionne aussi lorsque la liste des favoris a le focus. Copier/couper depuis TABaTAB ou l’Explorateur Windows puis coller respecte les collisions sans écraser les fichiers. Une image brute du presse-papiers est enregistrée en PNG avec un nom unique.
