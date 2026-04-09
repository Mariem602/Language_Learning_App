import streamlit as st
import ollama
import json
import random
import re

# ==================== CONFIGURATION ====================
THEMES = {
    "food": {"beginner": 5, "intermediate": 10, "advanced": 15},
    "clothing": {"beginner": 5, "intermediate": 10, "advanced": 15},
    "supermarket": {"beginner": 5, "intermediate": 10, "advanced": 15},
    "travel": {"beginner": 5, "intermediate": 10, "advanced": 15},
    "home": {"beginner": 5, "intermediate": 10, "advanced": 15},
}

DIFFICULTY_THRESHOLDS = {
    "beginner": 5,      # Need 5 correct to unlock intermediate
    "intermediate": 10,  # Need 10 correct to unlock advanced
    "advanced": 15       # Need 15 correct to unlock next theme
}

# ==================== INITIALIZE SESSION STATE ====================
if 'user_state' not in st.session_state:
    st.session_state.user_state = {
        'current_theme': 'food',
        'difficulty': 'beginner',
        'unlocked_themes': ['food'],
        'score': 0,
        'total_attempts': 0,
        'correct_answers': 0,
    }

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'current_word' not in st.session_state:
    st.session_state.current_word = None

if 'waiting_for_answer' not in st.session_state:
    st.session_state.waiting_for_answer = False

if 'used_words' not in st.session_state:
    st.session_state.used_words = set()  # Track words we've already shown

# ==================== HELPER FUNCTIONS ====================

def generate_word(theme, difficulty):
    """Generate a Spanish word for the given theme and difficulty"""
    
    max_retries = 5  # Increased to account for duplicate checking
    
    # Get list of used words
    used_words = st.session_state.get('used_words', set())
    
    # If we've used more than 20 words for this theme, reset the list
    theme_used = [w for w in used_words if f"{theme}:" in w]
    if len(theme_used) > 20:
        # Clear used words for this theme only
        st.session_state.used_words = {w for w in used_words if f"{theme}:" not in w}
        used_words = st.session_state.used_words
    
    for attempt in range(max_retries):
        # Create list of words to avoid
        used_spanish_words = [w.split(':')[1] for w in used_words if f"{theme}:" in w]
        avoid_list = ', '.join(used_spanish_words[-10:]) if used_spanish_words else 'none'  # Show last 10
        
        # Difficulty-specific instructions
        difficulty_hints = {
            'beginner': 'Use common, simple words that children learn first (like bread, water, milk).',
            'intermediate': 'Use everyday words that adults commonly use.',
            'advanced': 'Use less common or more specialized vocabulary.'
        }
        
        hint = difficulty_hints.get(difficulty, '')
        
        # Prompt that tells AI which words to avoid
        prompt = f"""Give me ONE {difficulty} level Spanish word about {theme}.
{hint}

DO NOT use these words (already used): {avoid_list}
DO NOT use dish names (like paella, gazpacho, tortilla española) - just use basic ingredients or items.

Reply ONLY with:
Spanish: [word]
English: [meaning]

Example:
Spanish: manzana
English: apple"""
        
        try:
            response = ollama.generate(
                model="llama3.2:3b",
                prompt=prompt,
                options={'temperature': 0.5, 'num_predict': 80}  # Keep consistent temperature
            )
            
            text = response['response'].strip().lower()
            
            # DEBUG: Show what the AI said (only first attempt)
            if attempt == 0:
                st.info(f"🔍 AI Response: {text}")
            
            # Parse the response
            spanish_word = None
            english_word = None
            
            lines = text.split('\n')
            
            for line in lines:
                # Skip junk lines
                if any(word in line for word in ['here', 'generate', 'give', 'reply', 'example', 'already']):
                    continue
                
                # Look for Spanish word
                if 'spanish' in line and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        word = parts[1].strip().split()[0] if parts[1].strip().split() else None
                        if word and len(word) > 2:
                            spanish_word = word.replace(',', '').replace('.', '').replace('"', '').replace("'", '')
                
                # Look for English translation
                if 'english' in line and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        word = parts[1].strip().split()[0] if parts[1].strip().split() else None
                        if word and len(word) > 2:
                            english_word = word.replace(',', '').replace('.', '').replace('"', '').replace("'", '')
            
            # Also try simple "word - translation" format
            if not spanish_word or not english_word:
                for line in lines:
                    if '-' in line:
                        parts = line.split('-', 1)
                        if len(parts) == 2:
                            sp = parts[0].strip().split()[0] if parts[0].strip().split() else None
                            en = parts[1].strip().split()[0] if parts[1].strip().split() else None
                            if sp and en and len(sp) > 2 and len(en) > 2:
                                spanish_word = sp.replace(',', '').replace('.', '')
                                english_word = en.replace(',', '').replace('.', '')
                                break
            
            # Validate words
            invalid_words = ['here', 'heres', 'word', 'spanish', 'english', 'example', 'the', 'a']
            
            if spanish_word and english_word:
                # Check if valid
                if spanish_word not in invalid_words and english_word not in invalid_words:
                    if len(spanish_word) > 2 and len(english_word) > 2:
                        # Check if we've used this word before
                        word_key = f"{theme}:{spanish_word}"
                        if word_key in used_words:
                            if attempt < max_retries - 1:
                                st.warning(f"⚠️ '{spanish_word}' already used, generating different word...")
                                continue
                        
                        # Success! Add to used words and return
                        st.session_state.used_words.add(word_key)
                        return {'spanish': spanish_word, 'english': english_word}
            
            # If we got here, parsing failed - try again
            if attempt < max_retries - 1:
                st.warning(f"⚠️ Attempt {attempt + 1} failed, retrying...")
            
        except Exception as e:
            if attempt < max_retries - 1:
                st.warning(f"⚠️ Error on attempt {attempt + 1}: {e}. Retrying...")
            else:
                st.error(f"❌ Failed after {max_retries} attempts: {e}")
    
    # If all retries failed
    st.error(f"❌ Could not generate a valid word after {max_retries} attempts. Please try again.")
    return {'spanish': 'error', 'english': 'click "Get New Word" again'}

