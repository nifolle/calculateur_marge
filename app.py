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

# --- 3. FONCTION DE CHARGEMENT ET NETTOYAGE (SPÉCIAL V12) ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None

    df = None
    
    # 1. Lecture Hybride (Excel ou CSV)
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

    # 2. Nettoyage et Renommage des colonnes
    if df is not None:
        try:
            # Structure attendue V12 (similaire V11) avec Fresenius
            # On s'assure d'avoir les 12 premières colonnes identifiées
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

            # Liste des colonnes de taux
            cols_to_clean = [
                "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026", "FRESENIUS_2026",
                "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025", "FRESENIUS_2025"
            ]
            
            for col in cols_to_clean:
                if col in df.columns:
                    # Conversion en string pour traitement du texte
                    df[col] = df[col].astype(str)
                    
                    # Remplacement de la virgule par un point
                    df[col] = df[col].str.replace(',', '.', regex=False)
                    
                    # GESTION SPÉCIFIQUE "NON ELIGIBLE" = 12% (0.12)
                    # On utilise str.contains pour attraper "NON ELIGIBLE", "Non eligible", etc.
                    mask_non_eligible = df[col].str.upper().str.contains("NON ELIGIBLE", na=False)
                    df.loc[mask_non_eligible, col] = "0.12"

                    # Conversion finale en numérique
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            return df
        except Exception as e:
            st.error(f"Erreur lors du nettoyage des données : {e}")
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
        st.error("❌ Erreur technique : Fichier 'data.csv' introuvable ou illisible.")
        return 

    # --- FORMULAIRE ÉTAPE 1 : LE PROFIL ---
    st.subheader("1️⃣ Profil de la Pharmacie")
    st.info("Veuillez sélectionner votre Cluster et votre mode d'Approvisionnement.")
    
    c_clust, c_appro = st.columns(2)
    with c_clust:
        # Récupération propre des clusters (ex: Aprium, UM/Monge)
        valeurs_cluster = sorted(df['CLUSTER'].dropna().astype(str).unique())
        choix_cluster = st.selectbox("Cluster", valeurs_cluster)
        
    with c_appro:
        # Récupération propre des modes (Direct, Grossiste)
        valeurs_appro = sorted(df['APPROVISIONNEMENT'].dropna().astype(str).unique())
        choix_appro = st.selectbox("Mode d'Approvisionnement", valeurs_appro)

    st.markdown("---")
    
    # --- FORMULAIRE ÉTAPE 2 : LES CHIFFRES ---
    st.subheader("2️⃣ Répartition des Achats 2025")
    st.write("Saisissez le chiffre d'affaires réalisé avec chaque laboratoire :")

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
        st.success(f"💰 Chiffre d'Affaires Total 2025 pris en compte : **{total_ca_2025:,.2f} €**")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- ACTION ---
    if st.button("📊 Analyser la performance", type="primary", use_container_width=True):
        
        if total_ca_2025 == 0:
            st.warning("Veuillez saisir au moins un montant de chiffre d'affaires.")
            return

        # 1. FILTRAGE STRICT (Cluster + Appro)
        mask_profil = (df['CLUSTER'].astype(str) == choix_cluster) & (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        df_filtre = df[mask_profil]

        if df_filtre.empty:
            st.error(f"ERREUR : Aucune ligne trouvée dans le fichier pour {choix_cluster} en {choix_appro}.")
        else:
            # 2. FILTRAGE PAR TRANCHE DE CA (Basé sur le total saisi)
            mask_ca = (df_filtre['CA mini'] <= total_ca_2025) & (df_filtre['CA maxi'] >= total_ca_2025)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning(f"Le CA Total ({total_ca_2025:,.0f}€) est hors des tranches définies dans le fichier (Min/Max).")
            else:
                row = resultat.iloc[0]

                # --- A. CALCUL MOYENNE 2025 (Pondérée par vos CA réels) ---
                # On récupère les taux 2025 (Note: 12% est déjà géré lors du chargement)
                r_nestle_25 = row.get("NESTLE_2025", 0.0)
                r_lactalis_25 = row.get("LACTALIS_2025", 0.0)
                r_nutricia_25 = row.get("NUTRICIA_2025", 0.0)
                r_fresenius_25 = row.get("FRESENIUS_2025", 0.0)

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
                r_nestle_26 = row.get("NESTLE_2026", 0.0)
                r_nutricia_26 = row.get("NUTRICIA_2026", 0.0)

                # Comparaison
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
                    st.metric("Marge Moyenne", f"{taux_moyen_2025:.2%}")
                    st.caption("Calculée sur vos volumes réels 2025.")

                with kpi2:
                    st.info("🎯 Projection 2026 (Optimisée)")
                    st.write(f"**70% {labo_gagnant}** / 30% {labo_perdant}")
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
                        st.error("📉 Baisse Mécanique")
                        st.metric("Perte par 10k€ de Vente", f"{gain_pour_10k:,.2f} €")
                        st.write(f"Évolution du taux : **{diff_taux:.2%}**")

if __name__ == "__main__":
    main()
