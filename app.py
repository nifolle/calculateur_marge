import streamlit as st
import pandas as pd
import os
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Stratégie CNO", layout="wide")

NOM_FICHIER_DATA = "data.csv" # Le code cherchera aussi les .xlsx
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

# --- 3. CHARGEMENT HYBRIDE (EXCEL + CSV) ---
@st.cache_data
def load_data():
    # 1. Recherche du fichier (CSV ou XLSX)
    target = NOM_FICHIER_DATA
    if not os.path.exists(target):
        files = [f for f in os.listdir() if "COMPARATIF" in f or "data" in f]
        valid_files = [f for f in files if f.endswith(".xlsx") or f.endswith(".csv")]
        if valid_files: target = valid_files[0]
        else: return None, "Fichier introuvable"

    df = None
    debug_msg = ""

    # --- TENTATIVE 1 : LECTURE EXCEL ---
    try:
        # engine='openpyxl' est nécessaire pour les .xlsx
        df_temp = pd.read_excel(target, header=None, engine='openpyxl')
        
        header_idx = -1
        for i, row in df_temp.iterrows():
            row_str = row.astype(str).str.cat(sep=' ').upper()
            if "CLUSTER" in row_str and "APPROVISIONNEMENT" in row_str:
                header_idx = i
                break
        
        if header_idx != -1:
            df = pd.read_excel(target, header=header_idx, engine='openpyxl')
        
    except Exception as e_excel:
        debug_msg += f"Excel fail: {e_excel}. "
        # --- TENTATIVE 2 : LECTURE CSV ---
        try:
            encodings = ['latin-1', 'utf-8', 'cp1252']
            for encoding in encodings:
                try:
                    with open(target, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    
                    header_idx = -1
                    sep = ','
                    for i, line in enumerate(lines):
                        if "CLUSTER" in line.upper():
                            header_idx = i
                            if line.count(';') > line.count(','): sep = ';'
                            break
                    
                    if header_idx != -1:
                        clean_content = "".join(lines[header_idx:])
                        df = pd.read_csv(io.StringIO(clean_content), sep=sep)
                        break
                except: continue
        except Exception as e_csv:
            debug_msg += f"CSV fail: {e_csv}"

    if df is not None:
        # --- NORMALISATION ---
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

    return None, debug_msg

# --- 4. INTERFACE ---
def main():
    st.markdown("""<style>[data-testid="stImage"]{display: block; margin-left: auto; margin-right: auto;}</style>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if os.path.exists(NOM_FICHIER_LOGO):
            st.image(NOM_FICHIER_LOGO, width=350)
        st.markdown("<h1 style='text-align: center; color: #2E4053;'>Stratégie catégorielle CNO</h1>", unsafe_allow_html=True)
    st.markdown("---")

    df, error_msg = load_data()

    if df is None:
        st.error("❌ Impossible de lire le fichier (ni en Excel, ni en CSV).")
        if error_msg: st.warning(f"Détails : {error_msg}")
        return

    # --- ÉTAPES ---
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
                
                # --- CALCULS ---
                # 2025
                r_n25 = row.get("NESTLE_2025", 0.0)
                r_l25 = row.get("LACTALIS_2025", 0.0)
                r_u25 = row.get("NUTRICIA_2025", 0.0)
                r_f25 = row.get("FRESENIUS_2025", 0.0)
                
                marge_2025 = (ca_nestle*r_n25) + (ca_lactalis*r_l25) + (ca_nutricia*r_u25) + (ca_fresenius*r_f25)
                taux_moy_25 = marge_2025 / total_ca

                # 2026
                r_n26 = row.get("NESTLE_2026", 0.0)
                r_u26 = row.get("NUTRICIA_2026", 0.0)
                r_l26 = row.get("LACTALIS_2026", 0.0) # Juste pour info si besoin
                r_f26 = row.get("FRESENIUS_2026", 0.0)

                if r_n26 >= r_u26:
                    win, lose = "NESTLE", "NUTRICIA"
                    t_win, t_lose = r_n26, r_u26
                else:
                    win, lose = "NUTRICIA", "NESTLE"
                    t_win, t_lose = r_u26, r_n26
                
                taux_strat_26 = (0.7 * t_win) + (0.3 * t_lose)
                diff = taux_strat_26 - taux_moy_25
                gain_10k = diff * 10000

                # --- AFFICHAGE ---
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
                    elif diff == 0:
                        st.warning("⚖️ Stable")
                        st.metric("Gain", "0 €")
                    else:
                        st.error("📉 Perte de Marge")
                        st.metric("Perte / 10k€ Vente", f"{gain_10k:,.2f} €")
                    st.write(f"Évolution: {diff:+.2%}")

                # --- NOUVEAU BLOC : DÉTAILS ---
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("🔎 Voir les détails des calculs (Valeurs utilisées)"):
                    
                    st.write("#### 1. Calcul du Taux Moyen 2025")
                    st.write("Ce taux correspond à la moyenne pondérée par vos volumes d'achats réels.")
                    
                    data_2025 = {
                        "Laboratoire": ["Nestlé", "Lactalis", "Nutricia", "Fresenius"],
                        "Vos Achats (Saisie)": [ca_nestle, ca_lactalis, ca_nutricia, ca_fresenius],
                        "Taux Marge (Fichier)": [r_n25, r_l25, r_u25, r_f25],
                        "Marge Générée (€)": [ca_nestle*r_n25, ca_lactalis*r_l25, ca_nutricia*r_u25, ca_fresenius*r_f25]
                    }
                    df_details = pd.DataFrame(data_2025)
                    
                    # Affichage propre du tableau
                    st.dataframe(df_details.style.format({
                        "Vos Achats (Saisie)": "{:,.2f} €",
                        "Taux Marge (Fichier)": "{:.2%}",
                        "Marge Générée (€)": "{:,.2f} €"
                    }), use_container_width=True)
                    
                    st.info(f"👉 **Calcul :** {marge_2025:,.2f} € (Marge Totale) ÷ {total_ca:,.2f} € (CA Total) = **{taux_moy_25:.4f}** ({taux_moy_25:.2%})")

                    st.markdown("---")
                    st.write("#### 2. Calcul du Nouveau Taux 2026")
                    st.write("Comparaison des taux catalogues 2026 pour votre tranche :")
                    
                    c_d1, c_d2 = st.columns(2)
                    with c_d1:
                        st.write(f"- 🔵 **Nestlé 2026 : {r_n26:.2%}**")
                        st.write(f"- 🟠 **Nutricia 2026 : {r_u26:.2%}**")
                    with c_d2:
                        st.write(f"🏆 Gagnant : **{win}**")
                        st.write(f"💀 Perdant : **{lose}**")
                    
                    st.markdown("**Formule stratégique appliquée :**")
                    st.latex(r"\text{Taux 26} = (0.7 \times \text{Gagnant}) + (0.3 \times \text{Perdant})")
                    st.latex(rf"\text{{Taux 26}} = (0.7 \times {t_win:.4f}) + (0.3 \times {t_lose:.4f}) = \mathbf{{{taux_strat_26:.4f}}}")

if __name__ == "__main__":
    main()
