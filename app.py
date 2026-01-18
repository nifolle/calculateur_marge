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

# --- 3. CHARGEMENT ROBUSTE ---
@st.cache_data
def load_data():
    target = NOM_FICHIER_DATA
    if not os.path.exists(target):
        files = [f for f in os.listdir() if "COMPARATIF" in f or "data" in f]
        valid_files = [f for f in files if f.endswith(".xlsx") or f.endswith(".csv")]
        if valid_files: target = valid_files[0]
        else: return None, "Fichier introuvable"

    df = None
    debug_msg = ""

    try:
        # TENTATIVE EXCEL
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
        # TENTATIVE CSV
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

# --- 4. FONCTION DE RECHERCHE DE TAUX ---
def get_rate_from_grid(df_grid, turnover, col_name):
    """
    Cherche le taux dans la grille correspondant exactement au CA fourni.
    """
    if turnover <= 0:
        return 0.0
    
    # On filtre la ligne où CA mini <= turnover <= CA maxi
    row = df_grid[(df_grid['CA mini'] <= turnover) & (df_grid['CA maxi'] >= turnover)]
    
    # Gestion des cas hors tranches
    if row.empty:
        max_limit = df_grid['CA maxi'].max()
        if turnover > max_limit:
            # On prend la dernière tranche (la plus haute)
            row = df_grid[df_grid['CA maxi'] == max_limit]
        else:
            return 0.0

    if not row.empty:
        return row.iloc[0].get(col_name, 0.0)
    return 0.0

