import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Stratégie Catégorielle CNO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONFIGURATION (Images uniquement) ---
NOM_FICHIER_LOGO = "logo.png" 
TAILLE_LOGO = 400 

# --- 3. FONCTION INTELLIGENTE DE CHARGEMENT ---
@st.cache_data
def load_data_smart():
    # Liste des noms probables pour vous aider
    noms_possibles = [
        "data.csv", 
        "data.csv.csv", 
        "COMPARATIF CNO 2025 V10 (1).xlsx - MARGE PAR CLUSTERS CA.csv"
    ]
    
    fichier_trouve = None

    # Etape 1 : On cherche les noms exacts
    for nom in noms_possibles:
        if os.path.exists(nom):
            fichier_trouve = nom
            break
            
    # Etape 2 : Si pas trouvé, on cherche N'IMPORTE QUEL fichier CSV ou Excel dans le dossier
    if fichier_trouve is None:
        files = os.listdir()
        for f in files:
            if f.endswith(".csv") or f.endswith(".xlsx"):
                fichier_trouve = f
                break
    
    # Etape 3 : Chargement
    if fichier_trouve:
        try:
            # Détection automatique de l'extension pour choisir la bonne fonction de lecture
            if fichier_trouve.endswith(".csv"):
                # header=1 est important pour votre format spécifique
                df = pd.read_csv(fichier_trouve, header=1, sep=None, engine='python')
            else:
                df = pd.read_excel(fichier_trouve, header=1)
                
            # Affichage discret du fichier utilisé pour info
            st.toast(f"Fichier chargé : {fichier_trouve}", icon="📂")
            
            # --- NETTOYAGE (Standardisation des colonnes) ---
            # On renforce le nettoyage en prenant les colonnes par index (0, 1, 2...) 
            # peu importe leurs noms
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
                ] + list(df.columns[10:]) # On garde le reste si ça existe
            
            # Nettoyage des chiffres
            cols_labos = ["NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026"]
            for col in cols_labos:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1.0)
            
            return df, fichier_trouve

        except Exception as e:
            st.error(f"Erreur de lecture du fichier '{fichier_trouve}': {e}")
            return None, None
    else:
        return None, None

# --- 4. INTERFACE PRINCIPALE ---
def main():
    
    # --- A. EN-TÊTE ---
    col_g, col_c, col_d = st.columns([1, 2, 1])
    with col_c:
        if os.path.exists(NOM_FICHIER_LOGO):
            st.image(NOM_FICHIER_LOGO, width=TAILLE_LOGO)
        
        st.markdown(
            """
            <h1 style='text-align: center; color: #2E4053; margin-top: -10px; margin-bottom: 30px;'>
                Stratégie Catégorielle CNO
            </h1>
            """, 
            unsafe_allow_html=True
        )

    st.markdown("---")

    # --- B. CHARGEMENT AUTOMATIQUE ---
    df, nom_fichier = load_data_smart()

    if df is None:
        # Si VRAIMENT aucun fichier n'est trouvé, on affiche le contenu du dossier pour débugger
        st.error("⚠️ AUCUN FICHIER DE DONNÉES TROUVÉ.")
        st.warning("Voici la liste des fichiers présents dans le dossier :")
        st.code(os.listdir())
        st.info("Copiez le nom exact d'un fichier .csv ci-dessus et renommez votre fichier sur l'ordinateur.")
        return 

    # --- C. FORMULAIRE ---
    st.subheader("🔎 Vos critères")
    
    col1, col2 = st.columns(2)
    with col1:
        # Tri et nettoyage des valeurs uniques
        valeurs_cluster = sorted(df['CLUSTER'].dropna().astype(str).unique())
        choix_cluster = st.selectbox("Votre Cluster", valeurs_cluster)
        
    with col2:
        valeurs_appro = sorted(df['APPROVISIONNEMENT'].dropna().astype(str).unique())
        choix_appro = st.selectbox("Mode d'approvisionnement", valeurs_appro)

    ca_input = st.number_input(
        "Chiffre d'affaire prévisionnel (€)", 
        min_value=0.0, step=500.0, format="%.2f"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📊 Analyser la meilleure offre 2026", type="primary", use_container_width=True):
        
        # --- D. CALCUL ---
        mask_profil = (
            (df['CLUSTER'].astype(str) == choix_cluster) & 
            (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        )
        df_filtre = df[mask_profil]

        if df_filtre.empty:
            st.warning(f"Pas de données pour {choix_cluster} / {choix_appro}.")
        else:
            mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning("Montant CA hors tranches.")
            else:
                row = resultat.iloc[0]
                
                labos_map = {
                    "NESTLE": "NESTLE_2026",
                    "LACTALIS": "LACTALIS_2026",
                    "NUTRICIA": "NUTRICIA_2026"
                }

                scores = {}
                for k, v in labos_map.items():
                    if v in row: # Sécurité si colonne manquante
                        scores[k] = row[v]
                    else:
                        scores[k] = -1.0

                gagnant = max(scores, key=scores.get)
                marge_gagnante = scores[gagnant]

                # --- E. AFFICHAGE ---
                st.markdown("---")
                st.subheader("🎯 Résultat de l'analyse")

                if marge_gagnante <= 0:
                    st.error("❌ Aucune offre éligible.")
                else:
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.success(f"✅ Meilleure stratégie : **{gagnant}**")
                    with c2:
                        st.metric("Marge estimée", f"{marge_gagnante:.2%}")

                    st.write("### Détail des offres")
                    data_disp = []
                    for k, v in labos_map.items():
                        val = row.get(v, -1.0)
                        if val > 0:
                            data_disp.append({"Labo": k, "Marge": f"{val:.2%}", "Statut": "✅ Eligible"})
                        else:
                            data_disp.append({"Labo": k, "Marge": "NON ELIGIBLE", "Statut": "❌"})
                    
                    df_disp = pd.DataFrame(data_disp)
                    
                    def color(s):
                        return ['background-color: #d4edda' if s['Labo'] == gagnant else '' for _ in s]

                    st.dataframe(df_disp.style.apply(color, axis=1), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
