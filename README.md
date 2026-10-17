# Bons Plans Instant Gaming → Discord

Ce bot publie depuis **une exécution Apify existante** : il ne déclenche pas de nouvelle recherche payante.

## Installation
1. Ajoutez les fichiers au dépôt GitHub (y compris `.github/workflows/bons-plans.yml`).
2. Dans GitHub → Settings → Secrets and variables → Actions → New repository secret, ajoutez :
   - `APIFY_TOKEN` : votre clé API Apify (à ne jamais publier).
   - `APIFY_RUN_ID` : identifiant de la **run** réussie (dans l'URL de la page Apify : `/runs/IDENTIFIANT`).
   - `DISCORD_WEBHOOK_URL` : URL de votre webhook Discord (à ne jamais publier).
3. Dans GitHub → Actions → Bons Plans Instant Gaming → Run workflow, lancez le test.
4. Le bot publie au maximum 3 jeux (pas les DLC) à au moins 50 % de remise, disponibles et non déjà envoyés.

## Important
- Le workflow n'a **pas** de planification automatique activée : l'ancienne exécution Apify ne peut pas donner de nouvelles offres. Il faudra plus tard configurer une source actualisée et son budget.
- Les offres envoyées sont mémorisées dans `sent_offers.json`, commité automatiquement dans le dépôt.
- Si l'action reçoit un 403 sur le push, vérifiez Settings → Actions → General → Workflow permissions → Read and write permissions.
- Ne mettez jamais de token ni l'URL de webhook dans les fichiers du dépôt.
- Un lien vers Instant Gaming doit être vérifié à l'achat ; les prix peuvent évoluer.
