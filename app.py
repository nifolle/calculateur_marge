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

# --- 3. FONCTION DE CHARGEMENT ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None

    df = None
    
    # Lecture Hybride (Excel ou CSV)
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

    # Nettoyage et Renommage des colonnes
    if df is not None:
        try:
            # On s'assure d'avoir assez de colonnes pour les 4 laboratoires sur 2 années
            # Structure attendue : Cluster, Appro, Min, Max, N26, L26, U26, F26, N25, L25, U25, F25
            if len(df.columns) >= 12:
                df.columns = [
                    "CLUSTER",             # 0
                    "APPROVISIONNEMENT",   # 1
                    "CA mini",             # 2
                    "CA maxi",             # 3
                    "NESTLE_2026",         # 4
                    "LACTALIS_2026",       # 5
                    "NUTRICIA_2026",       # 6
                    "FRESENIUS_2026",      # 7 (Nouveau)
                    "NESTLE_2025",         # 8
                    "LACTALIS_2025",       # 9
                    "NUTRICIA_2025",       # 10
                    "FRESENIUS_2025"       # 11 (Nouveau)
                ] + list(df.columns[12:])

            # Liste complète des colonnes à nettoyer
            cols_to_clean = [
                "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026", "FRESENIUS_2026",
                "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025", "FRESENIUS_2025"
            ]
            
            for col in cols_to_clean:
                if col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    # Les "NON ELIGIBLE" deviennent -1.0
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1.0)
            return df
        except:
            return None
    return None

