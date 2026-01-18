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
    
    # Lecture (Excel ou CSV)
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

    # Nettoyage des données
    if df is not None:
        try:
            # 1. Renommage des colonnes (V12)
            if len(df.columns) >= 12:
                df.columns = [
                    "CLUSTER",             # 0
                    "APPROVISIONNEMENT",   # 1
                    "CA mini",             # 2
                    "CA maxi",             # 3
                    "NESTLE_2026",         # 4
                    "LACTALIS_2026",       # 5
                    "NUTRICIA_2026",       # 6
                    "FRESENIUS_2026",      # 7
                    "NESTLE_2025",         # 8
                    "LACTALIS_2025",       # 9
                    "NUTRICIA_2025",       # 10
                    "FRESENIUS_2025"       # 11
                ] + list(df.columns[12:])

            # 2. NETTOYAGE CRITIQUE DES TEXTES (Cluster/Appro)
            # On enlève les espaces invisibles pour être sûr que "Direct " devienne "Direct"
            df['CLUSTER'] = df['CLUSTER'].astype(str).str.strip()
            df['APPROVISIONNEMENT'] = df['APPROVISIONNEMENT'].astype(str).str.strip()

            # 3. Nettoyage des taux (Gestion du 12%)
            cols_to_clean = [
                "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026", "FRESENIUS_2026",
                "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025", "FRESENIUS_2025"
            ]
            
            for col in cols_to_clean:
                if col in df.columns:
                    # Conversion texte
                    df[col] = df[col].astype(str)
                    # Virgule -> Point
                    df[col] = df[col].str.replace(',', '.', regex=False)
                    
                    # Remplacement "NON ELIGIBLE" par 0.12 (12%)
                    # On utilise une recherche flexible (maj/min)
                    mask_non = df[col].str.upper().str.contains("NON ELIGIBLE", na=False)
                    df.loc[mask_non, col] = "0.12"

                    # Conversion numérique
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            return df
        except Exception as e:
            st.error(f"Erreur lors du nettoyage : {e}")
            return None
    return None

