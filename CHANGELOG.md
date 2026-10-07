# Historique des versions

## 2.7

- **Miroir horizontal (H)** : inverse la gauche et la droite des images sélectionnées depuis la grille ou le menu de rotation. En plein écran, H et le bouton Miroir prévisualisent le résultat ; Ctrl+S permet de sauvegarder ou de créer une copie. Le miroir reste compatible avec les rotations, le recadrage et le floutage.
- **Début / Fin dans les miniatures** : rejoint la première ou la dernière image et fait défiler la grille jusqu’à elle.
- **Actualisation automatique** : surveillance du dossier, relecture au retour sur un onglet ou dans la fenêtre. Les nouveaux fichiers sont triés selon le réglage courant, avec conservation de la sélection et de la position de défilement. Les miniatures modifiées sont invalidées. F5 reste disponible.
- **Bouton ZIP** : affiche ou masque les archives ZIP, avec choix mémorisé. Double-cliquer ouvre l’archive avec Windows ; les ZIP ne font pas partie du diaporama.
- **Doublons du dossier affiché** : recherche en arrière-plan, annulable, de tous les fichiers ordinaires de contenu identique par SHA-256, indépendamment de leur nom et de leur extension. Les sous-dossiers et les liens sont exclus. La liste indique les fichiers conservés et les copies à supprimer. Le premier nom par ordre alphabétique est conservé ; les autres peuvent être envoyés à la corbeille avec le bouton Supprimer les doublons. Les empreintes sont revérifiées avant suppression et les fichiers sont conservés si la corbeille est indisponible.
- **Glisser-déposer renforcé** : suppression du transfert de secours utilisant une ancienne destination survolée ; dépôt dans une zone vide de la barre d’onglets refusé. Les transferts depuis la grille vers un onglet sont différés jusqu’à la fin du glisser-déposer Windows. Cette correction retire des comportements ambigus ; elle ne prétend pas établir la cause de l’incident observé en 2.6.

Distribution Windows portable complète et empreinte SHA-256 jointes. Les préférences personnelles sont exclues de l’archive GitHub.


## 2.6

- Glisser un fichier ou un dossier sur un favori pour le déplacer. Maintenir Ctrl au dépôt pour le copier. La destination est surlignée ; le dossier affiché reste inchangé. Fonctionne depuis TABaTAB et l’Explorateur Windows, sans écraser les fichiers existants.
- Croix rouge à droite de chaque favori : retrait immédiat, sans confirmation et sans supprimer le dossier. L’ordre des favoris et leur réorganisation par glisser-déposer sont conservés.
- Arborescence : les noms commençant par `_` passent avant les nombres, puis les autres noms. Le tri numérique reste naturel (`2` avant `10`).
- Plein écran : nom du fichier, compteur, nombre d’images restantes et pourcentage de zoom sont regroupés en haut à gauche et restent visibles avec la barre d’outils masquée.
- Ouvrir une photo depuis Windows réutilise une instance déjà ouverte. Un lancement sans photo, notamment par clic du milieu sur l’icône dans la barre des tâches Windows, ouvre une instance indépendante. `--new-instance` permet aussi de forcer une nouvelle instance. Si la fenêtre principale est fermée, une autre instance ouverte peut recevoir les prochaines photos.
- README actualisé et historique des versions connues reconstitué. Sources et archive Windows publiées sur GitHub ; nouvelle version copiée et vérifiée dans OneDrive avant suppression des anciennes distributions de TABaTAB dans le dossier de dernière version.

## 2.5

- Clic droit dans la grille : tri des miniatures par nom, date de modification, date de création, taille ou type, en ordre croissant ou décroissant. La barre de tri est synchronisée et le choix mémorisé.
- Menu ⋯ des favoris et clic droit : export/import JSON des chemins, de leur ordre et des raccourcis masqués. Import par fusion sans doublons ; les chemins temporairement inaccessibles sont conservés.
- Copier les images sélectionnées directement dans un dossier favori depuis le menu de l’image ou celui du favori. Coller dans un favori par clic droit ou Ctrl+V, avec prise en charge des fichiers copiés/coupés et des images brutes du presse-papiers. Aucun fichier existant n’est écrasé.


## 2.4

- F2 renomme les images dans la grille ou en plein écran et les dossiers dans la grille ou l'arborescence. L'extension de l'image est conservée. Les onglets et favoris suivent les dossiers renommés.
- Clic droit sur un dossier : « Ajouter aux favoris », dans la grille et l'arborescence. Les favoris sont mémorisés et partagés entre onglets.
- Le pourcentage de zoom reste visible en haut à droite du plein écran. L'image ajustée à l'écran correspond à 100 %. `+` affiche 125 %, `-` revient à 100 %. `0` ou `*` réinitialise à 100 % ; la molette actualise aussi l'indicateur.
- Publication des sources et des versions Windows compilées sur GitHub. Chaque release contient une archive portable sans préférences personnelles et son empreinte SHA-256.


