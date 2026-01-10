import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Stratégie CNO", layout="wide")

NOM_FICHIER_DATA = "data.csv"
NOM_FICHIER_LOGO = "logo.png"

# --- 2. FONCTION DE CHARGEMENT HYBRIDE (EXCEL + CSV) ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None, "Fichier absent"

    df = None
    debug_info = []

    # --- ESSAI 1 : Lecture comme un fichier EXCEL (Format .xlsx) ---
    # C'est souvent le cas si on a juste renommé le fichier
    try:
        # On force le moteur openpyxl pour lire du Excel même si l'extension est .csv
        df = pd.read_excel(NOM_FICHIER_DATA, header=1, engine='openpyxl')
        debug_info.append("Succès lecture format Excel (.xlsx)")
    except Exception as e:
        debug_info.append(f"Echec lecture Excel : {e}")

    # --- ESSAI 2 : Lecture comme un fichier CSV (Format texte) ---
    if df is None:
        separateurs = [';', ',']
        for sep in separateurs:
            try:
                df_temp = pd.read_csv(
                    NOM_FICHIER_DATA, 
                    header=1, 
                    sep=sep, 
                    engine='python', 
                    encoding='latin-1'
                )
                if df_temp.shape[1] > 2: # Si on a bien des colonnes
                    df = df_temp
                    debug_info.append(f"Succès lecture CSV (séparateur '{sep}')")
                    break
            except Exception as e:
                debug_info.append(f"Echec lecture CSV (sep '{sep}') : {e}")

    # --- NETTOYAGE SI CHARGEMENT REUSSI ---
    if df is not None:
        try:
            # Standardisation des colonnes (index 0 à 9)
            if len(df.columns) >= 10:
                df.columns = [
                    "CLUSTER", "APPROVISIONNEMENT", "CA mini", "CA maxi", 
                    "NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026",
                    "NESTLE_2025", "LACTALIS_2025", "NUTRICIA_2025"
                ] + list(df.columns[10:])

            # Nettoyage des chiffres
            cols_labos = ["NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026"]
            for col in cols_labos:
                if col in df.columns:
                    # Gestion virgule/point
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    # Conversion
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1.0)
            
            return df, None
        except Exception as e:
            return None, f"Erreur lors du nettoyage des données : {e}"

    return None, "\n".join(debug_info)

# --- 3. INTERFACE ---
def main():
    st.title("Stratégie Catégorielle CNO")
    
    if os.path.exists(NOM_FICHIER_LOGO):
        st.image(NOM_FICHIER_LOGO, width=300)

    st.markdown("---")

    # Chargement
    df, error_log = load_data()

    if df is None:
        st.error("❌ ÉCHEC CRITIQUE DU CHARGEMENT")
        st.warning("Voici les tentatives effectuées par le système :")
        st.text(error_log)
        
        st.markdown("### 🕵️‍♂️ DIAGNOSTIC DU FICHIER BRUT")
        st.write("Voici les 500 premiers caractères de votre fichier. Si vous voyez des caractères bizarres (, \x00, PK...), c'est un fichier Excel mal nommé.")
        try:
            with open(NOM_FICHIER_DATA, 'rb') as f:
                content = f.read(500)
                st.code(content)
        except:
            st.error("Impossible de lire le fichier brut.")
        return

    # --- Si on arrive ici, c'est que ça marche ! ---
    st.success("✅ Données chargées avec succès !")
    
    # Formulaire simplifié pour tester
    col1, col2 = st.columns(2)
    choix_cluster = col1.selectbox("Cluster", sorted(df['CLUSTER'].astype(str).unique()))
    choix_appro = col2.selectbox("Appro", sorted(df['APPROVISIONNEMENT'].astype(str).unique()))
    
    ca_input = st.number_input("CA Prévisionnel", min_value=0.0, step=1000.0)

    if st.button("Lancer l'analyse"):
        mask = (df['CLUSTER'].astype(str) == choix_cluster) & (df['APPROVISIONNEMENT'].astype(str) == choix_appro)
        df_res = df[mask]
        df_res = df_res[(df_res['CA mini'] <= ca_input) & (df_res['CA maxi'] >= ca_input)]
        
        if not df_res.empty:
            row = df_res.iloc[0]
            st.write("### Meilleures offres :")
            res_dict = {
                "NESTLE": row.get("NESTLE_2026", -1),
                "LACTALIS": row.get("LACTALIS_2026", -1),
                "NUTRICIA": row.get("NUTRICIA_2026", -1)
            }
            best = max(res_dict, key=res_dict.get)
            st.metric(f"Meilleur Labo : {best}", f"{res_dict[best]:.2%}")
            st.json(res_dict)
        else:
            st.warning("Aucune offre trouvée.")

if __name__ == "__main__":
    main()
