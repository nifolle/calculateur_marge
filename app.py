import streamlit as st
import pandas as pd
import os
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Stratégie CNO", layout="wide")

NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"

# --- 2. FONCTIONS DE NETTOYAGE ---
def clean_currency(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    s = str(val).strip()
    s = s.replace('€', '').replace(' ', '').replace('\xa0', '').replace(',', '.')
    if s in ['-', '']: return 0.0
    try: return float(s)
    except: return 0.0

def clean_rate(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    s = str(val).strip().upper().replace(',', '.')
    if "NON ELIGIBLE" in s: return 0.12 
    try: return float(s)
    except: return 0.0

# --- 3. CHARGEMENT ULTRA-ROBUSTE ---
@st.cache_data
def load_data():
    target = NOM_FICHIER_DATA
    if not os.path.exists(target):
        files = [f for f in os.listdir() if f.endswith(".csv") and "COMPARATIF" in f]
        if files: target = files[0]
        else: return None, "Fichier introuvable"

    # Liste des encodages probables (Excel FR, Excel Unicode, Standard Web)
    encodings_to_try = ['latin-1', 'utf-8', 'utf-16', 'cp1252']
    
    df = None
    debug_lines = [] # Pour afficher à l'utilisateur si ça plante

    for encoding in encodings_to_try:
        try:
            with open(target, 'r', encoding=encoding) as f:
                lines = f.readlines()
            
            if not lines: continue

            # Recherche de la ligne Header
            header_idx = -1
            separator = ','
            
            for i, line in enumerate(lines):
                # On nettoie la ligne pour la comparaison
                line_upper = line.upper()
                # Critère souple : on cherche juste "CLUSTER"
                if "CLUSTER" in line_upper:
                    header_idx = i
                    # Détection séparateur
                    if line.count(';') > line.count(','): separator = ';'
                    else: separator = ','
                    break
            
            if header_idx != -1:
                # On a trouvé ! On charge.
                clean_content = "".join(lines[header_idx:])
                df = pd.read_csv(io.StringIO(clean_content), sep=separator)
                break # Sortir de la boucle d'encodages
            else:
                # On garde une trace des lignes pour le debug si c'est le dernier essai
                if encoding == encodings_to_try[0]: 
                    debug_lines = lines[:5]

        except Exception:
            continue

    if df is not None:
        # Renommage et nettoyage standard
        if len(df.columns) >= 12:
            new_cols = list(df.columns)
            # Mapping forcé pour éviter les erreurs de noms
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

        if "CLUSTER" in df.columns:
            df['CLUSTER'] = df['CLUSTER'].astype(str).str.strip()
        if "APPROVISIONNEMENT" in df.columns:
            df['APPROVISIONNEMENT'] = df['APPROVISIONNEMENT'].astype(str).str.strip()
        
        for col in ["CA mini", "CA maxi"]:
            if col in df.columns: df[col] = df[col].apply(clean_currency)
        
        cols_taux = [
            "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026", "FRESENIUS_2026",
            "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025", "FRESENIUS_2025"
        ]
        for col in cols_taux:
            if col in df.columns: df[col] = df[col].apply(clean_rate)
            
        return df, None

    # Si on arrive ici, c'est que rien n'a marché
    return None, debug_lines

# --- 4. INTERFACE ---
def main():
    st.markdown("""<style>[data-testid="stImage"]{display: block; margin-left: auto; margin-right: auto;}</style>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if os.path.exists(NOM_FICHIER_LOGO):
            st.image(NOM_FICHIER_LOGO, width=350)
        st.markdown("<h1 style='text-align: center; color: #2E4053;'>Stratégie catégorielle CNO</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # Chargement
    df, error_info = load_data()

    # GESTION DES ERREURS D'AFFICHAGE
    if df is None:
        st.error("❌ Échec critique : Impossible de lire le fichier.")
        
        if isinstance(error_info, list) and len(error_info) > 0:
            st.warning("🧐 Voici ce que le programme voit dans votre fichier (5 premières lignes). Si c'est illisible, le fichier est corrompu ou crypté.")
            st.code("".join(error_info), language="text")
            st.markdown("**Conseil :** Vérifiez que la colonne s'appelle bien `CLUSTER`.")
        elif error_info == "Fichier introuvable":
             st.error("Le fichier 'data.csv' est introuvable.")
        else:
            st.error("Erreur inconnue. Essayez d'ouvrir le CSV dans Excel et de le ré-enregistrer en 'CSV (séparateur: point-virgule)'.")
        return

    # --- SUITE DU PROGRAMME (Si tout va bien) ---
    st.subheader("1️⃣ Profil Pharmacie")
    col_a, col_b = st.columns(2)
    
    with col_a:
        liste_clusters = sorted(df['CLUSTER'].unique()) if 'CLUSTER' in df.columns else ["Aprium", "UM/Monge"]
        choix_cluster = st.selectbox("Cluster", liste_clusters)
    with col_b:
        liste_appros = sorted(df['APPROVISIONNEMENT'].unique()) if 'APPROVISIONNEMENT' in df.columns else ["Direct", "Grossiste"]
        choix_appro = st.selectbox("Mode d'Approvisionnement", liste_appros)

    st.markdown("---")

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

    if st.button("📊 Analyser la performance", type="primary", use_container_width=True):
        if total_ca == 0:
            st.warning("Veuillez saisir au moins un montant.")
            return

        mask = (df['CLUSTER'] == choix_cluster) & (df['APPROVISIONNEMENT'] == choix_appro)
        df_filtre = df[mask]

        if df_filtre.empty:
            st.error(f"Aucune donnée trouvée pour : {choix_cluster} / {choix_appro}")
        else:
            mask_ca = (df_filtre['CA mini'] <= total_ca) & (df_filtre['CA maxi'] >= total_ca)
            res = df_filtre[mask_ca]

            if res.empty:
                st.warning(f"Le CA Total ({total_ca:,.0f}€) est hors des tranches prévues (Min/Max).")
            else:
                row = res.iloc[0]
                r_n25 = row.get("NESTLE_2025", 0.0)
                r_l25 = row.get("LACTALIS_2025", 0.0)
                r_u25 = row.get("NUTRICIA_2025", 0.0)
                r_f25 = row.get("FRESENIUS_2025", 0.0)
                
                marge_2025 = (ca_nestle*r_n25) + (ca_lactalis*r_l25) + (ca_nutricia*r_u25) + (ca_fresenius*r_f25)
                taux_moy_25 = marge_2025 / total_ca

                r_n26 = row.get("NESTLE_2026", 0.0)
                r_u26 = row.get("NUTRICIA_2026", 0.0)

                if r_n26 >= r_u26:
                    win, lose = "NESTLE", "NUTRICIA"
                    t_win, t_lose = r_n26, r_u26
                else:
                    win, lose = "NUTRICIA", "NESTLE"
                    t_win, t_lose = r_u26, r_n26
                
                taux_strat_26 = (0.7 * t_win) + (0.3 * t_lose)
                diff = taux_strat_26 - taux_moy_25
                gain_10k = diff * 10000

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
