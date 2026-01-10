import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Stratégie catégorielle CNO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. VARIABLES ---
NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"
TAILLE_LOGO = 350

# --- 3. FONCTION DE CHARGEMENT ET NETTOYAGE ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None

    df = None
    
    # Lecture (Tentative Excel puis CSV)
    try:
        df = pd.read_excel(NOM_FICHIER_DATA, header=1, engine='openpyxl')
    except:
        pass

    if df is None:
        separateurs = [';', ',']
        for sep in separateurs:
            try:
                df_temp = pd.read_csv(
                    NOM_FICHIER_DATA, header=1, sep=sep, engine='python', encoding='latin-1'
                )
                if df_temp.shape[1] > 2:
                    df = df_temp
                    break
            except:
                continue

    # Nettoyage
    if df is not None:
        try:
            # 1. Renommage des colonnes (On inclut bien 2025 et 2026)
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

            # 2. Conversion en chiffres pour TOUTES les colonnes (2025 et 2026)
            # C'est important pour pouvoir lire votre historique 2025
            cols_to_clean = [
                "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026",
                "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025"
            ]
            
            for col in cols_to_clean:
                if col in df.columns:
                    # Gestion virgule/point
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    # Conversion (les erreurs deviennent NaN puis -1.0)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1.0)
            return df
        except:
            return None
    return None

# --- 4. INTERFACE ---
def main():
    
    # --- EN-TÊTE ---
    col_g, col_c, col_d = st.columns([1, 2, 1])
    with col_c:
        if os.path.exists(NOM_FICHIER_LOGO):
            st.image(NOM_FICHIER_LOGO, width=TAILLE_LOGO)
        
        st.markdown(
            """
            <h1 style='text-align: center; color: #2E4053; margin-top: -10px; margin-bottom: 30px;'>
                Stratégie catégorielle CNO
            </h1>
            """, 
            unsafe_allow_html=True
        )

    st.markdown("---")

    df = load_data()
    if df is None:
        st.error("❌ Erreur technique : Fichier de données introuvable.")
        return 

    # --- FORMULAIRE ---
    st.subheader("🔎 Vos critères")
    
    c1, c2 = st.columns(2)
    with c1:
        valeurs_cluster = sorted(df['CLUSTER'].dropna().astype(str).unique())
        choix_cluster = st.selectbox("Votre Cluster", valeurs_cluster)
    with c2:
        valeurs_appro = sorted(df['APPROVISIONNEMENT'].dropna().astype(str).unique())
        choix_appro = st.selectbox("Mode d'approvisionnement", valeurs_appro)

    c3, c4 = st.columns(2)
    with c3:
        # Modification du titre comme demandé
        liste_fournisseurs = ["NESTLE", "LACTALIS", "NUTRICIA", "AUTRE/GROSSISTE"]
        choix_2025 = st.selectbox("Fournisseur 2025", liste_fournisseurs)
    with c4:
        # Modification du titre comme demandé
        ca_input = st.number_input(
            "Chiffre d'affaires avec fournisseur 2025 (€)", 
            min_value=0.0, step=500.0, format="%.2f"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- CALCUL ---
    if st.button("📊 Calculer le gain de marge", type="primary", use_container_width=True):
        
        # 1. Trouver la bonne ligne (Cluster + Appro + CA)
        mask = (df['CLUSTER'].astype(str) == choix_cluster) & (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        df_filtre = df[mask]

        if df_filtre.empty:
            st.warning("Profil introuvable.")
        else:
            mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning("Montant CA hors tranches.")
            else:
                row = resultat.iloc[0]
                
                # --- A. Analyse 2026 (Le Futur) ---
                map_2026 = {
                    "NESTLE": "NESTLE_2026",
                    "LACTALIS": "LACTALIS_2026",
                    "NUTRICIA": "NUTRICIA_2026"
                }
                # On cherche le meilleur taux parmi les 3 colonnes 2026
                scores_2026 = {nom: row.get(col, -1.0) for nom, col in map_2026.items()}
                gagnant_2026 = max(scores_2026, key=scores_2026.get)
                taux_gagnant_2026 = scores_2026[gagnant_2026]

                # --- B. Analyse 2025 (Le Passé) ---
                # On cherche le taux que vous aviez en 2025 selon votre sélection
                map_2025 = {
                    "NESTLE": "NESTLE_2025",
                    "LACTALIS": "LACTALIS_2025",
                    "NUTRICIA": "NUTRICIA_2025"
                }
                
                taux_2025 = 0.0
                if choix_2025 in map_2025:
                    col_2025 = map_2025[choix_2025]
                    val_2025 = row.get(col_2025, -1.0)
                    if val_2025 > 0:
                        taux_2025 = val_2025
                    else:
                        taux_2025 = 0.0 # Si non éligible en 2025, on considère 0%
                else:
                    taux_2025 = 0.0 # Grossiste ou Autre

                # --- C. Calcul du Gain ---
                # Différence de marge * CA
                diff_taux = taux_gagnant_2026 - taux_2025
                gain_euros = diff_taux * ca_input

                # --- D. Affichage ---
                st.markdown("---")
                
                if taux_gagnant_2026 <= 0:
                    st.error("❌ Aucune offre éligible pour 2026.")
                else:
                    # Affichage simplifié en gros indicateurs
                    kpi1, kpi2, kpi3 = st.columns(3)

                    with kpi1:
                        st.info("🏆 Meilleure offre 2026")
                        st.metric("Laboratoire", gagnant_2026)
                        st.write(f"Taux : **{taux_gagnant_2026:.2%}**")
                    
                    with kpi2:
                        st.info(f"🔙 Votre historique {choix_2025}")
                        st.metric("Comparatif", "Année 2025")
                        st.write(f"Taux : **{taux_2025:.2%}**")

                    with kpi3:
                        if gain_euros > 0:
                            st.success("💰 Gain de marge estimé")
                            st.metric("Gain", f"+ {gain_euros:,.2f} €")
                        elif gain_euros == 0:
                            st.warning("⚖️ Maintien de marge")
                            st.metric("Différence", "0 €")
                        else:
                            st.error("📉 Perte de marge")
                            st.metric("Perte", f"{gain_euros:,.2f} €")

if __name__ == "__main__":
    main()