def check_answer(user_answer, correct_answer):
    """Check if the user's answer is correct"""
    return user_answer.lower().strip() == correct_answer.lower().strip()

def update_progress(correct):
    """Update user progress and unlock new content"""
    state = st.session_state.user_state
    state['total_attempts'] += 1
    
    if correct:
        state['correct_answers'] += 1
        state['score'] += 1
        
        # Check for difficulty upgrade
        current_diff = state['difficulty']
        if current_diff == 'beginner' and state['score'] >= DIFFICULTY_THRESHOLDS['beginner']:
            state['difficulty'] = 'intermediate'
            st.success("🎉 Unlocked Intermediate level!")
            state['score'] = 0  # Reset score for new difficulty
        elif current_diff == 'intermediate' and state['score'] >= DIFFICULTY_THRESHOLDS['intermediate']:
            state['difficulty'] = 'advanced'
            st.success("🎉 Unlocked Advanced level!")
            state['score'] = 0
        elif current_diff == 'advanced' and state['score'] >= DIFFICULTY_THRESHOLDS['advanced']:
            # Unlock next theme
            unlock_next_theme()
            state['difficulty'] = 'beginner'
            state['score'] = 0

def unlock_next_theme():
    """Unlock the next theme in progression"""
    state = st.session_state.user_state
    all_themes = list(THEMES.keys())
    current_index = all_themes.index(state['current_theme'])
    
    if current_index < len(all_themes) - 1:
        next_theme = all_themes[current_index + 1]
        if next_theme not in state['unlocked_themes']:
            state['unlocked_themes'].append(next_theme)
            state['current_theme'] = next_theme
            st.success(f"🎉 Unlocked new theme: {next_theme.capitalize()}!")
    else:
        st.balloons()
        st.success("🎊 Congratulations! You've completed all themes!")

def chat_with_ai(user_message):
    """Chat with the AI tutor"""
    st.session_state.messages.append({"role": "user", "content": user_message})
    
    try:
        response = ollama.chat(
            model="llama3.2:3b",
            messages=st.session_state.messages,
            options={'temperature': 0.7}
        )
        
        ai_response = response['message']['content']
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        return ai_response
        
    except Exception as e:
        error_msg = f"Sorry, I encountered an error: {e}"
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        return error_msg

# ==================== UI ====================

st.set_page_config(page_title="Language Learning Chatbot", page_icon="📚", layout="wide")

st.title("📚 Spanish Language Learning Chatbot")

