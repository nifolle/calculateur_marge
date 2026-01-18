import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Stratégie CNO", layout="wide")

NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"

# --- 2. FONCTIONS DE NETTOYAGE ---

def clean_currency(val):
    """Nettoie les montants (enlève €, espaces, et convertit en chiffre)"""
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    
    s = str(val).strip()
    s = s.replace('€', '').replace(' ', '').replace('\xa0', '') 
    s = s.replace(',', '.') # Virgule -> Point
    if s in ['-', '']: return 0.0
    try:
        return float(s)
    except:
        return 0.0

def clean_rate(val):
    """Nettoie les taux (gère les %, les virgules et le texte)"""
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)

    s = str(val).strip().upper()
    s = s.replace(',', '.') # Virgule -> Point
    
    if "NON ELIGIBLE" in s:
        return 0.12 
    try:
        return float(s)
    except:
        return 0.0

# --- 3. CHARGEMENT ET PRÉPARATION (VERSION BULLDOZER) ---
@st.cache_data
def load_data():
    target = NOM_FICHIER_DATA
    if not os.path.exists(target):
        files = [f for f in os.listdir() if f.endswith(".csv") and "COMPARATIF" in f]
        if files: target = files[0]
        else: return None

    df = None
    try:
        # 1. REPÉRAGE DE LA LIGNE D'EN-TÊTE
        # On lit le fichier ligne par ligne pour trouver le numéro de la ligne qui contient "CLUSTER"
        header_row_idx = 0
        with open(target, 'r', encoding='latin-1') as f:
            for i, line in enumerate(f):
                if "CLUSTER" in line and "APPROVISIONNEMENT" in line:
                    header_row_idx = i
                    break
        
        # 2. LECTURE AVEC LE MOTEUR PYTHON (Plus tolérant aux erreurs)
        # On essaie d'abord avec la virgule
        try:
            df = pd.read_csv(target, header=header_row_idx, sep=',', engine='python', encoding='latin-1')
        except:
            # Si ça plante, on ne fait rien, on essaiera le point-virgule juste après
            pass

        # 3. VÉRIFICATION ET SECONDE CHANCE
        # Si df est vide ou s'il a tout mis dans une seule colonne (échec de la virgule)
        if df is None or df.shape[1] < 5:
            df = pd.read_csv(target, header=header_row_idx, sep=';', engine='python', encoding='latin-1')

    except Exception as e:
        st.error(f"Échec total de la lecture : {e}")
        return None

    if df is not None:
        # --- RENOMMAGE ET NETTOYAGE ---
        # On force les noms de colonnes car Pandas a peut-être ajouté des suffixes .1, .2
        if len(df.columns) >= 12:
            new_cols = list(df.columns)
            new_cols[0] = "CLUSTER"
            new_cols[1] = "APPROVISIONNEMENT"
            new_cols[2] = "CA mini"
            new_cols[3] = "CA maxi"
            new_cols[4] = "NESTLE_2026"
            new_cols[5] = "LACTALIS_2026"
            new_cols[6] = "NUTRICIA_2026"
            new_cols[7] = "FRESENIUS_2026"
            new_cols[8] = "NESTLE_2025"
            new_cols[9] = "LACTALIS_2025"
            new_cols[10] = "NUTRICIA_2025"
            new_cols[11] = "FRESENIUS_2025"
            df.columns = new_cols

        # Conversion forcée en String pour les filtres
        if "CLUSTER" in df.columns:
            df['CLUSTER'] = df['CLUSTER'].astype(str).str.strip()
        if "APPROVISIONNEMENT" in df.columns:
            df['APPROVISIONNEMENT'] = df['APPROVISIONNEMENT'].astype(str).str.strip()
        
        # Nettoyage chiffres
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
    st.markdown("""<style>[data-testid="stImage"]{display: block; margin-left: auto; margin-right: auto;}</style>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if os.path.exists(NOM_FICHIER_LOGO):
            st.image(NOM_FICHIER_LOGO, width=350)
        st.markdown("<h1 style='text-align: center; color: #2E4053;'>Stratégie catégorielle CNO</h1>", unsafe_allow_html=True)
    st.markdown("---")

    df = load_data()
    if df is None:
        st.error("❌ Impossible de charger les données. Vérifiez le fichier CSV.")
        return

    # --- ÉTAPE 1 : CHOIX DU PROFIL ---
    st.subheader("1️⃣ Profil Pharmacie")
    col_a, col_b = st.columns(2)
    
    with col_a:
        # On récupère les valeurs uniques dispo dans le fichier pour éviter les menus vides
        liste_clusters = sorted(df['CLUSTER'].unique()) if 'CLUSTER' in df.columns else ["Aprium", "UM/Monge"]
        choix_cluster = st.selectbox("Cluster", liste_clusters)
    with col_b:
        liste_appros = sorted(df['APPROVISIONNEMENT'].unique()) if 'APPROVISIONNEMENT' in df.columns else ["Direct", "Grossiste"]
        choix_appro = st.selectbox("Mode d'Approvisionnement", liste_appros)

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

    # --- ÉTAPE 3 : ANALYSE ---
    if st.button("📊 Analyser la performance", type="primary", use_container_width=True):
        if total_ca == 0:
            st.warning("Veuillez saisir au moins un montant.")
            return

        # 1. FILTRAGE
        mask = (df['CLUSTER'] == choix_cluster) & (df['APPROVISIONNEMENT'] == choix_appro)
        df_filtre = df[mask]

        if df_filtre.empty:
            st.error(f"Aucune donnée trouvée pour : {choix_cluster} / {choix_appro}")
        else:
            # 2. TRANCHE CA
            mask_ca = (df_filtre['CA mini'] <= total_ca) & (df_filtre['CA maxi'] >= total_ca)
            res = df_filtre[mask_ca]

            if res.empty:
                st.warning(f"Le CA Total ({total_ca:,.0f}€) est hors des tranches prévues (Min/Max).")
            else:
                row = res.iloc[0]

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

                # Qui gagne ?
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

                # D. AFFICHAGE
                st.markdown("---")
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.info("🔙 Moyenne 2025 (Réel)")
                    st.metric("Taux Actuel", f"{taux_moy_25:.2%}")
                    st.caption("Moyenne pondérée de vos 4 labos")
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