# --- 4. INTERFACE ---
def main():
    
    # CSS Logo centré
    st.markdown(
        """
        <style>
            [data-testid="stImage"] { display: block; margin-left: auto; margin-right: auto; }
        </style>
        """,
        unsafe_allow_html=True
    )

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
        st.error("❌ Erreur technique : Fichier 'data.csv' introuvable.")
        return 

    # --- FORMULAIRE 1 : SÉLECTION DU PROFIL ---
    st.subheader("1️⃣ Choix du Cluster et de l'Approvisionnement")
    
    col_choix1, col_choix2 = st.columns(2)
    
    with col_choix1:
        # On récupère les choix possibles directement depuis le fichier nettoyé
        # Cela garantit que le choix correspondra bien à une ligne du fichier
        choix_possibles_cluster = sorted(df['CLUSTER'].unique())
        choix_cluster = st.selectbox("Votre Cluster", choix_possibles_cluster)
        
    with col_choix2:
        choix_possibles_appro = sorted(df['APPROVISIONNEMENT'].unique())
        choix_appro = st.selectbox("Mode d'Approvisionnement", choix_possibles_appro)

    st.markdown("---")

    # --- FORMULAIRE 2 : SAISIE DES CA ---
    st.subheader("2️⃣ Répartition des Achats 2025")
    st.write("Indiquez vos volumes d'achats pour chaque laboratoire (pour calculer votre moyenne actuelle).")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ca_nestle = st.number_input("CA Nestle (€)", min_value=0.0, step=100.0)
    with c2:
        ca_lactalis = st.number_input("CA Lactalis (€)", min_value=0.0, step=100.0)
    with c3:
        ca_nutricia = st.number_input("CA Nutricia (€)", min_value=0.0, step=100.0)
    with c4:
        ca_fresenius = st.number_input("CA Fresenius (€)", min_value=0.0, step=100.0)

    total_ca_2025 = ca_nestle + ca_lactalis + ca_nutricia + ca_fresenius
    
    if total_ca_2025 > 0:
        st.success(f"💰 Chiffre d'Affaires Total 2025 : **{total_ca_2025:,.2f} €**")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- BOUTON ANALYSE ---
    if st.button("📊 Analyser la performance", type="primary", use_container_width=True):
        
        if total_ca_2025 == 0:
            st.warning("Veuillez saisir au moins un montant de CA.")
            return

        # 1. FILTRAGE : On applique les choix de l'utilisateur
        mask_profil = (df['CLUSTER'] == choix_cluster) & (df['APPROVISIONNEMENT'] == choix_appro)
        df_filtre = df[mask_profil]

        if df_filtre.empty:
            st.error(f"Aucune donnée trouvée pour le couple : {choix_cluster} / {choix_appro}")
        else:
            # 2. RECHERCHE TRANCHE CA
            mask_ca = (df_filtre['CA mini'] <= total_ca_2025) & (df_filtre['CA maxi'] >= total_ca_2025)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning(f"Le CA Total ({total_ca_2025:,.0f} €) ne rentre dans aucune tranche (Min/Max) du fichier.")
            else:
                row = resultat.iloc[0]

                # --- CALCULS ---

                # A. Moyenne 2025 (Pondérée)
                # Note: les "Non Eligible" valent 0.12 grâce au nettoyage
                r_n25 = row.get("NESTLE_2025", 0.0)
                r_l25 = row.get("LACTALIS_2025", 0.0)
                r_u25 = row.get("NUTRICIA_2025", 0.0)
                r_f25 = row.get("FRESENIUS_2025", 0.0)

                marge_eur_2025 = (ca_nestle*r_n25) + (ca_lactalis*r_l25) + (ca_nutricia*r_u25) + (ca_fresenius*r_f25)
                taux_moyen_2025 = marge_eur_2025 / total_ca_2025

                # B. Stratégie 2026 (70% Best / 30% 2nd - Entre Nestle et Nutricia)
                r_n26 = row.get("NESTLE_2026", 0.0)
                r_u26 = row.get("NUTRICIA_2026", 0.0)

                if r_n26 >= r_u26:
                    winner, loser = "NESTLE", "NUTRICIA"
                    t_win, t_lose = r_n26, r_u26
                else:
                    winner, loser = "NUTRICIA", "NESTLE"
                    t_win, t_lose = r_u26, r_n26
                
                taux_strategie_2026 = (0.7 * t_win) + (0.3 * t_lose)

                # C. Gain
                diff_taux = taux_strategie_2026 - taux_moyen_2025
                gain_10k = diff_taux * 10000

                # --- AFFICHAGE RESULTATS ---
                st.markdown("---")
                col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

                with col_kpi1:
                    st.info("🔙 Historique 2025")
                    st.metric("Marge Moyenne", f"{taux_moyen_2025:.2%}")
                    st.caption("Calculé sur vos 4 fournisseurs.")

                with col_kpi2:
                    st.info("🎯 Projection 2026")
                    st.write(f"**70% {winner}** / 30% {loser}")
                    st.metric("Nouveau Taux Mixte", f"{taux_strategie_2026:.2%}")

                with col_kpi3:
                    if diff_taux > 0:
                        st.success("🚀 Gain de Marge")
                        st.metric("Gain / 10k€ de Vente", f"+ {gain_10k:,.2f} €")
                        st.write(f"Évolution : **+{diff_taux:.2%}**")
                    elif diff_taux == 0:
                        st.warning("⚖️ Stable")
                        st.metric("Gain / 10k€ de Vente", "0 €")
                    else:
                        st.error("📉 Perte")
                        st.metric("Perte / 10k€ de Vente", f"{gain_10k:,.2f} €")
                        st.write(f"Évolution : **{diff_taux:.2%}**")

if __name__ == "__main__":
    main()