# Sidebar - User Progress
with st.sidebar:
    st.header("📊 Your Progress")
    state = st.session_state.user_state
    
    st.metric("Current Theme", state['current_theme'].capitalize())
    st.metric("Difficulty Level", state['difficulty'].capitalize())
    st.metric("Score", f"{state['score']}/{DIFFICULTY_THRESHOLDS[state['difficulty']]}")
    st.metric("Correct Answers", state['correct_answers'])
    st.metric("Total Attempts", state['total_attempts'])
    
    if state['total_attempts'] > 0:
        accuracy = (state['correct_answers'] / state['total_attempts']) * 100
        st.metric("Accuracy", f"{accuracy:.1f}%")
    
    st.divider()
    
    st.subheader("🔓 Unlocked Themes")
    for theme in state['unlocked_themes']:
        st.write(f"✅ {theme.capitalize()}")
    
    st.divider()
    
    # Theme selector
    st.subheader("📝 Select Theme")
    selected_theme = st.selectbox(
        "Choose a theme to practice:",
        state['unlocked_themes'],
        index=state['unlocked_themes'].index(state['current_theme'])
    )
    
    if selected_theme != state['current_theme']:
        state['current_theme'] = selected_theme
        st.rerun()
    
    st.divider()
    
    if st.button("🔄 Reset Progress"):
        st.session_state.user_state = {
            'current_theme': 'food',
            'difficulty': 'beginner',
            'unlocked_themes': ['food'],
            'score': 0,
            'total_attempts': 0,
            'correct_answers': 0,
        }
        st.session_state.messages = []
        st.session_state.current_word = None
        st.session_state.waiting_for_answer = False
        st.session_state.used_words = set()
        st.rerun()
    
    # Show how many words have been used
    used_count = len([w for w in st.session_state.get('used_words', set()) if f"{state['current_theme']}:" in w])
    if used_count > 0:
        st.caption(f"📝 {used_count} words used in {state['current_theme'].capitalize()}")
        if st.button("🗑️ Clear word history"):
            st.session_state.used_words = set()
            st.success("Word history cleared!")
            st.rerun()

# Main content area - tabs
tab1, tab2 = st.tabs(["🎯 Word Practice", "💬 Chat Tutor"])

# ==================== TAB 1: WORD PRACTICE ====================
with tab1:
    st.header("Word Translation Practice")
    st.write(f"**Theme:** {state['current_theme'].capitalize()} | **Level:** {state['difficulty'].capitalize()}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🎲 Get New Word", use_container_width=True):
            with st.spinner("Generating word..."):
                word = generate_word(state['current_theme'], state['difficulty'])
                st.session_state.current_word = word
                st.session_state.waiting_for_answer = True
                st.rerun()
    
    if st.session_state.current_word:
        st.divider()
        
        word = st.session_state.current_word
        
        st.subheader("Translate this word:")
        st.markdown(f"### 🇪🇸 **{word['spanish']}**")
        
        if st.session_state.waiting_for_answer:
            user_answer = st.text_input("Your answer (in English):", key="word_answer")
            
            col_submit, col_skip = st.columns(2)
            
            with col_submit:
                if st.button("✅ Submit Answer", use_container_width=True):
                    if user_answer:
                        is_correct = check_answer(user_answer, word['english'])
                        
                        if is_correct:
                            st.success(f"✅ Correct! '{word['spanish']}' means '{word['english']}'")
                            update_progress(True)
                        else:
                            st.error(f"❌ Not quite. '{word['spanish']}' means '{word['english']}'")
                            update_progress(False)
                        
                        st.session_state.waiting_for_answer = False
                        st.rerun()
                    else:
                        st.warning("Please enter an answer first!")
            
            with col_skip:
                if st.button("⏭️ Skip", use_container_width=True):
                    st.info(f"The answer was: **{word['english']}**")
                    st.session_state.waiting_for_answer = False
                    st.rerun()
        else:
            st.info(f"**Answer:** {word['english']}")
            if st.button("➡️ Next Word"):
                st.session_state.current_word = None
                st.rerun()

# ==================== TAB 2: CHAT TUTOR ====================
with tab2:
    st.header("Chat with Your Spanish Tutor")
    st.write("Ask questions, practice sentences, or get help with grammar!")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat_with_ai(prompt)
                st.write(response)
    
    # Quick action buttons
    st.divider()
    st.subheader("Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💡 Get a tip", use_container_width=True):
            tip_prompt = f"Give me one helpful tip for learning {state['current_theme']} vocabulary in Spanish at {state['difficulty']} level."
            with st.spinner("Getting tip..."):
                response = chat_with_ai(tip_prompt)
    
    with col2:
        if st.button("📝 Practice sentence", use_container_width=True):
            sentence_prompt = f"Give me a simple Spanish sentence using a {state['difficulty']} level word about {state['current_theme']}. Then translate it to English."
            with st.spinner("Creating sentence..."):
                response = chat_with_ai(sentence_prompt)
    
    with col3:
        if st.button("❓ Ask a question", use_container_width=True):
            st.info("Type your question in the chat box above!")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Footer
st.divider()
st.caption("Made with ❤️ using Streamlit and Ollama | Model: llama3.2:3b")