# --- 4. INTERFACE ---
def main():
    
    # CSS centrage logo
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
        st.error("❌ Erreur technique : Fichier introuvable ou format incorrect.")
        return 

    # --- FORMULAIRE ---
    st.subheader("🔎 Répartition de votre Chiffre d'Affaires 2025")
    
    # Choix Cluster / Appro
    c_clust, c_appro = st.columns(2)
    with c_clust:
        valeurs_cluster = sorted(df['CLUSTER'].dropna().astype(str).unique())
        choix_cluster = st.selectbox("Votre Cluster", valeurs_cluster)
    with c_appro:
        valeurs_appro = sorted(df['APPROVISIONNEMENT'].dropna().astype(str).unique())
        choix_appro = st.selectbox("Mode d'approvisionnement", valeurs_appro)

    st.write("Veuillez saisir vos volumes d'achats 2025 par laboratoire :")

    # 4 Inputs pour les CA
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ca_nestle = st.number_input("CA Nestle 2025 (€)", min_value=0.0, step=100.0)
    with col2:
        ca_lactalis = st.number_input("CA Lactalis 2025 (€)", min_value=0.0, step=100.0)
    with col3:
        ca_nutricia = st.number_input("CA Nutricia 2025 (€)", min_value=0.0, step=100.0)
    with col4:
        ca_fresenius = st.number_input("CA Fresenius 2025 (€)", min_value=0.0, step=100.0)

    # Calcul du CA Total instantané
    total_ca_2025 = ca_nestle + ca_lactalis + ca_nutricia + ca_fresenius
    if total_ca_2025 > 0:
        st.info(f"💰 Chiffre d'Affaires Total 2025 pris en compte : **{total_ca_2025:,.2f} €**")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- CALCUL ---
    if st.button("📊 Lancer l'analyse et la projection 2026", type="primary", use_container_width=True):
        
        if total_ca_2025 == 0:
            st.warning("Veuillez saisir au moins un chiffre d'affaires.")
            return

        # 1. Récupération de la ligne (Basé sur le CA TOTAL)
        mask = (df['CLUSTER'].astype(str) == choix_cluster) & (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        df_filtre = df[mask]

        if df_filtre.empty:
            st.warning("Profil Cluster/Appro introuvable.")
        else:
            # On cherche la tranche correspondant au CA TOTAL
            mask_ca = (df_filtre['CA mini'] <= total_ca_2025) & (df_filtre['CA maxi'] >= total_ca_2025)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning(f"Le CA Total ({total_ca_2025}€) ne correspond à aucune tranche dans le fichier.")
            else:
                row = resultat.iloc[0]

                # --- A. CALCUL MARGE MOYENNE 2025 (Pondérée) ---
                # On récupère les taux 2025 (si -1.0 ou vide, on compte 0%)
                def get_rate(col_name):
                    val = row.get(col_name, -1.0)
                    return val if val > 0 else 0.0

                r_nestle_25 = get_rate("NESTLE_2025")
                r_lactalis_25 = get_rate("LACTALIS_2025")
                r_nutricia_25 = get_rate("NUTRICIA_2025")
                r_fresenius_25 = get_rate("FRESENIUS_2025")

                # Marge en euros générée en 2025
                marge_euros_2025 = (
                    (ca_nestle * r_nestle_25) +
                    (ca_lactalis * r_lactalis_25) +
                    (ca_nutricia * r_nutricia_25) +
                    (ca_fresenius * r_fresenius_25)
                )
                
                # Taux moyen 2025
                taux_moyen_2025 = marge_euros_2025 / total_ca_2025

                # --- B. PROJECTION 2026 (Stratégie 70/30 Nestle vs Nutricia) ---
                # On ne regarde QUE Nestle et Nutricia pour 2026
                r_nestle_26 = get_rate("NESTLE_2026")
                r_nutricia_26 = get_rate("NUTRICIA_2026")

                if r_nestle_26 >= r_nutricia_26:
                    labo_principal = "NESTLE"
                    labo_secondaire = "NUTRICIA"
                    taux_prin = r_nestle_26
                    taux_sec = r_nutricia_26
                else:
                    labo_principal = "NUTRICIA"
                    labo_secondaire = "NESTLE"
                    taux_prin = r_nutricia_26
                    taux_sec = r_nestle_26

                # Calcul du taux mixte théorique (70% gagnant + 30% perdant)
                taux_strategie_2026 = (0.7 * taux_prin) + (0.3 * taux_sec)

                # --- C. DIFFÉRENTIEL ---
                diff_taux = taux_strategie_2026 - taux_moyen_2025
                gain_pour_10k = diff_taux * 10000

                # --- D. AFFICHAGE ---
                st.markdown("---")
                
                # Colonnes de résultats
                kpi1, kpi2, kpi3 = st.columns(3)

                with kpi1:
                    st.info("🔙 Moyenne Pondérée 2025")
                    st.write("Basée sur vos 4 fournisseurs :")
                    st.metric("Marge Moyenne", f"{taux_moyen_2025:.2%}")
                    st.caption(f"(Soit env. {marge_euros_2025:,.0f}€ de marge générée)")

                with kpi2:
                    st.info("🎯 Stratégie Cible 2026")
                    st.write(f"**70% {labo_principal} / 30% {labo_secondaire}**")
                    st.metric("Nouveau Taux Mixte", f"{taux_strategie_2026:.2%}")
                    st.caption(f"Basé sur {labo_principal}: {taux_prin:.2%} et {labo_secondaire}: {taux_sec:.2%}")

                with kpi3:
                    if diff_taux > 0:
                        st.success("🚀 Gain de performance")
                        st.metric("Gain / 10k€ de Vente", f"+ {gain_pour_10k:,.2f} €")
                        st.write(f"Évolution taux : **+{diff_taux:.2%}**")
                    elif diff_taux == 0:
                        st.warning("⚖️ Performance identique")
                        st.metric("Gain / 10k€ de Vente", "0 €")
                    else:
                        st.error("📉 Baisse mécanique")
                        st.metric("Perte / 10k€ de Vente", f"{gain_pour_10k:,.2f} €")
                        st.write(f"Évolution taux : **{diff_taux:.2%}**")

if __name__ == "__main__":
    main()
