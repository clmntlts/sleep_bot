import streamlit as st
import google.generativeai as genai
import requests
import datetime # Importation ajoutée

# 👉 Configuration de la page
st.set_page_config(page_title="Chatbot Gemini", layout="centered")
st.title("🤖 Sleep bot - Made in Clément")

# 👉 Barre latérale : Configuration
st.sidebar.header("🔐 Configuration")
api_key = st.sidebar.text_input("Clé API Gemini", type="password", placeholder="Collez votre API Key ici")

# 👉 Paramètres du modèle
st.sidebar.header("⚙️ Paramètres du modèle")
temperature = st.sidebar.slider("Température (créativité)", 0.0, 1.0, 0.7)
max_tokens = st.sidebar.slider("Longueur max de réponse", 100, 4096, 2048) # Augmenté
top_p = st.sidebar.slider("Top-p", 0.0, 1.0, 1.0)
top_k = st.sidebar.slider("Top-k", 1, 100, 40)

# 👉 Paramètres généraux
DEFAULT_PROMPT = "Tu es un assistant psychologue expert du sommeil spécialisé dans la Thérapie Cognitive et Comportementale pour l'Insomnie (TCC-I). Ton rôle est de guider un patient à travers un entretien clinique initial structuré. Suis attentivement les instructions de section."
GITHUB_PROMPT_URL = "https://raw.githubusercontent.com/clmntlts/sleep_bot/main/sleep_prompt.txt" # Assurez-vous que ce prompt est complet
MODEL_NAMES = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"]

INTERVIEW_SECTIONS = {
    1: "Motif de consultation et plainte principale",
    2: "Caractéristiques détaillées de l’insomnie",
    3: "Conséquences diurnes et somnolence",
    4: "Hygiène de sommeil, environnement et rythmes",
    5: "Facteurs cognitifs et émotionnels",
    6: "Facteurs comportementaux",
    7: "Antécédents médicaux et psychiatriques",
    8: "Histoire du sommeil et traitements antérieurs",
    9: "Contexte psychosocial et stresseurs",
    10: "Attentes et motivation"
}

if "interview_section" not in st.session_state:
    st.session_state.interview_section = 1
if "interview_complete" not in st.session_state:
    st.session_state.interview_complete = False


@st.cache_data(show_spinner="🔄 Téléchargement du prompt depuis GitHub...")
def fetch_prompt(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        st.success("Prompt de l'entretien chargé depuis GitHub.")
        return response.text
    except Exception as e:
        st.warning(f"Impossible de charger le prompt depuis GitHub ({e}). Utilisation du prompt par défaut.")
        return DEFAULT_PROMPT

# MODIFIÉ: init_gemini_model prend system_instruction
# RETIRÉ: @st.cache_resource car system_instruction est dynamique
def init_gemini_model(model_name, system_instruction_for_model):
    # st.write(f"DEBUG: Initialisation du modèle {model_name} avec instruction système.") # Pour débogage
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction_for_model # Paramètre correct
        )
        return model
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation de GenerativeModel ({model_name}): {e}")
        st.exception(e)
        return None

def export_conversation_as_markdown(history):
    today = datetime.date.today()
    md = f"# 🧠 Historique de Conversation - {today}\n\n"
    if not history: return "L'historique de la conversation est vide."
    for message in history:
        role = "👤 Patient" if message.role == "user" else "🤖 Assistant IA"
        text_content = message.parts[0].text if message.parts else "[Message vide]"
        md += f"**{role}:**\n{text_content}\n\n---\n\n"
    return md

