# Recette PPEF — parcours des agents et du superviseur

## État de livraison

La v0.5 est déployée. Le correctif v0.5.1 est préparé sur une branche distincte : cette fiche ne vaut pas confirmation de son déploiement. Aucun nouveau contrôle du navigateur Render, import hébergé ou changement de production n'est exécuté dans cette étape, pour laisser l'onglet disponible à l'autre conversation.

Les essais automatiques utilisent exclusivement des dossiers fictifs. Le classeur joint est un modèle sans dossier renseigné. La validation des nomenclatures et règles par les responsables métier reste à obtenir.

Contrôles locaux v0.5.1 réussis : **75 tests applicatifs**, parcours navigateur desktop/mobile incluant le refus d'une cellule sans en-tête et l'avertissement de résultat à confirmer, aucun message d'erreur JavaScript, restauration synthétique des **21 tables**. La lecture du classeur joint retrouve 76 colonnes, zéro dossier et zéro erreur. Preuves dans `evidence/v051/`. Les contrôles PostgreSQL sont exécutés séparément par GitHub Actions ; leur statut doit être lu sur la PR avant intégration.

## Parcours à faire accepter

| Étape | Responsable | Manipulation | Résultat attendu |
|---|---|---|---|
| Créer | Agent | Créer un RP fictif, saisir sa date et sa provenance | Brouillon identifié, aucun indicateur de dossier validé |
| Compléter | Agent | Ouvrir le registre, compléter les six sections | Les changements de section conservent la saisie ; les inconnus restent distincts de zéro |
| Rattacher | Agent | Associer personnes, infractions, décisions, peines et mesures | Refus des références absentes ; sommes séparées par nature et devise |
| Contrôler | Agent | Consulter Vérification, enregistrer avec un motif | Version et historique mis à jour ; les éléments à compléter sont affichés |
| Soumettre | Agent | Soumettre un dossier incomplet puis complété | Blocage expliqué, puis transmission au superviseur |
| Relire | Superviseur | Retourner avec motif ou valider | Historique conservé ; dossier validé non modifiable sans correction motivée |
| Analyser | Superviseur | Choisir période et observation, parcourir les six états | Flux et stock distincts ; seuls les dossiers validés alimentent les indicateurs |
| Exporter | Superviseur | Télécharger PDF, Excel et JSON | Filtres et méthode visibles ; données détaillées disponibles selon les droits |

## Import : trois situations de recette v0.5.1

### 1. Donnée sans en-tête

Un CSV comporte quatre en-têtes et cinq valeurs sur une ligne. La cinquième cellule apparaît sous `COL_5`, avec une erreur de correspondance. La confirmation reste désactivée. Ajouter un en-tête métier reconnu ou corriger le fichier ; ne pas supprimer une information utile pour contourner le contrôle.

### 2. Décision rédigée en texte libre

Une cellule « Contenu de la décision » indique « Annulation de la condamnation ». Le texte reste conservé intégralement. Le résultat est « À déterminer », sans compter une condamnation sur le seul mot rencontré. L'aperçu indique la ligne à relire. Après import du brouillon, ouvrir Décisions & peines, vérifier la pièce et sélectionner le résultat approprié ; « Autre » exige une précision. La soumission est bloquée tant que cette classification reste à déterminer.

Seuls les libellés exacts reconnus, tels que « Condamnation », « Relaxe » ou « Sursis à statuer », sont directement classés. Ce classement ne remplace pas la relecture de la pièce. Les dossiers déjà importés ne sont pas réinterprétés automatiquement : une correction exige un examen de la source et un motif.

### 3. Deux lignes strictement identiques

Le fichier comporte deux copies exactes du même dossier. Un seul brouillon et une seule fiche personne sont créés ; les deux numéros de ligne et l'original complet sont conservés. Des lignes différentes sur un même RP restent soumises aux règles de rapprochement et aux contrôles d'ambiguïté.

## Mise en production et passage de relais

1. Vérifier que les contrôles de la branche v0.5.1 sont réussis, y compris PostgreSQL 16/18 et navigateur.
2. Confirmer l'état actuel de la production et la fraîcheur de sa sauvegarde. La preuve de restauration v0.5 porte sur l'état antérieur au déploiement v0.5 ; elle ne couvre pas d'éventuels changements postérieurs.
3. Intégrer puis déployer le correctif depuis la conversation qui détient l'onglet Render. Ne pas lancer de restauration sur la source pour appliquer ce correctif, qui ne change pas le schéma.
4. Vérifier `/platform/config` en version `0.5.1`, `/ready` et l'accès authentifié. Effectuer la recette de fichiers fictifs dans un environnement de test autorisé.
5. Recueillir l'acceptation métier et les écarts observés avant d'annoncer une recette institutionnelle acquise.

La base isolée de sauvegarde v0.5 est à conserver selon la décision de rétention du propriétaire ; sa suppression et les frais Render ne sont pas modifiés dans cette étape.