## 2.3

Le dépôt est activé sur la surface des vignettes : glisser sur un dossier déplace les fichiers, maintenir Ctrl au dépôt les copie. Dans l'arborescence, un survol de 700 ms déplie le dossier ; maintenir la souris près du bord supérieur ou inférieur fait défiler la liste. Le dépôt ou la sortie de l'arborescence arrête ces actions. Ctrl+C, Ctrl+X et Ctrl+V restent disponibles.


## 2.2

Après avoir copié ou coupé des fichiers, sélectionner une vignette de dossier puis utiliser Ctrl+V les colle directement dans ce dossier. Son menu contextuel propose également « Coller dans ce dossier ». Le bouton « Associer toutes les images… » enregistre en une fois JPEG, JFIF, PNG, GIF, BMP, TIFF, WebP, AVIF et ICO, puis ouvre directement la page Windows de TABaTAB Cash pour la validation système obligatoire.


## 2.1

Le dépôt d'un fichier sur la vignette d'un dossier mémorise désormais la destination pendant tout le glissement, y compris lorsque Windows ne transmet pas l'événement final. L'outil de flou démarre sans zone présélectionnée, dessine des zones ovales et permet d'en cumuler plusieurs avant un seul enregistrement. Le bouton « Effacer la dernière zone » permet de corriger la sélection en cours.


## 2.0

La confirmation d'enregistrement d'une rotation reste lisible en plein écran. Les images sélectionnées peuvent être tournées ensemble à gauche ou à droite depuis leur menu contextuel. Un simple clic sélectionne une vidéo et seul le double-clic lance le lecteur externe. Le Ctrl+glisser interne dispose aussi d'un traitement de secours pour les versions de Windows/Qt qui n'envoient pas l'événement de dépôt à la grille.


## 1.9

Ctrl + glisser dans le même dossier crée une copie renommée. Les images et vidéos disposent de Copier, Couper (Ctrl+X), Coller, Renommer et Supprimer. La conversion reste réservée aux images. Le bouton Vidéos est vert quand il est activé. La navigation après rotation propose Enregistrer, Ignorer ou Annuler.

Sans corbeille disponible, les fichiers sont supprimés avec une sauvegarde temporaire permettant Ctrl+Z pendant la session. Cette sauvegarde est nettoyée à la fermeture.


## 1.8

- Bouton **Vidéos** dans la barre de tri : afficher ou masquer MP4, MKV, AVI, MOV, WebM et d'autres formats courants. Le choix est mémorisé. Une image de la vidéo sert de miniature lorsque le codec est pris en charge ; sinon une vignette « VIDÉO » reste disponible. Un clic ouvre le fichier dans le lecteur vidéo par défaut de Windows. Les vidéos ne sont pas incluses dans la navigation photo en plein écran.
- En plein écran, **M** passe à l'écran suivant, sans changer de photo. La commande **Écran suivant (M)** est aussi dans la barre d'outils affichée par clic droit. Le plein écran s'ouvre initialement sur l'écran de la fenêtre principale.
- Nom et version visibles en haut : **TABaTAB Cash — version 1.8**. L'exécutable s'appelle désormais **TABaTAB Cash.exe**.
- Pour utiliser l'application par défaut, associer les extensions d'image souhaitées au nouvel exécutable via Windows. L'image transmise par Windows est ouverte directement en plein écran, avec les autres photos du même répertoire pour la navigation. Échap revient à la grille sur cette image. Cette version ne modifie pas automatiquement vos associations de fichiers.
- Lanceur : **Lancer_TABaTAB_Cash.bat**. L'ancien lanceur reste compatible. Les préférences de la version précédente sont reprises.


## 1.7

- Clic droit → **Nouveau dossier…** dans la grille : créer un dossier dans le répertoire affiché. Dans l'arborescence, le nouveau dossier est créé à l'intérieur du dossier sur lequel on a fait un clic droit.
- Supprimer des dossiers par clic droit ou **Suppr**, dans la grille et dans l'arborescence : une confirmation indique que les dossiers et tout leur contenu seront envoyés à la **corbeille**. Les images seules conservent leur suppression sans confirmation.
- Déposer un fichier ou un dossier sur un autre onglet conserve **l'onglet d'origine**, pendant le survol et après le dépôt. Le surlignage indique la destination ; Ctrl permet toujours de copier.


## 1.6

