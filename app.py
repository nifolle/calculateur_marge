import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Stratégie CNO", layout="wide")

NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"

# --- 2. CHARGEMENT ET NETTOYAGE ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None

    df = None
    # Lecture
    try:
        df = pd.read_excel(NOM_FICHIER_DATA, header=1, engine='openpyxl')
    except:
        pass
    
    if df is None:
        try:
            # Essai avec virgule puis point-virgule
            df = pd.read_csv(NOM_FICHIER_DATA, header=1, sep=',', encoding='latin-1')
            if df.shape[1] < 5:
                df = pd.read_csv(NOM_FICHIER_DATA, header=1, sep=';', encoding='latin-1')
        except:
            return None

    if df is not None:
        # Renommage des colonnes (12 premières)
        if len(df.columns) >= 12:
            df.columns = [
                "CLUSTER", "APPROVISIONNEMENT", "CA mini", "CA maxi", 
                "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026", "FRESENIUS_2026",
                "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025", "FRESENIUS_2025"
            ] + list(df.columns[12:])
        
        # NETTOYAGE CRITIQUE : On force le texte en majuscule/sans espace pour le filtrage
        df['CLUSTER'] = df['CLUSTER'].astype(str).str.strip()
        df['APPROVISIONNEMENT'] = df['APPROVISIONNEMENT'].astype(str).str.strip()

        # Nettoyage des chiffres (Gestion du 12% / 0.12)
        cols_taux = [
            "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026", "FRESENIUS_2026",
            "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025", "FRESENIUS_2025"
        ]
        for col in cols_taux:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                # Si contient "NON ELIGIBLE", on remplace par 0.12
                mask_non = df[col].str.upper().str.contains("NON ELIGIBLE", na=False)
                df.loc[mask_non, col] = "0.12"
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        return df
    return None

# --- 3. INTERFACE ---
def main():
    # Logo Centré
    st.markdown("""<style>[data-testid="stImage"]{display: block; margin-left: auto; margin-right: auto;}</style>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if os.path.exists(NOM_FICHIER_LOGO):
            st.image(NOM_FICHIER_LOGO, width=350)
        st.markdown("<h1 style='text-align: center; color: #2E4053;'>Stratégie catégorielle CNO</h1>", unsafe_allow_html=True)
    st.markdown("---")

    df = load_data()
    if df is None:
        st.error("❌ Fichier 'data.csv' introuvable.")
        return

    # --- FORMULAIRE 1 : CHOIX IMPOSÉS ---
    st.subheader("1️⃣ Profil Pharmacie")
    col_a, col_b = st.columns(2)
    
    with col_a:
        # LISTE IMPOSÉE
        choix_cluster = st.selectbox("Cluster", ["Aprium", "UM/Monge"])
    with col_b:
        # LISTE IMPOSÉE
        choix_appro = st.selectbox("Mode d'Approvisionnement", ["Direct", "Grossiste"])

    st.markdown("---")

    # --- FORMULAIRE 2 : CA 2025 ---
    st.subheader("2️⃣ Répartition Achats 2025")
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1: ca_nestle = st.number_input("CA Nestle 25 (€)", step=100.0)
    with cc2: ca_lactalis = st.number_input("CA Lactalis 25 (€)", step=100.0)
    with cc3: ca_nutricia = st.number_input("CA Nutricia 25 (€)", step=100.0)
    with cc4: ca_fresenius = st.number_input("CA Fresenius 25 (€)", step=100.0)

    total_ca = ca_nestle + ca_lactalis + ca_nutricia + ca_fresenius
    if total_ca > 0:
        st.success(f"💰 CA Total 2025 : **{total_ca:,.2f} €**")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📊 Analyser", type="primary", use_container_width=True):
        if total_ca == 0:
            st.warning("Saisissez au moins un CA.")
            return

        # FILTRAGE
        mask = (df['CLUSTER'] == choix_cluster) & (df['APPROVISIONNEMENT'] == choix_appro)
        df_filtre = df[mask]

        if df_filtre.empty:
            st.error(f"Pas de données dans le fichier pour {choix_cluster} / {choix_appro}")
        else:
            # TRANCHE CA
            mask_ca = (df_filtre['CA mini'] <= total_ca) & (df_filtre['CA maxi'] >= total_ca)
            res = df_filtre[mask_ca]

            if res.empty:
                st.warning("CA hors tranches du fichier.")
            else:
                row = res.iloc[0]

                # A. MOYENNE 2025
                r_n25 = row.get("NESTLE_2025", 0.0)
                r_l25 = row.get("LACTALIS_2025", 0.0)
                r_u25 = row.get("NUTRICIA_2025", 0.0)
                r_f25 = row.get("FRESENIUS_2025", 0.0)
                
                marge_2025 = (ca_nestle*r_n25) + (ca_lactalis*r_l25) + (ca_nutricia*r_u25) + (ca_fresenius*r_f25)
                taux_moy_25 = marge_2025 / total_ca

                # B. STRATEGIE 2026 (Nestle vs Nutricia)
                r_n26 = row.get("NESTLE_2026", 0.0)
                r_u26 = row.get("NUTRICIA_2026", 0.0)

                if r_n26 >= r_u26:
                    win, lose = "NESTLE", "NUTRICIA"
                    t_win, t_lose = r_n26, r_u26
                else:
                    win, lose = "NUTRICIA", "NESTLE"
                    t_win, t_lose = r_u26, r_n26
                
                taux_strat_26 = (0.7 * t_win) + (0.3 * t_lose)
                
                # C. GAIN
                diff = taux_strat_26 - taux_moy_25
                gain_10k = diff * 10000

                # AFFICHAGE
                st.markdown("---")
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.info("🔙 Moyenne 2025 (Réel)")
                    st.metric("Taux Actuel", f"{taux_moy_25:.2%}")
                with k2:
                    st.info("🎯 Projection 2026")
                    st.write(f"**70% {win}** / 30% {lose}")
                    st.metric("Nouveau Taux", f"{taux_strat_26:.2%}")
                with k3:
                    if diff > 0:
                        st.success("🚀 Gain")
                        st.metric("Gain / 10k€ Vente", f"+{gain_10k:,.2f} €")
                        st.write(f"Évolution: +{diff:.2%}")
                    elif diff == 0:
                        st.warning("⚖️ Stable")
                        st.metric("Gain", "0 €")
                    else:
                        st.error("📉 Perte")
                        st.metric("Perte / 10k€ Vente", f"{gain_10k:,.2f} €")
                        st.write(f"Évolution: {diff:.2%}")

if __name__ == "__main__":
    main()