def generate_clinical_summary(chat_history, model_instance, generation_config_for_summary):
    if not chat_history: return "Impossible de générer le rapport : l'historique est vide."
    conversation_text = ""
    for message in chat_history:
        role = "Patient" if message.role == "user" else "Assistant IA"
        text_content = message.parts[0].text if message.parts else ""
        conversation_text += f"{role}: {text_content}\n\n"

    summary_prompt_text = f"""
**Prompt pour Génération de Compte Rendu Clinique TCC-I**
**Votre Rôle :** Vous êtes un assistant IA chargé de rédiger un compte rendu clinique structuré.
**Tâche :** En vous basant **exclusivement** sur l'historique de la conversation d'entretien clinique TCC-I fourni ci-dessous, générez un compte rendu synthétique, détaillé et organisé destiné à un thérapeute qualifié.
**Format de Sortie Attendu :** Le compte rendu doit **strictement** suivre la structure suivante, en extrayant et synthétisant les informations pertinentes de la conversation pour chaque section :

1.  **Identifiant Patient (si disponible dans l'historique, sinon omettre)**
2.  **Motif de Consultation**
3.  **Histoire de l'Insomnie & Caractéristiques Actuelles** (incluant type, début, durée, horaire type semaine/weekend, latence, réveils, TST estimé, qualité/satisfaction subjective, variabilité, perception par autrui)
4.  **Facteurs Cognitifs** (inquiétudes spécifiques, peurs sur conséquences, attentes, rumination, attribution, perception contrôle, effort/lutte, émotions associées, niveau de préoccupation)
5.  **Facteurs Comportementaux** (actions pendant l'éveil nocturne, description d'une nuit type, consultation de l'heure, comportements compensatoires)
6.  **Hygiène de Sommeil, Environnement & Rythmes** (routine, environnement, usage du lit, consommation substances, activité physique, alimentation, régularité horaires, lumière)
7.  **Conséquences Diurnes & Somnolence** (impact sur fonctionnement, échelle d'impact, évaluation type ESS si disponible, siestes)
8.  **Antécédents Médicaux, Psychiatriques & Autres Troubles du Sommeil** (conditions médicales, suivi psy, médicaments/compléments, facteurs féminins, dépistage SAOS/SJSR basé sur les réponses)
9.  **Traitements Antérieurs** (expériences passées avec traitements)
10. **Contexte Psychosocial & Stresseurs Actuels** (niveau de stress, sources, gestion stress, soutien social)
11. **Attentes & Motivation** (attentes TCC-I, objectifs concrets, échelle motivation, craintes/hésitations)
12. **Synthèse des Facteurs de Maintien Proposés** (résumé des hypothèses sur les facteurs cognitifs, comportementaux, circadiens etc. qui entretiennent l'insomnie, basé sur l'analyse de la conversation)
13. **Niveau de Motivation & Compréhension** (évaluation subjective basée sur les dires du patient)
14. **Drapeaux Rouges / Points d'Attention** (mention de toute suspicion SAOS/SJSR, symptômes anxio-dépressifs marqués, idées suicidaires si exprimées, abus de substance, ou tout autre point nécessitant une vigilance clinique particulière)

**Instructions Importantes :**
* **Basez-vous UNIQUEMENT sur le contenu de la conversation fournie.** N'inventez aucune information. Si une information manque pour une section, indiquez "Non abordé" ou "Information non disponible dans l'historique".
* Adoptez un ton clinique, professionnel et objectif.
* Soyez synthétique tout en restant informatif.
* Respectez scrupuleusement la structure demandée.
**Historique de la Conversation à Synthétiser :**
--- DÉBUT HISTORIQUE ---
{conversation_text}
--- FIN HISTORIQUE ---"""
    try:
        response = model_instance.generate_content(
            summary_prompt_text,
            generation_config=generation_config_for_summary
        )
        summary_text = response.parts[0].text if response.parts else ""
        if not summary_text and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            return f"Erreur : La génération du rapport a été bloquée. Raison : {response.prompt_feedback.block_reason}"
        return summary_text if summary_text else "Le modèle n'a pas pu générer de résumé."
    except Exception as e:
        print(f"Erreur lors de l'appel à generate_content pour le résumé : {e}")
        return f"Erreur technique lors de la génération du compte rendu : {e}"

# 👉 Lancement principal
if not api_key:
    st.warning("Veuillez entrer votre clé API Gemini dans la barre latérale.")
    st.stop()

