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
    
    # Lecture
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

    # Nettoyage
    if df is not None:
        try:
            if len(df.columns) >= 10:
                df.columns = [
                    "CLUSTER", "APPROVISIONNEMENT", "CA mini", "CA maxi", 
                    "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026",
                    "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025"
                ] + list(df.columns[10:])

            cols_to_clean = [
                "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026",
                "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025"
            ]
            
            for col in cols_to_clean:
                if col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1.0)
            return df
        except:
            return None
    return None

# --- 4. INTERFACE ---
def main():
    
    # CSS pour centrer le logo
    st.markdown(
        """
        <style>
            [data-testid="stImage"] {
                display: block;
                margin-left: auto;
                margin-right: auto;
            }
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
        st.error("❌ Erreur technique : Fichier de données introuvable.")
        return 

    # --- FORMULAIRE ---
    st.subheader("🔎 Vos critères")
    
    c1, c2 = st.columns(2)
    with c1:
        valeurs_cluster = sorted(df['CLUSTER'].dropna().astype(str).unique())
        choix_cluster = st.selectbox("Votre Cluster", valeurs_cluster)
    with c2:
        valeurs_appro = sorted(df['APPROVISIONNEMENT'].dropna().astype(str).unique())
        choix_appro = st.selectbox("Mode d'approvisionnement", valeurs_appro)

    c3, c4 = st.columns(2)
    with c3:
        liste_fournisseurs = ["NESTLE", "LACTALIS", "NUTRICIA", "AUTRE/GROSSISTE"]
        choix_2025 = st.selectbox("Fournisseur 2025", liste_fournisseurs)
    with c4:
        ca_input = st.number_input(
            "Chiffre d'affaires avec fournisseur 2025 (€)", 
            min_value=0.0, step=500.0, format="%.2f"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- CALCUL ---
    if st.button("📊 Comparer les taux 2025 vs 2026", type="primary", use_container_width=True):
        
        # Filtrage
        mask = (df['CLUSTER'].astype(str) == choix_cluster) & (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        df_filtre = df[mask]

        if df_filtre.empty:
            st.warning("Profil introuvable.")
        else:
            mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning("Montant CA hors tranches.")
            else:
                row = resultat.iloc[0]
                
                # A. Analyse 2026 (Meilleure offre)
                map_2026 = {"NESTLE": "NESTLE_2026", "LACTALIS": "LACTALIS_2026", "NUTRICIA": "NUTRICIA_2026"}
                scores_2026 = {nom: row.get(col, -1.0) for nom, col in map_2026.items()}
                gagnant_2026 = max(scores_2026, key=scores_2026.get)
                taux_gagnant_2026 = scores_2026[gagnant_2026]

                # B. Analyse 2025 (Historique)
                map_2025 = {"NESTLE": "NESTLE_2025", "LACTALIS": "LACTALIS_2025", "NUTRICIA": "NUTRICIA_2025"}
                taux_2025 = 0.0
                if choix_2025 in map_2025:
                    val_2025 = row.get(map_2025[choix_2025], -1.0)
                    if val_2025 > 0: taux_2025 = val_2025
                
                # C. Calcul des Différentiels
                diff_taux = taux_gagnant_2026 - taux_2025
                gain_pour_10k = diff_taux * 10000

                # D. Affichage
                st.markdown("---")
                
                if taux_gagnant_2026 <= 0:
                    st.error("❌ Aucune offre éligible pour 2026.")
                else:
                    # Affichage en 3 colonnes
                    kpi1, kpi2, kpi3 = st.columns(3)

                    with kpi1:
                        st.info("🏆 Meilleure offre 2026")
                        st.metric("Laboratoire", gagnant_2026)
                        st.write(f"Taux : **{taux_gagnant_2026:.2%}**")
                    
                    with kpi2:
                        st.info(f"🔙 Votre historique {choix_2025}")
                        st.metric("Comparatif", "Année 2025")
                        st.write(f"Taux : **{taux_2025:.2%}**")

                    with kpi3:
                        # Gestion des couleurs selon si c'est positif ou négatif
                        if diff_taux > 0:
                            st.success("📈 Gain de Marge")
                            # 1. Différence en %
                            st.metric("Évolution du taux", f"+ {diff_taux:.2%}")
                            # 2. Gain par tranche de 10k
                            st.metric("Gain en euros par tranche de 10k€ de CA Vente", f"+ {gain_pour_10k:,.2f} €")
                        elif diff_taux == 0:
                            st.warning("⚖️ Status Quo")
                            st.metric("Évolution du taux", "0.00%")
                            st.metric("Gain en euros par tranche de 10k€ de CA Vente", "0 €")
                        else:
                            st.error("📉 Perte de Marge")
                            st.metric("Évolution du taux", f"{diff_taux:.2%}")
                            st.metric("Gain en euros par tranche de 10k€ de CA Vente", f"{gain_pour_10k:,.2f} €")

if __name__ == "__main__":
    main()
