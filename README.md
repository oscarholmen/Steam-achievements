# Steam Achievement Monitor
 
A microservices system that monitors Steam users' achievements and sends webhook notifications when new achievements are unlocked.
 
> **Note:** Many technologies in this project were new to me, including Docker, PostgreSQL, and webhooks. I chose Python as the backend language since it allowed me to focus on learning these new concepts without also learning a new programming language at the same time.
 
---
 
## Architecture Overview
 
The system consists of three main components running as separate services:
 
```
Steam API
    ↓
Poller Service        ← fetches achievements every 15 minutes
    ↓
PostgreSQL DB         ← stores games and achievements
    ↓
Webhook Notification  ← sends Slack message on new unlock
```
 
**Database tables:**
- `games` – all games owned by the Steam user
- `achievements` – all achievements per game, with unlock status and timestamp
**Dashboard:** Power BI connects directly to PostgreSQL and visualizes the statistics.
 
---
 
## Technology Decisions
 
### Why Python instead of TypeScript
 
The case listed TypeScript as the preferred language. With more time, this would be the right choice – but this project introduced several technologies that were new to me simultaneously: Docker, PostgreSQL, and webhooks. Using a familiar language (Python) allowed me to focus on understanding these concepts rather than also learning a new language.
 
I would rather submit code I fully understand and can defend than code written in an unfamiliar language. The architecture is intentionally modular, so individual services could be rewritten in TypeScript without affecting the rest of the system.
 
### Why Power BI for the dashboard
 
Power BI connects natively to PostgreSQL and provides production-grade visualizations with minimal code. Since the case emphasizes backend quality as the primary evaluation criteria, this was a pragmatic choice that saved time for the more complex backend work.
 
---
 
## Project Structure
 
```
steam-achievements/
├── docker-compose.yml
├── .env.example
├── services/
│   └── poller/
│       ├── main.py          ← entry point, runs in Docker
│       ├── steam_client.py  ← Steam API wrapper
│       ├── database.py      ← PostgreSQL setup and models
│       ├── poller.py        ← achievement diff logic
│       └── webhooks.py      ← Slack webhook notifications
└── dashboard/
    └── steam_achievements.pbix
```
 
### File descriptions
 
**`main.py`**
Entry point for the Docker container. Starts a scheduler that polls Steam every 15 minutes and triggers webhook notifications when new achievements are detected. No logic is defined here – it imports from the other files and wires them together.
 
**`steam_client.py`**
Async wrapper around the Steam Web API (`https://api.steampowered.com`). Handles fetching owned games and achievements per game, with error handling for private profiles and games without achievements.
 
**`database.py`**
Sets up the async PostgreSQL connection using SQLAlchemy. Defines the `games` and `achievements` tables and creates them on startup if they don't exist.
 
**`poller.py`**
Implements the core polling logic. Fetches achievements from Steam, compares them against what is stored in the database, updates the database if there are differences, and calls the webhook for any newly unlocked achievements.
 
**`webhooks.py`**
Sends a formatted message to a Slack channel whenever a new achievement is unlocked.
 
---
 
## Setup Instructions
 
### Prerequisites
 
- Docker and Docker Compose installed
- A Steam API key – get one at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)
- Your Steam ID (64-bit format)
- A Slack webhook URL (optional – for notifications)
### 1. Clone the repository
 
```bash
git clone https://github.com/oscarholmen/Steam-achievements.git
cd Steam-achievements
```
 
### 2. Configure environment variables
 
```bash
cp .env.example .env
```
 
Edit `.env` and fill in your values:
 
```env
STEAM_API_KEY=your_steam_api_key
STEAM_ID=your_steam_id
POSTGRES_PASSWORD=your_password
POLL_INTERVAL_MINUTES=15
SLACK_WEBHOOK_URL=your_slack_webhook_url
```
 
### 3. Start the system
 
```bash
docker-compose up --build
```
 
This starts PostgreSQL and the poller service. The first poll runs immediately on startup.
 
---
 
## Docker Setup
 
| Service    | Description                        | Port  |
|------------|------------------------------------|-------|
| `postgres` | PostgreSQL database                | 5433  |
| `poller`   | Steam polling + webhook dispatcher | –     |
 
The poller waits for PostgreSQL to be healthy before starting, so no manual sequencing is needed.
 
---
 
## API Testing with Postman
 
Postman was used to explore the Steam API endpoints and identify which data was useful before implementing the integration.
 
**GetOwnedGames** – lists all games for a user:
![Using GetOwnedGames in Postman](getGames.png)
 
**GetPlayerAchievements** – lists achievements for a specific game:
![Using GetPlayerAchievements in Postman](getAchievements.png)
 
---
 
## Webhook Notifications
 
When a new achievement is unlocked, a message is automatically posted to a Slack channel via a configured incoming webhook.
 
![Slack notification example](slackNotifications.png)
 
---
 
## Dashboard
 
Statistics are visualized in Power BI, connected directly to the PostgreSQL database.
 
**Metrics displayed:**
- Total games with achievements
- Total achievements unlocked
- Average achievements per game
- Best streak of consecutive days with unlocks
- Achievements by weekday
- Cumulative achievements over time

