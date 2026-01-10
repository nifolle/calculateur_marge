import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Stratégie Catégorielle CNO",
    layout="wide", # "wide" permet de mieux centrer les éléments avec des colonnes
    initial_sidebar_state="expanded"
)

# --- 2. VARIABLES DE CONFIGURATION ---
# Mettez ici le nom EXACT de votre fichier de données
# J'ai mis un nom simple, renommez votre fichier excel/csv en 'data.csv' pour faire simple
NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png" 
TAILLE_LOGO = 400 # Taille réduite (environ 70% d'un affichage standard)

# --- 3. FONCTION DE CHARGEMENT ET NETTOYAGE ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None
    
    try:
        # Lecture du CSV
        # header=1 est CRUCIAL car la ligne 1 contient les années, la ligne 2 les titres
        df = pd.read_csv(NOM_FICHIER_DATA, header=1, sep=",")
        
        # Renommage explicite des colonnes pour éviter les confusions (NESTLE vs NESTLE.1)
        # On map les colonnes par leur position (index)
        df.columns = [
            "CLUSTER",             # 0
            "APPROVISIONNEMENT",   # 1
            "CA mini",             # 2
            "CA maxi",             # 3
            "NESTLE_2026",         # 4
            "LACTALIS_2026",       # 5
            "NUTRICIA_2026",       # 6
            "NESTLE_2025",         # 7 (Ignoré pour le calcul actuel)
            "LACTALIS_2025",       # 8
            "NUTRICIA_2025"        # 9
        ]
        
        # Nettoyage des colonnes numériques (2026)
        cols_labos = ["NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026"]
        
        for col in cols_labos:
            # Convertit "NON ELIGIBLE" en NaN (vide), et les chiffres en float
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Remplace les vides par -1.0 (pour indiquer clairement que c'est perdu)
            df[col] = df[col].fillna(-1.0)
            
        return df

    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
        return None

# --- 4. INTERFACE PRINCIPALE ---
def main():
    
    # --- A. EN-TÊTE (LOGO + TITRE CENTRÉS) ---
    col_g, col_c, col_d = st.columns([1, 2, 1])
    with col_c:
        # Affichage du Logo
        if os.path.exists(NOM_FICHIER_LOGO):
            st.image(NOM_FICHIER_LOGO, width=TAILLE_LOGO)
        else:
            st.warning(f"Logo introuvable : {NOM_FICHIER_LOGO}")

        # Affichage du Titre centré en HTML
        st.markdown(
            """
            <h1 style='text-align: center; color: #2E4053; margin-top: -10px; margin-bottom: 30px;'>
                Stratégie Catégorielle CNO
            </h1>
            """, 
            unsafe_allow_html=True
        )

    st.markdown("---")

    # --- B. CHARGEMENT DES DONNÉES ---
    df = load_data()

    if df is None:
        st.error("⚠️ Fichier de données introuvable. Vérifiez le nom du fichier dans le code.")
        return # On arrête le script ici si pas de données

    # --- C. FORMULAIRE UTILISATEUR ---
    st.subheader("🔎 Vos critères")
    
    col1, col2 = st.columns(2)
    with col1:
        # On récupère la liste unique des clusters
        liste_clusters = sorted(df['CLUSTER'].dropna().astype(str).unique())
        choix_cluster = st.selectbox("Votre Cluster", liste_clusters)
        
    with col2:
        # On récupère la liste unique des approvisionnements
        liste_appro = sorted(df['APPROVISIONNEMENT'].dropna().astype(str).unique())
        choix_appro = st.selectbox("Mode d'approvisionnement", liste_appro)

    # Input CA
    ca_input = st.number_input(
        "Chiffre d'affaire prévisionnel (€)", 
        min_value=0.0, 
        step=500.0, 
        format="%.2f"
    )

    st.markdown("<br>", unsafe_allow_html=True) # Petit espace

    # Bouton d'action
    if st.button("📊 Analyser la meilleure offre 2026", type="primary", use_container_width=True):
        
        # --- D. LOGIQUE DE CALCUL ---
        
        # 1. Filtrage Cluster + Appro
        mask_profil = (
            (df['CLUSTER'].astype(str) == choix_cluster) & 
            (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        )
        df_filtre = df[mask_profil]

        if df_filtre.empty:
            st.warning(f"Aucune donnée trouvée pour {choix_cluster} en {choix_appro}.")
        else:
            # 2. Filtrage par CA (Entre Min et Max)
            mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning("Montant hors des tranches prévues (CA trop haut ou trop bas).")
            else:
                # On prend la ligne correspondante
                row = resultat.iloc[0]

                # Dictionnaire pour comparer les scores
                # On map : Nom Affiché -> Nom de la colonne technique
                labos_map = {
                    "NESTLE": "NESTLE_2026",
                    "LACTALIS": "LACTALIS_2026",
                    "NUTRICIA": "NUTRICIA_2026"
                }

                scores = {}
                for nom_affiche, nom_colonne in labos_map.items():
                    valeur = row[nom_colonne]
                    # Si valeur > 0, c'est une marge valide. Si -1.0, c'est non éligible.
                    scores[nom_affiche] = valeur

                # Trouver le gagnant (la valeur max)
                gagnant = max(scores, key=scores.get)
                marge_gagnante = scores[gagnant]

                # --- E. AFFICHAGE DES RÉSULTATS ---
                st.markdown("---")
                st.subheader("🎯 Résultat de l'analyse")

                if marge_gagnante <= 0:
                    st.error("❌ Aucune offre éligible pour ce profil (Toutes les offres sont marquées 'NON ELIGIBLE').")
                else:
                    col_res1, col_res2 = st.columns([2, 1])
                    
                    with col_res1:
                        st.success(f"✅ La meilleure stratégie est : **{gagnant}**")
                    with col_res2:
                        st.metric("Marge estimée", f"{marge_gagnante:.2%}")

                    # --- TABLEAU COMPARATIF ---
                    st.write("### Détail des offres")

                    data_display = []
                    for nom_affiche, nom_colonne in labos_map.items():
                        val_brute = row[nom_colonne]
                        
                        if val_brute > 0:
                            txt_marge = f"{val_brute:.2%}"
                            statut = "🏆 Meilleure offre" if nom_affiche == gagnant else "✅ Eligible"
                        else:
                            txt_marge = "NON ELIGIBLE"
                            statut = "❌ Non éligible"

                        data_display.append({
                            "Laboratoire": nom_affiche,
                            "Marge": txt_marge,
                            "Statut": statut
                        })

                    df_display = pd.DataFrame(data_display)

                    # Application du style (Surligner le gagnant en vert)
                    def colorer_ligne(s):
                        est_gagnant = s['Laboratoire'] == gagnant and marge_gagnante > 0
                        return ['background-color: #d4edda; color: #155724; font-weight: bold' if est_gagnant else '' for _ in s]

                    st.dataframe(
                        df_display.style.apply(colorer_ligne, axis=1),
                        use_container_width=True,
                        hide_index=True
                    )

if __name__ == "__main__":
    main()