# --- 5. INTERFACE ---
def main():
    
    # --- MISE EN PAGE DU HEADER (Modifié pour alignement "g") ---
    # On injecte du CSS pour :
    # 1. Centrer le texte H1
    # 2. Centrer l'image MAIS la décaler de 40px vers la droite (transform: translateX) pour l'aligner avec le "g"
    st.markdown("""
        <style>
            [data-testid="stAppViewContainer"] > .main {
                padding-top: 2rem;
            }
            .header-container {
                text-align: center;
            }
            div[data-testid="stImage"] {
                display: block;
                margin-left: auto;
                margin-right: auto;
                text-align: center;
            }
            /* C'est ici que la magie opère : on décale l'image un peu à droite */
            div[data-testid="stImage"] > img {
                transform: translateX(45px); 
            }
            h1 {
                text-align: center;
                color: #2E4053;
                margin-top: -10px;
            }
        </style>
    """, unsafe_allow_html=True)

    # Affichage du Logo et Titre sans colonnes pour un centrage absolu
    if os.path.exists(NOM_FICHIER_LOGO):
        st.image(NOM_FICHIER_LOGO, width=350)
    st.markdown("<h1>Stratégie catégorielle CNO</h1>", unsafe_allow_html=True)
    
    st.markdown("---")

    # --- LOGIQUE DE L'APP ---
    df, error_msg = load_data()
    if df is None:
        st.error("❌ Erreur chargement fichier.")
        if error_msg: st.warning(error_msg)
        return

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

        # 1. On récupère LA GRILLE complète pour ce profil
        mask = (df['CLUSTER'] == choix_cluster) & (df['APPROVISIONNEMENT'] == choix_appro)
        df_grid = df[mask]

        if df_grid.empty:
            st.error(f"Aucune grille trouvée pour : {choix_cluster} / {choix_appro}")
        else:
            # --- A. CALCUL 2025 ---
            r_n25 = get_rate_from_grid(df_grid, ca_nestle, "NESTLE_2025")
            r_l25 = get_rate_from_grid(df_grid, ca_lactalis, "LACTALIS_2025")
            r_u25 = get_rate_from_grid(df_grid, ca_nutricia, "NUTRICIA_2025")
            r_f25 = get_rate_from_grid(df_grid, ca_fresenius, "FRESENIUS_2025")
            
            marge_2025 = (ca_nestle*r_n25) + (ca_lactalis*r_l25) + (ca_nutricia*r_u25) + (ca_fresenius*r_f25)
            taux_moy_25 = marge_2025 / total_ca

            # --- B. STRATEGIE 2026 ---
            vol_winner_70 = total_ca * 0.70
            vol_loser_30 = total_ca * 0.30

            rate_nestle_if_win = get_rate_from_grid(df_grid, vol_winner_70, "NESTLE_2026")
            rate_nutricia_if_win = get_rate_from_grid(df_grid, vol_winner_70, "NUTRICIA_2026")

            if rate_nestle_if_win >= rate_nutricia_if_win:
                win, lose = "NESTLE", "NUTRICIA"
                t_win = rate_nestle_if_win
                t_lose = get_rate_from_grid(df_grid, vol_loser_30, "NUTRICIA_2026")
            else:
                win, lose = "NUTRICIA", "NESTLE"
                t_win = rate_nutricia_if_win
                t_lose = get_rate_from_grid(df_grid, vol_loser_30, "NESTLE_2026")
            
            taux_strat_26 = (0.7 * t_win) + (0.3 * t_lose)
            diff = taux_strat_26 - taux_moy_25
            gain_10k = diff * 10000

            # --- AFFICHAGE ---
            st.markdown("---")
            k1, k2, k3 = st.columns(3)
            with k1:
                st.info("🔙 Moyenne 2025 (Réel)")
                st.metric("Taux Actuel", f"{taux_moy_25:.2%}")
                st.caption("Calculé ligne par ligne selon vos achats")
            with k2:
                st.info("🎯 Projection 2026")
                st.write(f"**70% {win}** / 30% {lose}")
                st.metric("Nouveau Taux", f"{taux_strat_26:.2%}")
                st.caption(f"Basé sur un volume gagnant de {vol_winner_70:,.0f}€")
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

            # --- DÉTAILS DYNAMIQUES ---
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🔎 DÉTAILS DES CALCULS (JUSTIFICATION)", expanded=True):
                
                st.markdown("### 1. Détail 2025 (Réel)")
                st.write("Le programme a cherché le taux correspondant au CA de **chaque** laboratoire individuellement.")
                
                data_2025 = {
                    "Labo": ["Nestlé", "Lactalis", "Nutricia", "Fresenius"],
                    "Votre CA": [ca_nestle, ca_lactalis, ca_nutricia, ca_fresenius],
                    "Taux Trouvé": [r_n25, r_l25, r_u25, r_f25],
                    "Marge €": [ca_nestle*r_n25, ca_lactalis*r_l25, ca_nutricia*r_u25, ca_fresenius*r_f25]
                }
                st.dataframe(pd.DataFrame(data_2025).style.format({
                    "Votre CA": "{:,.0f} €",
                    "Taux Trouvé": "{:.2%}",
                    "Marge €": "{:,.2f} €"
                }), use_container_width=True)

                st.markdown("---")
                
                st.markdown("### 2. Simulation 2026 (Projection)")
                st.write(f"Hypothèse : Vous basculez **70%** de votre CA total ({total_ca:,.0f} €) sur le gagnant.")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown(f"""
                    **🏆 Le GAGNANT ({win})**
                    * Volume projeté : **{vol_winner_70:,.0f} €**
                    * Taux correspondant dans la grille : **{t_win:.2%}**
                    """)
                with col_d2:
                    st.markdown(f"""
                    **💀 Le PERDANT ({lose})**
                    * Volume projeté : **{vol_loser_30:,.0f} €**
                    * Taux correspondant dans la grille : **{t_lose:.2%}**
                    """)
                
                # Formule corrigée pour éviter l'erreur LaTeX
                st.latex(rf"\text{{Taux Final}} = (0.7 \times {t_win*100:.2f}\%) + (0.3 \times {t_lose*100:.2f}\%) = \mathbf{{{taux_strat_26*100:.2f}\%}}")

if __name__ == "__main__":
    main()
