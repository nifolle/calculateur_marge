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
    # Note: On suppose que df_grid est déjà filtré par Cluster/Appro
    
    # 1. Cas normal : dans une tranche
    row = df_grid[(df_grid['CA mini'] <= turnover) & (df_grid['CA maxi'] >= turnover)]
    
    # 2. Cas hors tranches (ex: CA très élevé)
    if row.empty:
        max_limit = df_grid['CA maxi'].max()
        if turnover > max_limit:
            # On prend la dernière tranche (la plus haute)
            row = df_grid[df_grid['CA maxi'] == max_limit]
        else:
            # CA trop bas (sous le mini) -> 0% ou première tranche ?
            # Généralement 0 si < min, mais ici on va supposer que la tranche 0 existe
            return 0.0

    if not row.empty:
        return row.iloc[0].get(col_name, 0.0)
    return 0.0

# --- 5. INTERFACE ---
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
        st.error("❌ Erreur chargement fichier.")
        if error_msg: st.warning(error_msg)
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

        # 1. On récupère LA GRILLE complète pour ce profil (sans filtrer par CA tout de suite)
        mask = (df['CLUSTER'] == choix_cluster) & (df['APPROVISIONNEMENT'] == choix_appro)
        df_grid = df[mask]

        if df_grid.empty:
            st.error(f"Aucune grille trouvée pour : {choix_cluster} / {choix_appro}")
        else:
            # --- A. CALCUL 2025 (Basé sur le CA RÉEL de chaque labo) ---
            r_n25 = get_rate_from_grid(df_grid, ca_nestle, "NESTLE_2025")
            r_l25 = get_rate_from_grid(df_grid, ca_lactalis, "LACTALIS_2025")
            r_u25 = get_rate_from_grid(df_grid, ca_nutricia, "NUTRICIA_2025")
            r_f25 = get_rate_from_grid(df_grid, ca_fresenius, "FRESENIUS_2025")
            
            marge_2025 = (ca_nestle*r_n25) + (ca_lactalis*r_l25) + (ca_nutricia*r_u25) + (ca_fresenius*r_f25)
            taux_moy_25 = marge_2025 / total_ca

            # --- B. STRATEGIE 2026 (Basé sur des CA PROJETÉS 70/30) ---
            
            # 1. On calcule les volumes projetés
            vol_winner_70 = total_ca * 0.70
            vol_loser_30 = total_ca * 0.30

            # 2. On regarde qui gagnerait SI on lui donnait 70% du volume
            # On va chercher le taux dans la grille correspondant à ce volume "boosté"
            rate_nestle_if_win = get_rate_from_grid(df_grid, vol_winner_70, "NESTLE_2026")
            rate_nutricia_if_win = get_rate_from_grid(df_grid, vol_winner_70, "NUTRICIA_2026")

            # 3. Duel : Qui a le meilleur taux à 70% de part de marché ?
            if rate_nestle_if_win >= rate_nutricia_if_win:
                win, lose = "NESTLE", "NUTRICIA"
                # Le gagnant (Nestle) prend son taux de "Gros Faiseur" (vol 70%)
                t_win = rate_nestle_if_win
                # Le perdant (Nutricia) prend son taux de "Petit Faiseur" (vol 30%)
                t_lose = get_rate_from_grid(df_grid, vol_loser_30, "NUTRICIA_2026")
            else:
                win, lose = "NUTRICIA", "NESTLE"
                # Le gagnant (Nutricia) prend son taux de "Gros Faiseur"
                t_win = rate_nutricia_if_win
                # Le perdant (Nestle) prend son taux de "Petit Faiseur"
                t_lose = get_rate_from_grid(df_grid, vol_loser_30, "NESTLE_2026")
            
            # 4. Taux Mixte 2026
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
                
                # TABLEAU 2025
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
                
                # EXPLICATION 2026
                st.markdown("### 2. Simulation 2026 (Projection)")
                st.write(f"Hypothèse : Vous basculez **70%** de votre CA total ({total_ca:,.0f} €) sur le gagnant.")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown(f"""
                    **🏆 Le GAGNANT ({win})**
                    * Volume projeté : **{vol_winner_70:,.0f} €**
                    * Taux correspondant dans la grille : **{t_win:.2%}**
                    * *Note : Taux bonifié grâce au gros volume.*
                    """)
                with col_d2:
                    st.markdown(f"""
                    **💀 Le PERDANT ({lose})**
                    * Volume projeté : **{vol_loser_30:,.0f} €**
                    * Taux correspondant dans la grille : **{t_lose:.2%}**
                    * *Note : Taux plus faible car petit volume.*
                    """)
                
                st.latex(rf"\text{{Taux Final}} = (0.7 \times {t_win:.2\%}) + (0.3 \times {t_lose:.2\%}) = \mathbf{{{taux_strat_26:.2\%}}}")

if __name__ == "__main__":
    main()
