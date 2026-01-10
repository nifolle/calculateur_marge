import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Stratégie catégorielle CNO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. VARIABLES DE CONFIGURATION ---
NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"
TAILLE_LOGO = 350

# --- 3. FONCTION DE CHARGEMENT HYBRIDE ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None

    df = None
    
    # Tentative 1 : Excel
    try:
        df = pd.read_excel(NOM_FICHIER_DATA, header=1, engine='openpyxl')
    except:
        pass

    # Tentative 2 : CSV
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

            cols_labos = ["NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026"]
            for col in cols_labos:
                if col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1.0)
            return df
        except:
            return None
    return None

# --- 4. INTERFACE UTILISATEUR ---
def main():
    
    # --- A. EN-TÊTE ---
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

    # --- B. CHARGEMENT ---
    df = load_data()
    if df is None:
        st.error("❌ Erreur : Fichier 'data.csv' introuvable ou illisible.")
        return 

    # --- C. FORMULAIRE ---
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
        # Liste des choix N-1
        liste_fournisseurs = ["NESTLE", "LACTALIS", "NUTRICIA", "AUTRE/GROSSISTE"]
        choix_n1 = st.selectbox("Fournisseur N-1", liste_fournisseurs)
    with c4:
        ca_input = st.number_input(
            "Chiffre d'affaires avec fournisseur N-1 (€)", 
            min_value=0.0, step=500.0, format="%.2f"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- D. CALCUL & ANALYSE ---
    if st.button("📊 Analyser la meilleure offre 2026", type="primary", use_container_width=True):
        
        # 1. Filtre Cluster/Appro
        mask = (df['CLUSTER'].astype(str) == choix_cluster) & (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        df_filtre = df[mask]

        if df_filtre.empty:
            st.warning(f"Profil inconnu : {choix_cluster} / {choix_appro}")
        else:
            # 2. Filtre CA
            mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
            resultat = df_filtre[mask_ca]

            if resultat.empty:
                st.warning("Montant CA hors tranches.")
            else:
                row = resultat.iloc[0]
                
                # Mapping des colonnes 2026
                labos_map = {
                    "NESTLE": "NESTLE_2026",
                    "LACTALIS": "LACTALIS_2026",
                    "NUTRICIA": "NUTRICIA_2026"
                }

                # Récupération des taux
                scores = {}
                for nom, col in labos_map.items():
                    scores[nom] = row.get(col, -1.0)

                # --- 1. LE GAGNANT ---
                gagnant = max(scores, key=scores.get)
                taux_gagnant = scores[gagnant]

                # --- 2. LE N-1 (Comparatif) ---
                # Si le N-1 est dans la liste des labos, on prend son taux 2026
                # Si c'est "AUTRE", on considère le taux comme 0.0 (pas de contrat direct)
                if choix_n1 in labos_map:
                    taux_n1 = row.get(labos_map[choix_n1], 0.0)
                    # Si le labo N-1 est marqué "NON ELIGIBLE" (-1), on compte 0 pour le calcul du gain
                    if taux_n1 < 0: taux_n1 = 0.0
                else:
                    taux_n1 = 0.0

                # --- 3. CALCUL DU GAIN EN EUROS ---
                # Différence de taux * CA
                delta_taux = taux_gagnant - taux_n1
                gain_euros = delta_taux * ca_input

                # --- E. AFFICHAGE ---
                st.markdown("---")
                st.subheader("🎯 Résultat Financier")

                if taux_gagnant <= 0:
                    st.error("❌ Aucune offre éligible pour ce profil.")
                else:
                    # Affichage en 3 colonnes pour bien séparer les infos
                    kpi1, kpi2, kpi3 = st.columns(3)

                    with kpi1:
                        st.info("🏆 Meilleure Stratégie")
                        st.metric(label="Laboratoire", value=gagnant)
                    
                    with kpi2:
                        st.info("📈 Performance")
                        st.metric(label="Marge 2026", value=f"{taux_gagnant:.2%}")

                    with kpi3:
                        # Logique de couleur pour le gain
                        if gain_euros > 0:
                            st.success(f"💰 Gain vs {choix_n1}")
                            st.metric(label="Gain estimé", value=f"+ {gain_euros:,.2f} €")
                        elif gain_euros == 0:
                            st.warning(f"⚖️ Status Quo vs {choix_n1}")
                            st.metric(label="Différence", value="0 €")
                        else:
                            st.error(f"📉 Perte vs {choix_n1}")
                            st.metric(label="Différence", value=f"{gain_euros:,.2f} €")

                    # Tableau détaillé
                    st.write("### 📋 Comparatif détaillé")
                    data_disp = []
                    for nom, col in labos_map.items():
                        val = row.get(col, -1.0)
                        
                        # Calcul du gain spécifique pour chaque labo par rapport au N-1
                        if val > 0:
                            diff_vs_n1 = (val - taux_n1) * ca_input
                            txt_gain = f"{diff_vs_n1:+,.2f} €"
                            statut = "✅ Eligible"
                            if nom == gagnant: statut = "🏆 TOP CHOIX"
                        else:
                            txt_gain = "N/A"
                            statut = "❌ Non éligible"

                        data_disp.append({
                            "Laboratoire": nom,
                            "Marge 2026": f"{val:.2%}" if val > 0 else "NON ELIGIBLE",
                            "Gain vs N-1 (€)": txt_gain,
                            "Statut": statut
                        })
                    
                    df_disp = pd.DataFrame(data_disp)
                    
                    # Style
                    def style_rows(s):
                        if s['Laboratoire'] == gagnant:
                            return ['background-color: #d4edda; color: #155724; font-weight: bold'] * len(s)
                        return [''] * len(s)

                    st.dataframe(
                        df_disp.style.apply(style_rows, axis=1), 
                        use_container_width=True, 
                        hide_index=True
                    )

if __name__ == "__main__":
    main()
