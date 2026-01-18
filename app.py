import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Stratégie CNO", layout="wide")

NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"

# --- 2. FONCTIONS DE NETTOYAGE ---

def clean_currency(val):
    """Convertit n'importe quel format de chiffre (texte avec €, espace, ou nombre pur) en float"""
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val) # Si c'est déjà un nombre
    
    s = str(val).strip()
    s = s.replace('€', '').replace(' ', '').replace('\xa0', '') # Enlever devise et espaces (y compris insécables)
    s = s.replace(',', '.')                 # Virgule -> Point
    if s in ['-', '']: return 0.0
    try:
        return float(s)
    except:
        return 0.0

def clean_rate(val):
    """Convertit '0,25', '0.25' ou 'NON ELIGIBLE' en float"""
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)

    s = str(val).strip().upper()
    s = s.replace(',', '.')
    
    # Règle des 12%
    if "NON ELIGIBLE" in s:
        return 0.12 
    try:
        return float(s)
    except:
        return 0.0

# --- 3. CHARGEMENT INTELLIGENT (Spécial V15) ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None

    df = None
    try:
        # V15 : Les titres sont sur la ligne 2 (donc header=1 en python qui commence à 0)
        # On essaie d'abord la virgule (standard CSV)
        df = pd.read_csv(NOM_FICHIER_DATA, header=1, sep=',', encoding='latin-1')
        
        # Si ça a mal lu (tout dans une colonne), on essaie le point-virgule
        if df.shape[1] < 5:
            df = pd.read_csv(NOM_FICHIER_DATA, header=1, sep=';', encoding='latin-1')
    except Exception as e:
        st.error(f"Erreur lecture CSV: {e}")
        return None

    if df is not None:
        # RENOMMAGE DES COLONNES PAR POSITION
        # Le fichier V15 a des doublons de noms (NESTLE apparaît pour 2026 et 2025).
        # On force les noms pour éviter la confusion.
        if len(df.columns) >= 12:
            new_columns = list(df.columns)
            # Colonnes 0 à 3 : Contexte
            new_columns[0] = "CLUSTER"
            new_columns[1] = "APPROVISIONNEMENT"
            new_columns[2] = "CA mini"
            new_columns[3] = "CA maxi"
            # Colonnes 4 à 7 : 2026
            new_columns[4] = "NESTLE_2026"
            new_columns[5] = "LACTALIS_2026"
            new_columns[6] = "NUTRICIA_2026"
            new_columns[7] = "FRESENIUS_2026"
            # Colonnes 8 à 11 : 2025
            new_columns[8] = "NESTLE_2025"
            new_columns[9] = "LACTALIS_2025"
            new_columns[10] = "NUTRICIA_2025"
            new_columns[11] = "FRESENIUS_2025"
            
            df.columns = new_columns

        # NETTOYAGE TEXTE (Cluster/Appro) pour le filtrage
        if "CLUSTER" in df.columns:
            df['CLUSTER'] = df['CLUSTER'].astype(str).str.strip()
        if "APPROVISIONNEMENT" in df.columns:
            df['APPROVISIONNEMENT'] = df['APPROVISIONNEMENT'].astype(str).str.strip()
        
        # NETTOYAGE CHIFFRES (CA et TAUX)
        for col in ["CA mini", "CA maxi"]:
            if col in df.columns:
                df[col] = df[col].apply(clean_currency)

        cols_taux = [
            "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026", "FRESENIUS_2026",
            "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025", "FRESENIUS_2025"
        ]
        for col in cols_taux:
            if col in df.columns:
                df[col] = df[col].apply(clean_rate)
        
        return df
    return None

# --- 4. INTERFACE ---
def main():
    # Centrage Logo
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

    # --- ÉTAPE 1 : CHOIX IMPOSÉS ---
    st.subheader("1️⃣ Profil Pharmacie")
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Listes fixes comme demandé
        choix_cluster = st.selectbox("Cluster", ["Aprium", "UM/Monge"])
    with col_b:
        choix_appro = st.selectbox("Mode d'Approvisionnement", ["Direct", "Grossiste"])

    st.markdown("---")

    # --- ÉTAPE 2 : SAISIE CA 2025 ---
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

    # --- ÉTAPE 3 : CALCUL ---
    if st.button("📊 Analyser la performance", type="primary", use_container_width=True):
        if total_ca == 0:
            st.warning("Veuillez saisir au moins un montant.")
            return

        # 1. FILTRE CLUSTER / APPRO
        mask = (df['CLUSTER'] == choix_cluster) & (df['APPROVISIONNEMENT'] == choix_appro)
        df_filtre = df[mask]

        if df_filtre.empty:
            st.error(f"Pas de données trouvées dans le fichier pour : {choix_cluster} / {choix_appro}")
        else:
            # 2. FILTRE TRANCHE CA
            mask_ca = (df_filtre['CA mini'] <= total_ca) & (df_filtre['CA maxi'] >= total_ca)
            res = df_filtre[mask_ca]

            if res.empty:
                st.warning(f"Le CA Total ({total_ca:,.0f}€) ne correspond à aucune tranche (Min/Max) dans le fichier.")
            else:
                row = res.iloc[0]

                # --- CALCULS ---

                # A. MOYENNE 2025 (Pondérée Réelle)
                r_n25 = row.get("NESTLE_2025", 0.0)
                r_l25 = row.get("LACTALIS_2025", 0.0)
                r_u25 = row.get("NUTRICIA_2025", 0.0)
                r_f25 = row.get("FRESENIUS_2025", 0.0)
                
                marge_2025 = (ca_nestle*r_n25) + (ca_lactalis*r_l25) + (ca_nutricia*r_u25) + (ca_fresenius*r_f25)
                taux_moy_25 = marge_2025 / total_ca

                # B. STRATEGIE 2026 (Nestle vs Nutricia, 70/30)
                r_n26 = row.get("NESTLE_2026", 0.0)
                r_u26 = row.get("NUTRICIA_2026", 0.0)

                # Comparaison
                if r_n26 >= r_u26:
                    win, lose = "NESTLE", "NUTRICIA"
                    t_win, t_lose = r_n26, r_u26
                else:
                    win, lose = "NUTRICIA", "NESTLE"
                    t_win, t_lose = r_u26, r_n26
                
                # Calcul Mixte
                taux_strat_26 = (0.7 * t_win) + (0.3 * t_lose)
                
                # C. GAIN
                diff = taux_strat_26 - taux_moy_25
                gain_10k = diff * 10000

                # --- AFFICHAGE ---
                st.markdown("---")
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.info("🔙 Moyenne 2025 (Réel)")
                    st.metric("Taux Actuel", f"{taux_moy_25:.2%}")
                    st.caption("Pondérée sur vos 4 labos")
                with k2:
                    st.info("🎯 Projection 2026")
                    st.write(f"**70% {win}** / 30% {lose}")
                    st.metric("Nouveau Taux", f"{taux_strat_26:.2%}")
                with k3:
                    if diff > 0:
                        st.success("🚀 Gain de Marge")
                        st.metric("Gain / 10k€ Vente", f"+{gain_10k:,.2f} €")
                        st.write(f"Évolution: +{diff:.2%}")
                    elif diff == 0:
                        st.warning("⚖️ Stable")
                        st.metric("Gain", "0 €")
                    else:
                        st.error("📉 Perte de Marge")
                        st.metric("Perte / 10k€ Vente", f"{gain_10k:,.2f} €")
                        st.write(f"Évolution: {diff:.2%}")

if __name__ == "__main__":
    main()
