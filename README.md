# 🎮 CheckPrice — Bot Discord de Surveillance des Prix PS Store (PSPrices)

Bot Discord moderne développé en Python permettant de **surveiller et analyser les prix des jeux PlayStation** à partir du site [PSPrices](https://psprices.com/).

Le bot stocke toutes ses données **localement dans des fichiers JSON** (aucun système de base de données lourd tel que SQLite, MySQL ou PostgreSQL n'est requis), surveille les promotions, alerte un rôle Discord lors des baisses de prix et fournit une analyse quotidienne automatique à **08h00 (Europe/Paris)**.

---

## ✨ Fonctionnalités Principales

- 🔍 **Surveillance PSPrices propre et respectueuse** : Récupère les données publiques officielles (JSON-LD Schema.org `Product` et `VideoGame`) sans requêtes inutiles ni spamming.
- 💾 **Stockage 100% JSON local** :
  - `data/games.json` : Liste des jeux surveillés avec prix actuel, précédent, plus bas historique, réduction et date.
  - `data/price_history.json` : Historique complet avec détection de doublons (aucun ajout si le prix n'a pas changé).
- 🚨 **Détection intelligente de promotions** :
  - Alerte automatique quand `nouveau_prix < ancien_prix`.
  - **Ping automatique d'un rôle Discord dédié** uniquement lors d'une véritable nouvelle baisse.
  - Aucun ping intempestif au démarrage, en cas de prix stable ou lors d'une fin de promotion (hausse de prix).
- ⏰ **Analyse quotidienne automatique à 08h00** :
  - Gérée par `discord.ext.tasks` et `zoneinfo` (`Europe/Paris`).
  - Prise en compte native de l'heure d'été et de l'heure d'hiver, résistant aux redémarrages.
- ⚡ **Commandes Slash intuitives** :
  - Autocomplétion dynamique pour sélectionner les jeux facilement.
  - Possibilité de forcer l'analyse à tout moment via `/analyse`.
- 📊 **Analyse statistique** : Indication du prix plancher atteint, calcul du pourcentage de remise, historique des baisses.

---

## 📁 Architecture du Projet

```text
Checkprice/
│
├── main.py                     # Point d'entrée principal du bot Discord
│
├── commands/                   # Commandes Slash (Cogs discord.py)
│   ├── watch.py                # /watch : ajouter un jeu par URL
│   ├── unwatch.py              # /unwatch : retirer un jeu (avec autocomplétion)
│   ├── watchlist.py            # /watchlist : lister les jeux surveillés
│   ├── analyse.py              # /analyse : lancer l'analyse manuelle immédiate
│   └── prix.py                 # /prix : consulter le prix et l'analyse d'un jeu
│
├── services/                   # Logique métier et scraping
│   ├── psprices.py             # Parser PSPrices (Schema.org JSON-LD & OpenGraph)
│   ├── price_checker.py        # Moteur de comparaison et mise à jour des prix
│   └── analyzer.py             # Analyse statistique et tendances des prix
│
├── tasks/                      # Tâches planifiées
│   └── daily_analysis.py       # Tâche automatique à 08h00 (Europe/Paris)
│
├── utils/                      # Utilitaires
│   ├── json_manager.py         # Gestion atomique des fichiers JSON et historique
│   └── embeds.py               # Génération des embeds visuels Discord
│
├── data/                       # Stockage des données locales
│   ├── games.json              # Liste des jeux surveillés
│   └── price_history.json      # Historique des variations de prix
│
├── .env                        # Variables d'environnement secrètes (non versionné)
├── .env.example                # Modèle des variables d'environnement
├── .gitignore                  # Fichiers exclus de Git
├── requirements.txt            # Dépendances Python
└── README.md                   # Documentation complète
```

---

## 🛠️ Prérequis

- **Python 3.11+**
- Un compte Discord et une application créée sur le [Portail Développeur Discord](https://discord.com/developers/applications).

---

## 🚀 Installation et Configuration

### 1. Cloner ou ouvrir le projet

```bash
cd Checkprice
```

### 2. Créer un environnement virtuel (recommandé)

```bash
python -m venv .venv

# Sous Windows (PowerShell) :
.venv\Scripts\Activate.ps1

# Sous Linux / macOS :
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Copiez le fichier `.env.example` en `.env` :

```bash
copy .env.example .env     # Windows
# ou : cp .env.example .env # Linux / macOS
```

Éditez le fichier `.env` avec vos identifiants :

```env
# Token du bot Discord (Portail Développeur -> Bot -> Reset Token)
DISCORD_TOKEN=votre_token_secret_ici

# ID de votre serveur Discord (clic droit sur votre serveur -> Copier l'identifiant du serveur)
# Permet une synchronisation instantanée des Slash Commands
DISCORD_GUILD_ID=123456789012345678

# ID du salon Discord où envoyer le rapport de 08h00 et les alertes promos
DISCORD_CHANNEL_ID=123456789012345678

# ID du rôle Discord à ping lors d'une nouvelle promotion
DISCORD_PROMO_ROLE_ID=123456789012345678
```

> **Note :** Pour copier les identifiants sur Discord, activez le **Mode Développeur** dans *Paramètres Discord > Avancés > Mode Développeur*.

### 5. Permissions du Bot sur Discord

Dans le **Discord Developer Portal** :
1. Rendez-vous dans **OAuth2 > URL Generator**.
2. Cochez les scopes :
   - `bot`
   - `applications.commands`
3. Cochez les permissions du bot :
   - `Send Messages` (Envoyer des messages)
   - `Embed Links` (Intégrer des liens)
   - `Mention Everyone` (Mentionner des rôles)
   - `View Channels` (Voir les salons)
   - `Read Message History` (Voir l'historique des messages)
4. Invitez le bot sur votre serveur avec l'URL générée.

---

## 🎯 Commandes Slash Disponibles

| Commande | Description |
| :--- | :--- |
| `/watch <url>` | Ajoute un jeu PSPrices à la surveillance (extrait prix, plus bas, image, ID). |
| `/unwatch [jeu]` | Retire un jeu de la surveillance avec recherche automatique / autocomplétion. |
| `/watchlist` | Affiche l'ensemble des jeux surveillés avec prix actuels et prix record. |
| `/prix [jeu]` | Affiche la fiche complète et l'analyse détaillée d'un jeu surveillé ou via URL. |
| `/analyse` | Déclenche immédiatement l'analyse de tous les jeux, met à jour les données et alerte en cas de promotion. |

---

## 🌐 Déclenchement Externe via Cron / Webhook

Le bot supporte deux méthodes de déclenchement externe pour mettre à jour tous les prix de la liste :

### 1. Par requête HTTP (Webhook pour cron-job.org, EasyCron, etc.)
Lorsque le bot est lancé (`python main.py`), il démarre automatiquement un serveur web léger :
- **Endpoint** : `GET` ou `POST` sur `http://votre-ip-ou-domaine:8080/api/cron`
- **Sécurité (optionnelle)** : Ajoutez `CRON_SECRET=mon_token` dans votre `.env`. La requête doit inclure l'en-tête `Authorization: Bearer mon_token` ou le paramètre `?secret=mon_token`.
- **Réponse** :
  ```json
  {
    "status": "success",
    "message": "Analyse effectuée avec succès.",
    "total_games": 2,
    "promotions_detected": 1,
    "price_hikes": 0,
    "unchanged": 1
  }
  ```

### 2. Par script autonome (`cron_check.py`)
Si vous préférez exécuter un cron système (crontab Linux, GitHub Actions, etc.) sans maintenir le bot connecté en continu :
```bash
python cron_check.py
```
Ce script vérifie tous les jeux, met à jour les fichiers JSON locaux, et envoie directement les alertes et le rapport dans le salon Discord via l'API REST Discord.

---

## 🔄 Analyse Quotidienne et Détection de Promotion

### Règle de détection de promotion :
- Une promotion est détectée lorsque **`nouveau_prix < ancien_prix`**.
- Le bot envoie directement un embed d'alerte propre dans le salon (sans ping de rôle) :
  ```text
  🚨 NOUVELLE PROMO
  🎮 Uncharted: The Nathan Drake Collection
  💰 19,99 € → 5,99 €
  🔥 -70 %
  🏆 Plus bas historique : 5,99 €
  🔗 Voir sur PSPrices
  ```

### Cas sans alerte promo :
- Aucun changement de prix.
- Le jeu était déjà en promotion au même tarif.
- Fin de promotion (le prix passe de 5,99 € à 19,99 €) : l'historique est mis à jour, le rapport indique `🔺 Fin de promotion`.
- Au démarrage du bot ou lors d'un simple `/analyse` sans nouvelle baisse.

### Historique des prix (`data/price_history.json`) :
- Une nouvelle entrée est insérée **uniquement** si le prix varie (`19.99 € → 9.99 €`).
- Les prix identiques consécutifs (`19.99 € → 19.99 €`) ne sont **jamais** dupliqués.

---

## 🛡️ Respect du site PSPrices

Le bot respecte les bonnes pratiques de requêtage web :
- **Extraction par Schema.org JSON-LD** : PSPrices fournit des balises sémantiques officielles pour les moteurs de recherche. Le bot lit directement ces métadonnées structurées sans charger d'éléments inutiles.
- **Temporisation (Rate-Limiting)** : Une pause de 1,5 seconde est appliquée entre chaque jeu lors des analyses globales (`/analyse` ou 08h00) pour ne pas saturer le serveur.
- **Headers conformes** : En-têtes standards de navigateur moderne pour éviter les faux positifs et blocages.

---

## 💻 Démarrage du Bot

Pour lancer le bot :

```bash
python main.py
```

Vous devriez observer dans votre terminal :

```text
2026-10-03 14:00:00 [INFO] checkprice: Extension chargée : commands.watch
2026-10-03 14:00:00 [INFO] checkprice: Extension chargée : commands.unwatch
2026-10-03 14:00:00 [INFO] checkprice: Extension chargée : commands.watchlist
2026-10-03 14:00:00 [INFO] checkprice: Extension chargée : commands.prix
2026-10-03 14:00:00 [INFO] checkprice: Extension chargée : commands.analyse
2026-10-03 14:00:00 [INFO] checkprice: Extension chargée : tasks.daily_analysis
2026-10-03 14:00:01 [INFO] checkprice: Slash commands synchronisées instantanément pour le serveur.
==================================================
 Connecté en tant que : CheckPrice#1234 (ID: 987654321098765432)
 Heure Paris : 03/10/2026 14:00:01
 Jeux surveillés actuellement : 0
==================================================
```
