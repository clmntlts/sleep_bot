import streamlit as st
import google.generativeai as genai
import requests

# 👉 Configuration de la page
st.set_page_config(page_title="Chatbot Gemini", layout="centered")
st.title("🤖 Sleep bot - Made in Clément")

# 👉 Barre latérale : Configuration
st.sidebar.header("🔐 Configuration")
api_key = st.sidebar.text_input("Clé API Gemini", type="password", placeholder="Collez votre API Key ici")

# 👉 Paramètres du modèle
st.sidebar.header("⚙️ Paramètres du modèle")
temperature = st.sidebar.slider("Température (créativité)", 0.0, 1.0, 0.7)
max_tokens = st.sidebar.slider("Longueur max de réponse", 100, 2048, 1024)
top_p = st.sidebar.slider("Top-p", 0.0, 1.0, 1.0)
top_k = st.sidebar.slider("Top-k", 1, 100, 40)

# 👉 Paramètres généraux
DEFAULT_PROMPT = "Tu es un assistant psychologue expert du sommeil"
GITHUB_PROMPT_URL = "https://raw.githubusercontent.com/clmntlts/sleep_bot/main/sleep_prompt.txt"
MODEL_NAMES = ["gemini-2.5-pro-exp-03-25", "gemini-1.5-flash"]

# 👉 Mise en cache du prompt
@st.cache_data(show_spinner="🔄 Téléchargement du prompt depuis GitHub...")
def fetch_prompt(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception:
        return DEFAULT_PROMPT

# 👉 Initialisation du modèle avec cache
@st.cache_resource(show_spinner="🔄 Initialisation du modèle...")
def init_model(model_name, system_instruction, config):
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction,
        generation_config=config
    )

# 👉 Fonction export markdown
def export_conversation_as_markdown(history):
    md = "# 🧠 Rapport de conversation\n\n"
    for message in history:
        role = "👤 Utilisateur" if message.role == "user" else "🤖 Assistant"
        md += f"## {role}\n\n{message.parts[0].text}\n\n"
    return md

# 👉 Lancement principal
if not api_key:
    st.warning("Veuillez entrer votre clé API Gemini dans la barre latérale.")
else:
    try:
        genai.configure(api_key=api_key)

        # 👉 Choix du modèle
        selected_model = st.sidebar.selectbox("🧠 Choisir le modèle", MODEL_NAMES, index=0)

        # 👉 Chargement du prompt depuis GitHub
        prompt_text = fetch_prompt(GITHUB_PROMPT_URL)

        # 👉 Configuration du modèle
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
        )

        # 👉 Initialisation ou récupération du modèle depuis session_state
        if "model" not in st.session_state or st.session_state.model_name != selected_model:
            try:
                st.session_state.model = init_model(selected_model, prompt_text, generation_config)
                st.session_state.model_name = selected_model
            except Exception as e:
                if "deprecated" in str(e).lower():
                    st.warning(f"{selected_model} est déprécié. Passage à 'gemini-1.5-flash'.")
                    selected_model = "gemini-1.5-flash"
                    st.session_state.model = init_model(selected_model, prompt_text, generation_config)
                    st.session_state.model_name = selected_model
                else:
                    raise e

        # 👉 Initialisation du chat
        if "chat" not in st.session_state:
            st.session_state.chat = st.session_state.model.start_chat(history=[])

        # 👉 Zone de saisie utilisateur
        user_input = st.chat_input("Entrez votre message...")

        # 👉 Affichage de l’historique
        for message in st.session_state.chat.history:
            with st.chat_message(message.role):
                st.markdown(message.parts[0].text)

        # 👉 Réponse du bot
        if user_input:
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("model"):
                response = st.session_state.chat.send_message(user_input)
                st.markdown(response.text)

        # 👉 Bouton d’exportation du rapport
        if st.session_state.chat.history:
            report_md = export_conversation_as_markdown(st.session_state.chat.history)
            st.download_button(
                label="📥 Télécharger le rapport (.md)",
                data=report_md.encode("utf-8"),
                file_name="rapport_conversation.md",
                mime="text/markdown"
            )

    except Exception as e:
        st.error(f"❌ Erreur lors de l'initialisation : {e}")
