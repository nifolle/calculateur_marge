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

    # Nettoyage et Renommage des colonnes (Structure V11 avec Fresenius)
    if df is not None:
        try:
            # On s'attend à 12 colonnes de base : 
            # 0:Cluster, 1:Appro, 2:Min, 3:Max, 
            # 4:N26, 5:L26, 6:U26, 7:F26
            # 8:N25, 9:L25, 10:U25, 11:F25
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

            # Nettoyage des chiffres
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
        st.error("❌ Erreur technique : Fichier 'data.csv' introuvable.")
        return 

    # --- FORMULAIRE ---
    st.subheader("1️⃣ Profil de la Pharmacie")
    
    # SÉLECTEURS DE PROFIL (La base du calcul)
    c_clust, c_appro = st.columns(2)
    with c_clust:
        # Récupération des clusters uniques dans le fichier
        valeurs_cluster = sorted(df['CLUSTER'].dropna().astype(str).unique())
        choix_cluster = st.selectbox("Sélectionnez votre Cluster", valeurs_cluster)
    with c_appro:
        # Récupération des modes d'approvisionnement uniques
        valeurs_appro = sorted(df['APPROVISIONNEMENT'].dropna().astype(str).unique())
        choix_appro = st.selectbox("Mode d'approvisionnement (Commun aux 4 laboratoires)", valeurs_appro)

    st.markdown("---")
    st.subheader("2️⃣ Répartition des Achats 2025")
    st.write("Saisissez le chiffre d'affaires réalisé avec chaque laboratoire :")

    # SAISIE DES 4 CA
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ca_nestle = st.number_input("CA Nestle (€)", min_value=0.0, step=100.0)
    with col2:
        ca_lactalis = st.number_input("CA Lactalis (€)", min_value=0.0, step=100.0)
    with col3:
        ca_nutricia = st.number_input("CA Nutricia (€)", min_value=0.0, step=100.0)
    with col4:
        ca_fresenius = st.number_input("CA Fresenius (€)", min_value=0.0, step=100.0)

    # Calcul du CA Total instantané
    total_ca_2025 = ca_nestle + ca_lactalis + ca_nutricia + ca_fresenius
    
    if total_ca_2025 > 0:
        st.info(f"💰 Chiffre d'Affaires Total 2025 : **{total_ca_2025:,.2f} €**")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- ACTION ---
    if st.button("📊 Analyser la performance", type="primary", use_container_width=True):
        
        if total_ca_2025 == 0:
            st.warning("Veuillez saisir au moins un montant de chiffre d'affaires.")
            return

        # 1. FILTRAGE PRINCIPAL (Cluster + Appro)
        # On ne garde que les lignes qui correspondent au choix de l'utilisateur
        mask_profil = (df['CLUSTER'].astype(str) == choix_cluster) & (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        df_filtre = df[mask_profil]

        if df_filtre.empty:
            st.warning(f"Aucun tarif trouvé pour le profil : {choix_cluster} en {choix_appro}.")
        else:
            # 2. FILTRAGE PAR TRANCHE DE CA
            # On cherche la ligne où CA Total est compris entre Min et Max
            mask_ca = (df_filtre['CA mini'] <= total_ca_2025) & (df_filtre['CA maxi'] >= total_ca_2025)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning(f"Le CA Total ({total_ca_2025:,.0f}€) est hors des tranches prévues (trop bas ou trop haut).")
            else:
                row = resultat.iloc[0]

                # --- A. CALCUL MOYENNE 2025 (Pondérée par vos CA réels) ---
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
                
                # Taux moyen 2025 (Marge Totale / CA Total)
                taux_moyen_2025 = marge_euros_2025 / total_ca_2025

                # --- B. PROJECTION 2026 (Stratégie 70/30 Nestle vs Nutricia) ---
                # Comparaison uniquement entre Nestle et Nutricia
                r_nestle_26 = get_rate("NESTLE_2026")
                r_nutricia_26 = get_rate("NUTRICIA_2026")

                if r_nestle_26 >= r_nutricia_26:
                    labo_gagnant = "NESTLE"
                    labo_perdant = "NUTRICIA"
                    taux_prin = r_nestle_26
                    taux_sec = r_nutricia_26
                else:
                    labo_gagnant = "NUTRICIA"
                    labo_perdant = "NESTLE"
                    taux_prin = r_nutricia_26
                    taux_sec = r_nestle_26

                # Taux mixte théorique : 70% sur le gagnant, 30% sur le perdant
                taux_strategie_2026 = (0.7 * taux_prin) + (0.3 * taux_sec)

                # --- C. RÉSULTATS ---
                diff_taux = taux_strategie_2026 - taux_moyen_2025
                gain_pour_10k = diff_taux * 10000

                # --- D. AFFICHAGE ---
                st.markdown("---")
                
                kpi1, kpi2, kpi3 = st.columns(3)

                with kpi1:
                    st.info("🔙 Historique 2025 (Réel)")
                    st.metric("Marge Moyenne Pondérée", f"{taux_moyen_2025:.2%}")
                    st.caption("Calculée sur la répartition exacte de vos 4 fournisseurs.")

                with kpi2:
                    st.info("🎯 Projection 2026 (Optimisée)")
                    st.write(f"Hypothèse : **70% {labo_gagnant}** / 30% {labo_perdant}")
                    st.metric("Nouveau Taux Mixte", f"{taux_strategie_2026:.2%}")

                with kpi3:
                    if diff_taux > 0:
                        st.success("🚀 Gain de Performance")
                        st.metric("Gain par 10k€ de Vente", f"+ {gain_pour_10k:,.2f} €")
                        st.write(f"Évolution du taux : **+{diff_taux:.2%}**")
                    elif diff_taux == 0:
                        st.warning("⚖️ Performance Stable")
                        st.metric("Gain par 10k€ de Vente", "0 €")
                    else:
                        st.error("📉 Perte Mécanique")
                        st.metric("Perte par 10k€ de Vente", f"{gain_pour_10k:,.2f} €")
                        st.write(f"Évolution du taux : **{diff_taux:.2%}**")

if __name__ == "__main__":
    main()