- Déplacer les dossiers par glisser-déposer depuis la grille ou l'arborescence, vers un autre dossier ou onglet. Maintenir **Ctrl** pour les copier avec leur contenu. Les dépôts d'un dossier dans lui-même ou un de ses sous-dossiers sont refusés.
- **F2** ou clic droit → **Renommer le dossier** dans la grille. Les onglets ouverts et les favoris suivent le nouveau chemin lors d'un renommage ou déplacement.
- Les symboles **+** (copie) et **flèche** (déplacement) du curseur sont agrandis à 48 pixels.
- Réordonner les favoris par glisser-déposer dans la liste de gauche. L'ordre est conservé au redémarrage et partagé entre onglets.
- Le renommage groupé utilise au moins **trois chiffres** : `Image 001`, `Image 002`, `Image 003`… Une image seule conserve le nom saisi, sans numéro ajouté.
- Chaque dossier du chemin est cliquable. Le bouton **…** donne accès à tous les ancêtres lorsque le chemin est long ; **Chemin** ou **Alt+D** permet de saisir ou copier l'adresse complète, et **Échap** revient aux boutons.


## 1.5

- **F2** renomme une image en conservant son extension. Sur plusieurs images, saisir le nom de la première ; la numérotation utilise maintenant au moins trois chiffres (voir 1.6). L'ordre est celui affiché dans la grille. Un nom déjà occupé bloque le renommage sans écrasement.
- Clic droit → **Convertir → JPEG / PNG** : conserver les images initiales ou supprimer le format initial après conversion réussie. Fonctionne sur toute la sélection et préserve les autres fichiers déjà présents.
- Le dossier de destination est surligné en **bleu** pendant le glissement, dans la grille et sur toute la ligne de l'arborescence. Les onglets sont également surlignés.
- **Ctrl+glisser** copie, même dans le dossier courant ; relâcher Ctrl pendant le glissement revient au déplacement. Ctrl seul reste la touche de sélection multiple, comme dans Windows.
- Fenêtres **B** : uniquement au survol, croix rouge sur fond noir en haut à droite, commande de déplacement en haut et poignée de redimensionnement en bas à droite. Tout disparaît lorsque la souris quitte la fenêtre.


## 1.4

- Maintenir **Ctrl et glisser** une ou plusieurs images copie les fichiers, même dans le dossier courant. Sans Ctrl, le dépôt dans un autre dossier les déplace. Le dépôt fonctionne sur les dossiers de la grille, l'arborescence et les onglets.
- **F** en plein écran : sélectionner une zone avec les poignées, régler le flou de 0 à 100 % avec aperçu, puis enregistrer une copie ou remplacer l'original. **Échap** annule sans modifier le fichier.
- **Suppr** envoie les images à la corbeille sans confirmation. **Maj+Suppr** les efface définitivement. **Ctrl+Z** restaure la dernière image mise à la corbeille pendant la session, avec un message de restauration. Répéter Ctrl+Z pour restaurer plusieurs suppressions. La suppression définitive n'est pas annulable.
- Après suppression de la dernière image, le plein écran reste ouvert pour permettre Ctrl+Z. Échap revient à l'explorateur.
- **Début / Fin** : première / dernière image. La navigation s'arrête aux extrémités et affiche « Fin du répertoire » à la fin.
- À la sortie du plein écran, la dernière image affichée est sélectionnée et rendue visible dans l'explorateur.
- Clic droit sur un favori : le retirer de la liste (sans supprimer le dossier). Clic droit sur un dossier : nouvel onglet. Clic droit sur un onglet : fermer tous les onglets.
- **B** ouvre chaque image sélectionnée dans sa propre fenêtre, adaptée à l'écran, sans compteur ni ascenseur. Les commandes apparaissent uniquement au survol (voir 1.5). **Alt+glisser** déplace aussi la fenêtre ; ses bords permettent de la redimensionner. Le clic droit donne accès aux outils.


## 1.2–1.3 et premières versions

Les sources et tests anciens documentent les fonctionnalités suivantes, mais ne permettent pas d’attribuer précisément chaque changement à 1.2 ou 1.3 :

- Explorateur avec onglets indépendants, favoris et grille de miniatures réglable.
- Tri naturel par nom, date, taille ou type ; conservation de la sélection au changement de tri.
- Plein écran avec compteur jaune, navigation entre photos et barre d’outils sur clic droit.
- Recadrage avec poignées, proportions et dimensions ; enregistrement d’une copie ou remplacement de l’original.
- Copier/coller entre dossiers et onglets, et Ctrl+glisser pour copier.
- Fenêtres flottantes ouvertes avec B, sans bordure ; adaptation à la taille de l’image et à l’écran.

Historique reconstitué à partir du README et des tests conservés. Les versions anciennes ne sont pas présentées comme de nouvelles releases GitHub.
