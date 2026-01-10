import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION DU FICHIER ---
# Si vous changez le nom du fichier sur GitHub, changez-le ici aussi
NOM_FICHIER = 'COMPARATIF_CNO_2025_V4.xlsx'

# Configuration de la page
st.set_page_config(page_title="Comparateur CNO", page_icon="💊")

# --- FONCTION DE CHARGEMENT ---
@st.cache_data # Cette commande garde le fichier en mémoire pour que ce soit ultra rapide
def charger_donnees():
    if not os.path.exists(NOM_FICHIER):
        return None
    try:
        df = pd.read_excel(NOM_FICHIER)
        # Nettoyage des noms de colonnes (supprime les espaces invisibles)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return None

# --- DÉBUT DE L'APPLICATION ---
st.title("💊 Comparateur de Marges CNO")
st.write("Entrez vos critères pour obtenir la meilleure offre fournisseur.")
st.markdown("---")

# Chargement automatique
df = charger_donnees()

if df is None:
    st.error(f"⚠️ Le fichier '{NOM_FICHIER}' est introuvable sur le serveur.")
    st.info("Assurez-vous d'avoir uploadé le fichier Excel sur GitHub avec le bon nom.")
else:
    # --- FORMULAIRE ---
    col1, col2 = st.columns(2)
    
    with col1:
        # Liste déroulante Cluster
        liste_clusters = sorted(df['CLUSTER'].unique().astype(str))
        choix_cluster = st.selectbox("Votre Cluster", liste_clusters)
        
    with col2:
        # Liste déroulante Appro
        liste_appro = sorted(df['APPROVISIONNEMENT'].unique().astype(str))
        choix_appro = st.selectbox("Mode d'approvisionnement", liste_appro)
        
    # Saisie CA
    ca_input = st.number_input("Votre Chiffre d'Affaires (€)", min_value=0.0, step=500.0)

    # Bouton de validation
    if st.button("Voir le meilleur fournisseur", type="primary"):
        
        # --- FILTRAGE ---
        # 1. On filtre par Cluster et Appro
        mask_profil = (df['CLUSTER'] == choix_cluster) & (df['APPROVISIONNEMENT'] == choix_appro)
        df_filtre = df[mask_profil]
        
        # 2. On cherche la tranche de CA
        mask_ca = (df_filtre['CA mini'] <= ca_input) & (df_filtre['CA maxi'] >= ca_input)
        resultat = df_filtre[mask_ca]

        st.markdown("---")

        if resultat.empty:
            st.warning("❌ Aucune offre trouvée pour ce montant de CA et ces critères.")
            st.write("Vérifiez les tranches de CA dans le document original.")
        else:
            # On prend la première ligne trouvée
            row = resultat.iloc[0]
            
            # --- COMPARAISON ---
            fournisseurs = ['NESTLE', 'LACTALIS', 'NUTRICIA']
            scores = {}
            
            for f in fournisseurs:
                val = row[f]
                # Si c'est un chiffre, on le prend, sinon (ex: "NON ELIGIBLE") on met -1
                if isinstance(val, (int, float)):
                    scores[f] = val
                else:
                    scores[f] = -1.0
            
            # Qui est le meilleur ?
            gagnant = max(scores, key=scores.get)
            marge_max = scores[gagnant]

            # Affichage du résultat
            if marge_max == -1.0:
                st.error("Aucune éligibilité pour ces 3 fournisseurs (Mention 'NON ELIGIBLE').")
            else:
                st.subheader(f"🏆 Meilleur choix : {gagnant}")
                st.metric("Marge estimée", f"{marge_max:.2%}")
                
                # Petit tableau récapitulatif propre
                st.caption("Détail des offres pour votre profil :")
                
                # Construction d'un tableau simple pour l'affichage
                data_display = []
                for f in fournisseurs:
                    raw_val = row[f]
                    # Formatage joli (pourcentage ou texte)
                    if isinstance(raw_val, (int, float)):
                        txt_val = f"{raw_val:.2%}"
                    else:
                        txt_val = str(raw_val)
                    
                    data_display.append({
                        "Fournisseur": f,
                        "Marge": txt_val,
                        "Note": "✅ Recommandé" if f == gagnant else ""
                    })
                
                st.dataframe(pd.DataFrame(data_display), hide_index=True)
