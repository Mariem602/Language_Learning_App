#  AI Spanish Tutor

A progressive Spanish learning app built with **Streamlit** and a **local LLM** (Llama 3.2 3B running through **Ollama**). Practice vocabulary by theme, unlock harder levels as you improve, and chat with an AI tutor, all without sending any data to an external API.

## Features

- **AI-generated vocabulary drills:** the model produces a Spanish word for the chosen theme and difficulty, and you translate it into English.
- **Progressive unlocking:**
  - Difficulty goes `beginner → intermediate → advanced`.
  - Finishing *advanced* in a theme unlocks the next theme.
  - Themes, in order: **food → clothing → supermarket → travel → home**.
- **Score thresholds:** 5 correct answers to unlock Intermediate, 10 for Advanced, 15 to unlock the next theme (the score resets at each level).
- **Chat tutor:** ask grammar questions, practice sentences, or get tips. Quick-action buttons generate a tip or a practice sentence for your current theme and level.
- **Progress sidebar:** current theme and level, score, correct answers, total attempts and accuracy.
- **Repeat avoidance:** words already shown in a theme are passed back to the model so it avoids repeating them (the history resets after 20 words per theme).
- **Private and free:** inference runs locally via Ollama, so there are no API keys and no per-request cost.

## Tech stack

| Component | Role |
|-----------|------|
| Python 3.9+ | Language |
| Streamlit | Web UI and session state |
| Ollama | Local LLM runtime |
| Llama 3.2 3B (`llama3.2:3b`) | Word generation and chat |

## Getting started

### 1. Install Ollama and the model

Install Ollama from [ollama.com](https://ollama.com), then pull the model:

```bash
ollama pull llama3.2:3b
```

Make sure the Ollama service is running before you start the app.

### 2. Install the Python dependencies

```bash
pip install streamlit ollama
```

### 3. Run the app

```bash
streamlit run app.py
```

Replace `app.py` with the name of your main script. The app opens at `http://localhost:8501`.

## How to use

1. **Word Practice tab:** click *Get New Word*, type the English translation, and press *Submit Answer* (or *Skip* to see the answer).
2. **Chat Tutor tab:** type any question, or use the quick actions for a tip or a practice sentence.
3. Use the **sidebar** to follow your progress, switch between unlocked themes, reset your progress or clear the word history.

## How it works

1. `generate_word()` prompts the model for one word at the current theme and difficulty. It includes a difficulty hint and the list of recently used words to avoid, then parses the `Spanish: / English:` reply. Invalid or duplicate results trigger up to 5 retries.
2. `check_answer()` compares your answer to the expected translation, ignoring case and surrounding spaces.
3. `update_progress()` updates the score and handles level and theme unlocking.
4. `chat_with_ai()` keeps the whole conversation in session state and sends it to the model on each turn.

Model settings: temperature `0.5` for word generation (more consistent) and `0.7` for chat (more natural).

## Known limitations

- Progress is stored in Streamlit session state, so it **is lost when the page is refreshed or the app restarts**.
- Answers must match the expected translation exactly. Synonyms (for example "bread" vs "loaf") are marked wrong.
- A 3B model sometimes returns badly formatted or wrong translations, which is why the app retries and shows a debug line with the raw model output.
- The parser keeps only the first word of each answer, so multi-word translations are cut short.

## Possible improvements

- Persist progress (SQLite or a JSON file).
- Accept synonyms or fuzzy matches when checking answers.
- Ask the model for structured JSON output to make parsing more reliable.
- Add more themes, sentence-level exercises and pronunciation support.
- Let users choose the Ollama model from the sidebar.
