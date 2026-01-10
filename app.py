import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION DE LA PAGE (Doit être la toute première commande) ---
st.set_page_config(
    page_title="Stratégie Catégorielle CNO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONFIGURATION DES NOMS DE FICHIERS ---
NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"
TAILLE_LOGO = 400

# --- 3. FONCTION DE CHARGEMENT ROBUSTE ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None
    
    # On teste les deux séparateurs possibles (Excel FR = ; / Excel US = ,)
    separateurs_a_tester = [';', ',']
    
    for sep in separateurs_a_tester:
        try:
            # On essaie de lire avec le séparateur courant + encoding latin-1
            df = pd.read_csv(
                NOM_FICHIER_DATA, 
                header=1, 
                sep=sep, 
                engine='python', 
                encoding='latin-1'
            )
            
            # Si le fichier a moins de 2 colonnes, c'est que le séparateur est mauvais
            if df.shape[1] < 2:
                continue

            # --- SI ON ARRIVE ICI, C'EST QUE LA LECTURE A MARCHÉ ---

            # 1. Renommage des colonnes (Sécurité index)
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
                ] + list(df.columns[10:])

            # 2. Nettoyage des chiffres (Gestion des virgules 0,12 vs 0.12)
            cols_labos = ["NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026"]
            for col in cols_labos:
                if col in df.columns:
                    # Si c'est du texte, on remplace la virgule par un point
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    
                    # Conversion en nombre
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    # Remplacement des erreurs/vides par -1.0
                    df[col] = df[col].fillna(-1.0)
            
            return df # On renvoie le DataFrame propre

        except Exception:
            continue # Si ça plante, on essaie le séparateur suivant

    # Si rien n'a marché après la boucle
    return None

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

    # --- B. CHARGEMENT ---
    df = load_data()

    if df is None:
        st.error(f"⚠️ Impossible de lire le fichier '{NOM_FICHIER_DATA}'.")
        st.warning("Vérifiez que le fichier n'est pas corrompu et qu'il est bien au format CSV (séparateur virgule ou point-virgule).")
        return 

    # --- C. FORMULAIRE ---
    st.subheader("🔎 Vos critères")
    
    col1, col2 = st.columns(2)
    with col1:
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

    # --- D. ANALYSE ---
    if st.button("📊 Analyser la meilleure offre 2026", type="primary", use_container_width=True):
        
        # Filtrage
        mask_profil = (
            (df['CLUSTER'].astype(str) == choix_cluster) & 
            (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        )
        df_filtre = df[mask_profil]

        if df_filtre.empty:
            st.warning(f"Pas de données pour le profil : {choix_cluster} / {choix_appro}.")
        else:
            mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning("Montant CA hors des tranches définies dans le fichier.")
            else:
                row = resultat.iloc[0]
                
                labos_map = {
                    "NESTLE": "NESTLE_2026",
                    "LACTALIS": "LACTALIS_2026",
                    "NUTRICIA": "NUTRICIA_2026"
                }

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
