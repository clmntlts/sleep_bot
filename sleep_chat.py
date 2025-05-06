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
max_tokens = st.sidebar.slider("Longueur max de réponse", 100, 2048, 1024) # Augmenté pour permettre des rapports plus longs
top_p = st.sidebar.slider("Top-p", 0.0, 1.0, 1.0)
top_k = st.sidebar.slider("Top-k", 1, 100, 40)

# 👉 Paramètres généraux
DEFAULT_PROMPT = "Tu es un assistant psychologue expert du sommeil"
# Assurez-vous que ce prompt contient les instructions détaillées pour mener l'entretien
# comme celui fourni dans les messages précédents.
GITHUB_PROMPT_URL = "https://raw.githubusercontent.com/clmntlts/sleep_bot/main/sleep_prompt.txt"
MODEL_NAMES = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"] # Modèles recommandés pour de longues conversations/synthèses

# 👉 Définition des sections de l'entretien
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

# 👉 Initialisation de l'état de l'entretien
if "interview_section" not in st.session_state:
    st.session_state.interview_section = 1

if "interview_complete" not in st.session_state:
    st.session_state.interview_complete = False

# 👉 Mise en cache du prompt
@st.cache_data(show_spinner="🔄 Téléchargement du prompt depuis GitHub...")
def fetch_prompt(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        st.success("Prompt chargé depuis GitHub.")
        return response.text
    except Exception as e:
        st.warning(f"Impossible de charger le prompt depuis GitHub ({e}). Utilisation du prompt par défaut.")
        return DEFAULT_PROMPT

# 👉 Initialisation du modèle avec cache
# Note: La configuration de génération est appliquée lors de l'appel, pas à l'init.
# Le system_instruction peut changer, donc on ne le cache pas ici directement.
@st.cache_resource(show_spinner="🔄 Initialisation du modèle...")
def init_gemini_model(model_name):
     # L'instruction système sera définie lors du démarrage du chat
    return genai.GenerativeModel(model_name=model_name)

# 👉 Fonction export markdown (adaptée à la structure de l'historique Gemini)
def export_conversation_as_markdown(history):
    today = datetime.date.today()
    md = f"# 🧠 Historique de Conversation - {today}\n\n"
    if not history:
        return "L'historique de la conversation est vide."
    for message in history:
        # Utilisation de 'user' et 'model' comme rôles standards de l'API Gemini
        role = "👤 Patient" if message.role == "user" else "🤖 Assistant IA"
        # Vérifier si parts existe et n'est pas vide
        text_content = ""
        if message.parts:
            # Prendre le texte de la première partie (la plus courante)
            text_content = message.parts[0].text
        md += f"**{role}:**\n{text_content}\n\n---\n\n"
    return md

# 👉 NOUVELLE FONCTION POUR GÉNÉRER LE COMPTE RENDU STRUCTURÉ
def generate_clinical_summary(chat_history, model, generation_config):
    if not chat_history:
        return "Impossible de générer le rapport : l'historique est vide."

    # 1. Formater l'historique pour l'envoyer au modèle
    conversation_text = ""
    for message in chat_history:
        role = "Patient" if message.role == "user" else "Assistant IA"
        text_content = ""
        if message.parts:
            text_content = message.parts[0].text
        conversation_text += f"{role}: {text_content}\n\n"

    # 2. Définir le prompt de synthèse
    summary_prompt = f"""
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
--- FIN HISTORIQUE ---
"""

    # 3. Appeler le modèle IA pour générer la synthèse
    # Note: On utilise le même modèle que pour le chat, mais sans l'instruction système de l'entretien
    # et avec une configuration de génération potentiellement ajustée si nécessaire (ici on garde la même)
    try:
        # Utilisation de generate_content pour une tâche unique (pas de chat continu)
        response = model.generate_content(
            summary_prompt,
            generation_config=generation_config # Utilisation de la config définie par l'utilisateur
            )
        # Extraction correcte pour Gemini API
        summary_text = ""
        if response.parts:
            summary_text = response.parts[0].text
        # Vérification si le modèle a bloqué la réponse
        if not summary_text and response.prompt_feedback.block_reason:
             return f"Erreur : La génération du rapport a été bloquée. Raison : {response.prompt_feedback.block_reason}"
        return summary_text if summary_text else "Le modèle n'a pas pu générer de résumé."

    except Exception as e:
        # Log l'erreur pour le débogage pourrait être utile ici
        print(f"Erreur lors de l'appel à generate_content pour le résumé : {e}")
        return f"Erreur technique lors de la génération du compte rendu : {e}"


# 👉 Lancement principal
if not api_key:
    st.warning("Veuillez entrer votre clé API Gemini dans la barre latérale.")
    st.stop() # Arrêter l'exécution si pas de clé API

try:
    genai.configure(api_key=api_key)

    # 👉 Choix du modèle
    selected_model_name = st.sidebar.selectbox("🧠 Choisir le modèle", MODEL_NAMES, index=0)

    # 👉 Chargement du prompt de l'entretien
    interview_prompt_base = fetch_prompt(GITHUB_PROMPT_URL)

    # 👉 Initialisation ou récupération du modèle depuis session_state
    # On initialise le modèle sans instruction système ici, elle sera ajoutée au début du chat
    if "gemini_model" not in st.session_state or st.session_state.model_name != selected_model_name:
        try:
            st.session_state.gemini_model = init_gemini_model(selected_model_name)
            st.session_state.model_name = selected_model_name
            # Supprimer l'ancien chat si le modèle change
            if "chat" in st.session_state:
                del st.session_state.chat
            st.success(f"Modèle {selected_model_name} initialisé.")
        except Exception as e:
            st.error(f"Impossible d'initialiser le modèle {selected_model_name}: {e}")
            st.stop()

    # 👉 Construction du prompt système complet pour l'entretien en cours
    if not st.session_state.interview_complete:
        current_section_number = st.session_state.interview_section
        current_section_title = INTERVIEW_SECTIONS.get(current_section_number, "Section inconnue")
        section_instruction = f"\n\n🎯 Nous sommes actuellement dans la section {current_section_number} : '{current_section_title}'. Concentre tes questions sur cette section spécifique pour le moment. Guide l'utilisateur à travers cette section."
        full_system_prompt_for_interview = interview_prompt_base + section_instruction
    else:
        # Si l'entretien est terminé, on n'a plus besoin d'instruction de section
        full_system_prompt_for_interview = interview_prompt_base + "\n\n L'entretien est terminé. Remercie l'utilisateur et indique qu'il peut télécharger les rapports."


    # 👉 Initialisation du chat avec le prompt système dynamique
    # On redémarre le chat si le prompt système a changé (changement de section)
    # ou si le chat n'existe pas
    start_new_chat = False
    if "chat" not in st.session_state:
        start_new_chat = True
    elif "current_system_prompt" not in st.session_state or st.session_state.current_system_prompt != full_system_prompt_for_interview:
         # Si le prompt a changé (ex: section suivante), il faut parfois redémarrer le chat
         # ou au moins mettre à jour le contexte, selon l'API.
         # Pour Gemini, redémarrer peut être plus simple pour garantir le nouveau contexte.
         start_new_chat = True # Forcer le redémarrage pour appliquer le nouveau prompt de section


    if start_new_chat:
        st.session_state.current_system_prompt = full_system_prompt_for_interview
         # Démarrer un nouveau chat avec le prompt système actuel et l'historique existant
        history_for_new_chat = st.session_state.chat.history if "chat" in st.session_state else []
        st.session_state.chat = st.session_state.gemini_model.start_chat(
            history=history_for_new_chat # Conserver l'historique existant
            # Note: L'API Gemini actuelle gère le system prompt au niveau du modèle,
            # mais si on veut le changer dynamiquement, il faut le passer à send_message
            # ou redémarrer le chat si nécessaire. Ici on le gère au niveau du modèle si possible
            # ou on l'inclura dans les messages si besoin.
            # Pour l'instant, le prompt est surtout pour guider l'IA.
        )
        # Envoyer un premier message système pour guider sur la section actuelle (si non premier message)
        # if current_section_number > 1:
            # Pourrait être utile mais peut alourdir l'historique. À tester.
            # st.session_state.chat.send_message(f"Nous passons maintenant à la section : {current_section_title}", role="system") # Pas un rôle standard Gemini

    # 👉 Configuration de génération pour les appels send_message
    generation_config = genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        top_p=top_p,
        top_k=top_k,
    )


    # === AFFICHAGE ET INTERACTION ===

    # 👉 Affichage de la section en cours (si entretien non terminé)
    if not st.session_state.interview_complete:
        current_section_title = INTERVIEW_SECTIONS.get(st.session_state.interview_section, "Terminé")
        st.markdown(f"### 📋 Section {st.session_state.interview_section} / {len(INTERVIEW_SECTIONS)} : {current_section_title}")
        # Barre de progression
        progress_value = st.session_state.interview_section / len(INTERVIEW_SECTIONS)
        st.progress(progress_value)


    # 👉 Affichage de l’historique du chat
    if "chat" in st.session_state:
        for message in st.session_state.chat.history:
            role_display = "user" if message.role == "user" else "model"
            with st.chat_message(role_display):
                text_content = message.parts[0].text if message.parts else "[Message vide]"
                st.markdown(text_content)

    # 👉 Zone de saisie utilisateur (seulement si entretien non terminé)
    user_input = None
    if not st.session_state.interview_complete:
        user_input = st.chat_input("Répondez ici...")

    # 👉 Traitement de la réponse de l'utilisateur et réponse du bot
    if user_input and "chat" in st.session_state:
        # Afficher le message de l'utilisateur
        with st.chat_message("user"):
            st.markdown(user_input)

        # Envoyer le message au modèle et afficher la réponse
        with st.chat_message("model"):
            message_placeholder = st.empty()
            try:
                # Construire le message avec le contexte de la section si nécessaire
                # (Alternative si le system_prompt n'est pas dynamique)
                # prompt_with_context = f"{full_system_prompt_for_interview}\n\nUtilisateur: {user_input}\n\nAssistant:"
                # response = st.session_state.gemini_model.generate_content(prompt_with_context, generation_config=generation_config)

                # Utilisation de send_message (plus adapté pour un chat)
                response = st.session_state.chat.send_message(
                     user_input,
                     generation_config=generation_config,
                     # stream=True # Activer si vous voulez un affichage en streaming
                 )

                # Affichage simple (si stream=False)
                response_text = ""
                if response.parts:
                     response_text = response.parts[0].text
                elif response.prompt_feedback.block_reason:
                     response_text = f"⚠️ Réponse bloquée par le modèle. Raison : {response.prompt_feedback.block_reason}"

                message_placeholder.markdown(response_text)

                # Affichage en streaming (si stream=True)
                # full_response = ""
                # for chunk in response:
                #     full_response += chunk.text
                #     message_placeholder.markdown(full_response + "▌")
                # message_placeholder.markdown(full_response)


            except Exception as e:
                st.error(f"Erreur lors de l'envoi du message : {e}")
                # Retirer le dernier message utilisateur de l'historique si l'envoi échoue ?
                # Cela dépend de la gestion d'erreur souhaitée.

    # --- GESTION DE LA FIN DE SECTION ET DE L'ENTRETIEN ---

    # Colonnes pour les boutons d'action en bas
    col_action1, col_action2 = st.columns([3,1]) # Donne plus de place au bouton suivant

    with col_action1:
        # 👉 Bouton pour passer à la section suivante (affiché seulement si non terminé)
        if not st.session_state.interview_complete and st.session_state.interview_section < len(INTERVIEW_SECTIONS):
            if st.button(f"✅ Terminer la section {st.session_state.interview_section} et passer à la suivante", use_container_width=True):
                st.session_state.interview_section += 1
                # Pas besoin de relancer le chat ici, le prompt sera mis à jour au prochain rerun
                st.rerun()
        elif not st.session_state.interview_complete and st.session_state.interview_section == len(INTERVIEW_SECTIONS):
             if st.button("🏁 Terminer l'entretien", use_container_width=True):
                  st.session_state.interview_complete = True
                  # Supprimer le message système spécifique à la dernière section
                  if "current_system_prompt" in st.session_state:
                      del st.session_state.current_system_prompt
                  st.rerun()

    # 👉 Affichage des boutons de téléchargement (uniquement si l'entretien est terminé)
    if st.session_state.interview_complete:
        st.success("🎉 Entretien terminé ! Vous pouvez maintenant télécharger les rapports.")
        st.markdown("---")
        st.subheader("Téléchargement des Rapports")

        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            # Bouton pour l'historique brut
            if "chat" in st.session_state and st.session_state.chat.history:
                raw_history_md = export_conversation_as_markdown(st.session_state.chat.history)
                st.download_button(
                    label="📥 Télécharger l'Historique (.md)",
                    data=raw_history_md.encode("utf-8"),
                    file_name=f"historique_entretien_{datetime.date.today()}.md",
                    mime="text/markdown",
                    key="download_raw_history" # Clé unique
                )
            else:
                st.info("Aucun historique à télécharger.")

        with col_dl2:
             # Bouton pour le compte rendu structuré
            if "chat" in st.session_state and st.session_state.chat.history:
                # S'assurer que le modèle est disponible
                if "gemini_model" in st.session_state:
                    with st.spinner("Génération du compte rendu clinique..."):
                        # Utiliser la config définie par l'utilisateur pour la génération
                        clinical_summary_md = generate_clinical_summary(
                            st.session_state.chat.history,
                            st.session_state.gemini_model, # Utilise le même modèle que le chat
                            generation_config # Utilise la config définie plus haut
                        )

                    if "Erreur" in clinical_summary_md:
                         st.error(clinical_summary_md)
                    else:
                         st.download_button(
                             label="📥 Télécharger le Compte Rendu (.md)",
                             data=clinical_summary_md.encode("utf-8"),
                             file_name=f"compte_rendu_clinique_{datetime.date.today()}.md",
                             mime="text/markdown",
                             key="download_summary_report" # Clé unique différente
                         )
                else:
                    st.warning("Le modèle IA n'est pas initialisé, impossible de générer le compte rendu.")
            else:
                 st.info("Aucun historique disponible pour générer un compte rendu.")


    # 👉 Bouton pour réinitialiser l'entretien (toujours visible en bas ?)
    # On le met dans la deuxième colonne d'action
    with col_action2:
        if st.button("🔄 Réinitialiser", use_container_width=True):
            # Liste étendue des clés à potentiellement supprimer
            keys_to_reset = [
                "chat", "interview_section", "interview_complete",
                "gemini_model", "model_name", "current_system_prompt"
            ]
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            # Vider le cache de données et de ressources peut aussi être utile
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Entretien réinitialisé.")
            st.rerun()


except Exception as e:
    st.error(f"❌ Une erreur majeure est survenue : {e}")
    st.exception(e) # Affiche la trace complète pour le débogage