try:
    genai.configure(api_key=api_key)
    selected_model_name = st.sidebar.selectbox("🧠 Choisir le modèle", MODEL_NAMES, index=0)
    interview_prompt_base = fetch_prompt(GITHUB_PROMPT_URL)

    # Auto-introduction par le bot en début de section
    if not st.session_state.interview_complete and st.session_state.get("awaiting_bot_intro", True):
        with st.chat_message("model"):
            intro_prompt = f"Commençons la section {st.session_state.interview_section} : '{INTERVIEW_SECTIONS[st.session_state.interview_section]}'. Peux-tu me parler de cela ?"
            response = st.session_state.chat.send_message(intro_prompt, generation_config=generation_config)
            st.markdown(response.text if hasattr(response, "text") else "[Réponse vide]")
        st.session_state.awaiting_bot_intro = False


    if not st.session_state.interview_complete:
        current_section_number = st.session_state.interview_section
        current_section_title = INTERVIEW_SECTIONS.get(current_section_number, "Section inconnue")
        section_instruction = f"\n\n🎯 Nous sommes actuellement dans la section {current_section_number} : '{current_section_title}'. Concentre tes questions sur cette section spécifique pour le moment. Guide l'utilisateur à travers cette section."
        current_full_system_prompt = interview_prompt_base + section_instruction
    else:
        current_full_system_prompt = interview_prompt_base + "\n\n L'entretien est terminé. Remercie l'utilisateur et indique qu'il peut télécharger les rapports."

    should_reinitialize_model_and_chat = (
        "gemini_model_instance" not in st.session_state or
        st.session_state.get("current_model_name") != selected_model_name or
        st.session_state.get("system_prompt_in_use") != current_full_system_prompt
    )

    if should_reinitialize_model_and_chat:
        # st.write("DEBUG: Réinitialisation du modèle et/ou de la session de chat...")
        st.session_state.gemini_model_instance = init_gemini_model(selected_model_name, current_full_system_prompt)
        if st.session_state.gemini_model_instance is None: # Vérifier si l'init a échoué
            st.error("Échec de l'initialisation du modèle. Vérifiez la console pour les erreurs.")
            st.stop()

        st.session_state.current_model_name = selected_model_name
        st.session_state.system_prompt_in_use = current_full_system_prompt
        
        history_for_new_chat = []
        # Conserver l'historique si le nom du modèle n'a pas changé
        if "chat" in st.session_state and hasattr(st.session_state.chat, 'history') and st.session_state.get("current_model_name") == selected_model_name:
            history_for_new_chat = st.session_state.chat.history
        
        st.session_state.chat = st.session_state.gemini_model_instance.start_chat(
            history=history_for_new_chat # PAS d'argument system_prompt ici
        )
        # st.success(f"Modèle {selected_model_name} prêt. Section : {st.session_state.get('interview_section',1)}")


    generation_config = genai.types.GenerationConfig(
        temperature=temperature, max_output_tokens=max_tokens, top_p=top_p, top_k=top_k
    )

    if not st.session_state.interview_complete:
        current_section_title = INTERVIEW_SECTIONS.get(st.session_state.interview_section, "Terminé")
        st.markdown(f"### 📋 Section {st.session_state.interview_section} / {len(INTERVIEW_SECTIONS)} : {current_section_title}")
        st.progress(st.session_state.interview_section / len(INTERVIEW_SECTIONS))

    if "chat" in st.session_state:
        for message in st.session_state.chat.history:
            role_display = "user" if message.role == "user" else "model"
            with st.chat_message(role_display):
                st.markdown(message.parts[0].text if message.parts else "[Message vide]")

    user_input = None
    if not st.session_state.interview_complete:
        user_input = st.chat_input("Répondez ici...")

    if user_input and "chat" in st.session_state:
        with st.chat_message("user"): st.markdown(user_input)
        with st.chat_message("model"):
            message_placeholder = st.empty()
            try:
                response = st.session_state.chat.send_message(user_input, generation_config=generation_config)
                response_text = response.parts[0].text if response.parts else ""
                if not response_text and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    response_text = f"⚠️ Réponse bloquée. Raison : {response.prompt_feedback.block_reason}"
                message_placeholder.markdown(response_text)
            except Exception as e:
                st.error(f"Erreur lors de l'envoi du message : {e}")

    col_action1, col_action2 = st.columns([3,1])
    with col_action1:
        if not st.session_state.interview_complete:
            if st.session_state.interview_section < len(INTERVIEW_SECTIONS):
                if st.button(f"✅ Terminer section {st.session_state.interview_section} et passer à la suivante", use_container_width=True):
                    st.session_state.interview_section += 1
                    st.session_state.awaiting_bot_intro = True
                    st.rerun()
            elif st.session_state.interview_section == len(INTERVIEW_SECTIONS):
                if st.button("🏁 Terminer l'entretien", use_container_width=True):
                    st.session_state.interview_complete = True
                    st.rerun()
    
    with col_action2:
        if st.button("🔄 Réinitialiser", use_container_width=True):
            keys_to_reset = ["chat", "interview_section", "interview_complete", "gemini_model_instance", "current_model_name", "system_prompt_in_use"]
            for key in keys_to_reset:
                if key in st.session_state: del st.session_state[key]
            st.cache_data.clear(); st.cache_resource.clear()
            st.success("Entretien réinitialisé."); st.rerun()

    if st.session_state.interview_complete:
        st.success("🎉 Entretien terminé ! Vous pouvez maintenant télécharger les rapports.")
        st.markdown("---"); st.subheader("Téléchargement des Rapports")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            if "chat" in st.session_state and st.session_state.chat.history:
                raw_history_md = export_conversation_as_markdown(st.session_state.chat.history)
                st.download_button(label="📥 Télécharger l'Historique (.md)", data=raw_history_md.encode("utf-8"), file_name=f"historique_entretien_{datetime.date.today()}.md", mime="text/markdown", key="download_raw_history")
            else: st.info("Aucun historique à télécharger.")
        with col_dl2:
            if "chat" in st.session_state and st.session_state.chat.history and "gemini_model_instance" in st.session_state:
                with st.spinner("Génération du compte rendu clinique..."):
                    clinical_summary_md = generate_clinical_summary(st.session_state.chat.history, st.session_state.gemini_model_instance, generation_config)
                if "Erreur" in clinical_summary_md: st.error(clinical_summary_md)
                else: st.download_button(label="📥 Télécharger le Compte Rendu (.md)", data=clinical_summary_md.encode("utf-8"), file_name=f"compte_rendu_clinique_{datetime.date.today()}.md", mime="text/markdown", key="download_summary_report")
            elif not ("chat" in st.session_state and st.session_state.chat.history) : st.info("Aucun historique pour générer un compte rendu.")
            else: st.warning("Modèle IA non initialisé, compte rendu impossible.")

except Exception as e:
    st.error(f"❌ Une erreur majeure est survenue : {e}")
    st.exception(e)