import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Stratégie Catégorielle CNO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONFIGURATION DES NOMS DE FICHIERS ---
# C'est ici que nous utilisons le nom exact trouvé dans votre liste :
NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"
TAILLE_LOGO = 400

# --- 3. FONCTION DE CHARGEMENT ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None
    
    try:
        # Lecture du CSV
        # header=1 signifie qu'on saute la 1ère ligne (Années) pour prendre la 2ème (Titres)
        # sep=None et engine='python' permet à Pandas de deviner le séparateur (, ou ;)
        df = pd.read_csv(NOM_FICHIER_DATA, header=1, sep=None, engine='python')

        # Renommage explicite des colonnes par position pour éviter les doublons
        # On s'assure qu'on a bien au moins 10 colonnes
        if len(df.columns) >= 10:
            df.columns = [
                "CLUSTER",             # 0
                "APPROVISIONNEMENT",   # 1
                "CA mini",             # 2
                "CA maxi",             # 3
                "NESTLE_2026",         # 4
                "LACTALIS_2026",       # 5
                "NUTRICIA_2026",       # 6
                "NESTLE_2025",         # 7
                "LACTALIS_2025",       # 8
                "NUTRICIA_2025"        # 9
            ] + list(df.columns[10:]) # On garde le reste s'il y en a

        # Nettoyage des chiffres (Conversion "NON ELIGIBLE" -> -1.0)
        cols_labos = ["NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026"]
        for col in cols_labos:
            if col in df.columns:
                # On force la conversion en nombre, les erreurs deviennent NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # On remplace les vides par -1.0
                df[col] = df[col].fillna(-1.0)
        
        return df

    except Exception as e:
        st.error(f"Erreur technique lors de la lecture : {e}")
        return None

# --- 4. INTERFACE PRINCIPALE ---
def main():
    
    # --- A. EN-TÊTE ---
    col_g, col_c, col_d = st.columns([1, 2, 1])
    with col_c:
        if os.path.exists(NOM_FICHIER_LOGO):
            st.image(NOM_FICHIER_LOGO, width=TAILLE_LOGO)
        else:
            st.warning("Logo non trouvé (ce n'est pas grave, l'appli continue)")

        st.markdown(
            """
            <h1 style='text-align: center; color: #2E4053; margin-top: -10px; margin-bottom: 30px;'>
                Stratégie Catégorielle CNO
            </h1>
            """, 
            unsafe_allow_html=True
        )

    st.markdown("---")

    # --- B. CHARGEMENT ---
    df = load_data()

    if df is None:
        st.error(f"⚠️ Le fichier '{NOM_FICHIER_DATA}' est introuvable.")
        st.info("Pourtant il apparait dans la liste. Essayez de redémarrer l'app (Reboot App) en haut à droite.")
        return 

    # --- C. FORMULAIRE ---
    st.subheader("🔎 Vos critères")
    
    col1, col2 = st.columns(2)
    with col1:
        # Liste des clusters
        valeurs_cluster = sorted(df['CLUSTER'].dropna().astype(str).unique())
        choix_cluster = st.selectbox("Votre Cluster", valeurs_cluster)
        
    with col2:
        # Liste des appros
        valeurs_appro = sorted(df['APPROVISIONNEMENT'].dropna().astype(str).unique())
        choix_appro = st.selectbox("Mode d'approvisionnement", valeurs_appro)

    ca_input = st.number_input(
        "Chiffre d'affaire prévisionnel (€)", 
        min_value=0.0, step=500.0, format="%.2f"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- D. ANALYSE ---
    if st.button("📊 Analyser la meilleure offre 2026", type="primary", use_container_width=True):
        
        # 1. Filtre Cluster/Appro
        mask_profil = (
            (df['CLUSTER'].astype(str) == choix_cluster) & 
            (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        )
        df_filtre = df[mask_profil]

        if df_filtre.empty:
            st.warning(f"Pas de données pour le profil : {choix_cluster} / {choix_appro}.")
        else:
            # 2. Filtre CA
            mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning("Montant CA hors des tranches définies dans le fichier.")
            else:
                row = resultat.iloc[0]
                
                # Mapping Labo -> Colonne
                labos_map = {
                    "NESTLE": "NESTLE_2026",
                    "LACTALIS": "LACTALIS_2026",
                    "NUTRICIA": "NUTRICIA_2026"
                }

                # Calcul des scores
                scores = {}
                for nom_affiche, nom_colonne in labos_map.items():
                    val = row.get(nom_colonne, -1.0)
                    scores[nom_affiche] = val

                gagnant = max(scores, key=scores.get)
                marge_gagnante = scores[gagnant]

                # --- E. RESULTATS ---
                st.markdown("---")
                st.subheader("🎯 Résultat de l'analyse")

                if marge_gagnante <= 0:
                    st.error("❌ Aucune offre éligible pour ce profil.")
                else:
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.success(f"✅ Meilleure stratégie : **{gagnant}**")
                    with c2:
                        st.metric("Marge estimée", f"{marge_gagnante:.2%}")

                    # Tableau
                    st.write("### Détail des offres")
                    data_disp = []
                    for nom_affiche, nom_colonne in labos_map.items():
                        val = row.get(nom_colonne, -1.0)
                        if val > 0:
                            data_disp.append({
                                "Laboratoire": nom_affiche, 
                                "Marge": f"{val:.2%}", 
                                "Statut": "✅ Eligible"
                            })
                        else:
                            data_disp.append({
                                "Laboratoire": nom_affiche, 
                                "Marge": "NON ELIGIBLE", 
                                "Statut": "❌"
                            })
                    
                    df_disp = pd.DataFrame(data_disp)
                    
                    # Style conditionnel
                    def highlight_winner(s):
                        est_gagnant = (s['Laboratoire'] == gagnant and marge_gagnante > 0)
                        return ['background-color: #d4edda; color: #155724; font-weight: bold' if est_gagnant else '' for _ in s]

                    st.dataframe(
                        df_disp.style.apply(highlight_winner, axis=1), 
                        use_container_width=True, 
                        hide_index=True
                    )

if __name__ == "__main__":
    main()
