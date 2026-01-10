import streamlit as st
import pandas as pd
import os
from PIL import Image

# --- CONFIGURATION DES FICHIERS SUR GITHUB ---
# Assurez-vous que ces noms sont EXACTEMENT les mêmes que sur GitHub
NOM_FICHIER_EXCEL = 'COMPARATIF CNO 2025 V10.xlsx'
NOM_FICHIER_LOGO = 'logo.png' # Remplacez par .jpg si votre logo est un jpg

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Strategie catégorielle CNO", 
    layout="centered"
    # Nous n'utilisons plus l'icône 💊 car nous avons un vrai logo maintenant
)

# --- FONCTION DE CHARGEMENT DES DONNÉES (Mise en cache) ---
@st.cache_data
def charger_donnees():
    if not os.path.exists(NOM_FICHIER_EXCEL):
        return None
    try:
        # On lit le fichier
        df = pd.read_excel(NOM_FICHIER_EXCEL)
        # Nettoyage des noms de colonnes (supprime les espaces invisibles avant/après)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erreur technique lors de la lecture du fichier Excel : {e}")
        return None

# --- DÉBUT DE L'INTERFACE UTILISATEUR ---

# 1. Affichage du Logo et du Titre
# On vérifie si le logo existe pour éviter une erreur laide si vous oubliez de l'uploader
if os.path.exists(NOM_FICHIER_LOGO):
    try:
        image = Image.open(NOM_FICHIER_LOGO)
        # On affiche le logo centré, avec une largeur raisonnable
        col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
        with col_logo2:
             st.image(image, use_column_width=True)
    except Exception as e:
        st.warning(f"Impossible de charger le logo : {e}")
else:
    # Si pas de logo, on laisse un petit espace
    st.write("")

st.title("Strategie catégorielle CNO")
st.markdown("---")

# 2. Chargement des données
df = charger_donnees()

if df is None:
    st.error(f"⚠️ Le fichier Excel '{NOM_FICHIER_EXCEL}' est introuvable sur GitHub.")
    st.info("Vérifiez que vous avez bien uploadé le fichier V10 avec le nom exact.")
else:
    # --- FORMULAIRE DE SAISIE ---
    st.subheader("Vos critères")

    # On utilise 2 colonnes pour les listes principales
    col1, col2 = st.columns(2)
    
    with col1:
        # Liste déroulante Cluster
        # On convertit en texte pour être sûr, on prend les valeurs uniques et on trie
        liste_clusters = sorted(df['CLUSTER'].dropna().unique().astype(str))
        choix_cluster = st.selectbox("Votre Cluster", liste_clusters)
        
    with col2:
        # Liste déroulante Appro
        liste_appro = sorted(df['APPROVISIONNEMENT'].dropna().unique().astype(str))
        choix_appro = st.selectbox("Mode d'approvisionnement actuel", liste_appro)

    # --- NOUVEAU CHAMP : Fournisseur N-1 ---
    # Je définis une liste standard. Si cette liste doit aussi venir d'Excel, dites-le moi.
    liste_fournisseurs_n1 = ['NESTLE', 'LACTALIS', 'NUTRICIA', 'AUTRE/GROSSISTE']
    choix_n1 = st.selectbox("Fournisseur N-1 (Année précédente)", liste_fournisseurs_n1)
        
    # --- CHAMP MODIFIÉ : Saisie CA ---
    # Changement du libellé comme demandé
    ca_input = st.number_input("Chiffre d'affaire avec fournisseur N-1 (€)", min_value=0.0, step=500.0, format="%.2f")
    st.markdown("---")

    # Bouton de validation (en bleu avec type="primary")
    if st.button("📊 Analyser la meilleure stratégie", type="primary", use_container_width=True):
        
        # --- LOGIQUE DE FILTRAGE (Inchangée) ---
        
        # 1. On filtre par Cluster et Appro
        mask_profil = (df['CLUSTER'].astype(str) == choix_cluster) & (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        df_filtre = df[mask_profil]
        
        if df_filtre.empty:
             st.warning(f"Attention : La combinaison Cluster '{choix_cluster}' et Approvisionnement '{choix_appro}' ne semble pas exister dans le fichier.")
        else:
            # 2. On cherche la tranche de CA
            # La condition est : CA mini <= Votre CA <= CA maxi
            mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning("❌ Aucune offre trouvée pour ce montant de Chiffre d'Affaires.")
                st.write("Vérifiez que le montant saisi correspond aux tranches de CA du fichier (CA mini / CA maxi).")
            else:
                # On prend la première ligne qui correspond (il ne devrait y en avoir qu'une)
                row = resultat.iloc[0]
                
                # --- COMPARAISON DES MARGES ---
                fournisseurs_a_comparer = ['NESTLE', 'LACTALIS', 'NUTRICIA']
                scores = {}
                
                for f in fournisseurs_a_comparer:
                    # On récupère la valeur dans la colonne du fournisseur
                    val = row.get(f) # .get est plus sûr si une colonne manque
                    
                    # Si c'est un chiffre (int ou float), c'est une marge valide
                    if isinstance(val, (int, float)) and not pd.isna(val):
                        scores[f] = val
                    # Sinon (ex: "NON ELIGIBLE", ou case vide), on met un score négatif pour l'exclure
                    else:
                        scores[f] = -1.0
                
                # Qui est le meilleur ? (Celui avec le score le plus élevé)
                gagnant = max(scores, key=scores.get)
                marge_max = scores[gagnant]

                # --- AFFICHAGE DU RÉSULTAT ---
                st.subheader("Résultat de l'analyse")

                if marge_max == -1.0:
                    st.error("Selon le fichier actuel, vous n'êtes éligible à aucune offre directe (Mention 'NON ELIGIBLE' pour les 3 fournisseurs).")
                else:
                    # Affichage du gagnant
                    st.success(f"✅ La stratégie recommandée est : **{gagnant}**")
                    st.metric("Marge potentielle 2025/2026", f"{marge_max:.2%}")
                    
                    # Petit rappel du contexte (facultatif, mais utile pour l'utilisateur)
                    st.caption(f"Basé sur un cluster {choix_cluster}, en {choix_appro}, avec un historique chez {choix_n1}.")
                    
                    # --- Tableau comparatif propre ---
                    st.subheader("Détail des comparatifs")
                    
                    data_display = []
                    for f in fournisseurs_a_comparer:
                        raw_val = row.get(f)
                        # Formatage joli (pourcentage ou texte brut)
                        if isinstance(raw_val, (int, float)) and not pd.isna(raw_val):
                            txt_val = f"{raw_val:.2%}"
                            statut = "⭐ Meilleure offre" if f == gagnant else "Alternative"
                        else:
                            # Si c'est du texte (NON ELIGIBLE) ou vide (nan)
                            txt_val = str(raw_val) if not pd.isna(raw_val) else "Non renseigné"
                            statut = "Non éligible"
                        
                        data_display.append({
                            "Laboratoire": f,
                            "Condition / Marge": txt_val,
                            "Statut": statut
                        })
                    
                    # Création d'un DataFrame pour l'affichage et style pour mettre en avant le gagnant
                    df_display = pd.DataFrame(data_display)
                    
                    # Fonction simple pour colorer la ligne du gagnant
                    def highlight_winner(s):
                        return ['background-color: #d4edda' if s['Laboratoire'] == gagnant else '' for _ in s]

                    st.dataframe(
                        df_display.style.apply(highlight_winner, axis=1), 
                        hide_index=True,
                        use_container_width=True
                    )
                st.dataframe(pd.DataFrame(data_display), hide_index=True)
