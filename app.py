# --- 3. FONCTION DE CHARGEMENT ---
@st.cache_data
def load_data():
    if not os.path.exists(NOM_FICHIER_DATA):
        return None
    
    try:
        # CORRECTION ICI : ajout de encoding='latin-1' pour gérer les accents Excel
        df = pd.read_csv(NOM_FICHIER_DATA, header=1, sep=None, engine='python', encoding='latin-1')

        # Renommage explicite des colonnes
        if len(df.columns) >= 10:
            df.columns = [
                "CLUSTER",             # 0
                "APPROVISIONNEMENT",   # 1
                "CA mini",             # 2
                "CA maxi",             # 3
                "NESTLE_2026",         # 4
                "LACTALIS_2026",       # 5
                "NUTRICIA_2026",       # 6
                "NESTLE_2025",         # 7
                "LACTALIS_2025",       # 8
                "NUTRICIA_2025"        # 9
            ] + list(df.columns[10:])

        # Nettoyage des chiffres
        cols_labos = ["NESTLE_2026", "LACTALIS_2026", "NUTRICIA_2026"]
        for col in cols_labos:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(-1.0)
        
        return df

    except Exception as e:
        # Affiche l'erreur exacte pour le débogage
        st.error(f"Erreur technique lors de la lecture : {e}")
        return None
