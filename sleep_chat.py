import streamlit as st
import google.generativeai as genai
import requests

# 👉 Configuration de la page
st.set_page_config(page_title="Chatbot Gemini", layout="centered")
st.title("🤖 Sleep bot - Made in Clément")

# 👉 Barre latérale : Clé API et chargement prompt
st.sidebar.header("🔐 Configuration")
api_key = st.sidebar.text_input("Clé API Gemini", type="password", placeholder="Collez votre API Key ici")

st.sidebar.markdown("---")
default_instruction = st.sidebar.text_area(
    "✍️ Instructions du système",
    placeholder="Ex : Tu es un assistant psychologue expert du sommeil..."
)

# 👉 GitHub raw URL for the sleep_prompt.txt
github_raw_url = "https://raw.githubusercontent.com/clmntlts/sleep_bot/main/sleep_prompt.txt"

# 👉 Initialisation API et configuration
if api_key:
    try:
        genai.configure(api_key=api_key)

        # 👉 Liste des modèles
        model_names = []
        try:
            all_models = genai.list_models()
            model_names = [m.name for m in all_models if "generateContent" in m.supported_generation_methods]
        except Exception as e:
            model_names = ["models/gemini-pro"]
            st.sidebar.warning(f"Erreur lors du chargement des modèles : {e}")

        selected_model = st.sidebar.selectbox("🧠 Choisir le modèle", model_names, index=0)

        # 👉 Paramètres du modèle
        st.sidebar.header("⚙️ Paramètres du modèle")
        temperature = st.sidebar.slider("Température (créativité)", 0.0, 1.0, 0.7)
        max_tokens = st.sidebar.slider("Longueur max de réponse", 100, 2048, 1024)
        top_p = st.sidebar.slider("Top-p", 0.0, 1.0, 1.0)
        top_k = st.sidebar.slider("Top-k", 1, 100, 40)

        # 👉 Télécharger et utiliser le fichier sleep_prompt.txt depuis GitHub
        try:
            response = requests.get(github_raw_url)
            response.raise_for_status()  # Raises an error for non-200 status codes
            system_instruction = response.text
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur lors du téléchargement du fichier de prompt depuis GitHub : {e}")
            system_instruction = default_instruction

        # 👉 Initialisation du modèle
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
            )
        )

        # 👉 Démarrage session de chat
        if "chat" not in st.session_state:
            st.session_state.chat = model.start_chat(history=[])

        # 👉 Zone de saisie utilisateur
        user_input = st.chat_input("Entrez votre message...")

        # 👉 Affichage de l’historique
        for message in st.session_state.chat.history:
            with st.chat_message(message.role):
                st.markdown(message.parts[0].text)

        # 👉 Traitement du message utilisateur
        if user_input:
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("model"):
                response = st.session_state.chat.send_message(user_input)
                st.markdown(response.text)

        # 👉 Fonction export markdown
        def export_conversation_as_markdown(history):
            md = "# 🧠 Rapport de conversation\n\n"
            for message in history:
                role = "👤 Utilisateur" if message.role == "user" else "🤖 Assistant"
                md += f"## {role}\n\n{message.parts[0].text}\n\n"
            return md

        # 👉 Bouton de téléchargement du rapport
        if st.session_state.chat.history:
            report_md = export_conversation_as_markdown(st.session_state.chat.history)
            st.download_button(
                label="📥 Télécharger le rapport (.md)",
                data=report_md.encode("utf-8"),
                file_name="rapport_conversation.md",
                mime="text/markdown"
            )

    except Exception as e:
        st.error(f"Erreur lors de l'initialisation du modèle : {e}")
else:
    st.warning("Veuillez entrer votre clé API Gemini dans la barre latérale.")
