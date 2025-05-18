# README.md

# Mulla Games

A collection of multiplayer and offline party games built with Flet.

## Games Included:

*   Bara Alsalfa (Online & Offline)
*   Bedoon Kalam (Online & Offline)
*   Heads Up (Offline Only)
*   Mafia (Offline Only)
*   Min Fina? (Online & Offline)
*   Taboo (Online & Offline)
*   Trivia Battle (Online & Offline)

## Setup and Running Locally

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd OnlineFlet 
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will be accessible at `http://localhost:8550` (or the port specified in `app.py`).

## Deployment

This application is configured for deployment on Render.com as a Web Service.

## Project Structure

*   `app.py`: Main Flet application, routing, and global state.
*   `*_game.py`: Client-side UI logic for each game (offline and online).
*   `server_actions/`: Contains server-side action processing logic for online games.
*   `assets/`: Static files like icons and `manifest.json`.
*   `trivia_data/`: Python modules containing trivia questions.
*   `*.py` (word lists, categories): Data files for various games.