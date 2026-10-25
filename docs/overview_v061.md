# Vue d’ensemble 0.6.1

La vue d’ensemble propose explicitement « Tous les cabinets », une comparaison des cabinets et des raccourcis vers chacun. Les options de cabinets autorisés restent disponibles après sélection d’un seul cabinet. Les lignes sans affectation sont identifiées séparément. Les droits et les autres filtres continuent de s’appliquer au comparatif.

Le choix des indicateurs affichés est conservé dans la session du navigateur. Les 15 cartes proposées comprennent les nouveaux compteurs descriptifs de décisions, ancienneté depuis RP, absence de mouvement récent, retours pour correction et délai moyen. Un catalogue de 63 indicateurs reprend le document fourni ; les définitions nécessitant des données supplémentaires ou une règle de terminaison restent explicitement non calculables. Aucune date de clôture d’instruction n’est assimilée à une clôture judiciaire finale.

Chaque graphique propose histogramme groupé, barres horizontales, courbes ou tableau. L’anneau est réservé aux séries uniques ; il n’additionne pas des unités différentes. Les légendes, tableaux exacts et liens vers les dossiers restent accessibles. Une préférence générale permet de changer les graphiques ensemble.

Les bandeaux et libellés de démonstration sont retirés de l’interface, ainsi que les tirets cadratins des textes de présentation. La provenance des données et le statut de validation de la méthode restent dans les métadonnées. Les identifiants et contenus des dossiers ne sont pas réécrits. Les données absentes ne sont pas converties en zéros.

Les cartes, graphiques, formulaires et tableaux utilisent des tailles cohérentes et une disposition adaptée aux petits écrans. Les montants abrégés restent accompagnés d’une valeur exacte.

Validation : tests des cabinets et du catalogue côté serveur, parcours navigateur de sélection du cabinet puis retour à tous, choix des indicateurs et changement de représentation. Aucune migration ni réimportation des 1500 dossiers n’est nécessaire.
