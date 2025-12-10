import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import io

# --- Function to Scrape Data ---
def scrape_voting_data(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, None, f"Error fetching URL: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1. Final Result
    resultado_box = soup.select_one(".resultadoVotacao")
    resultado_final = resultado_box.get_text(strip=True) if resultado_box else "Result not found in page."

    # 2. List of Voters
    items = soup.select("#accordion li")
    
    if not items:
        return None, None, "No voting list found (check if the URL is correct)."

    rows = []
    for li in items:
        text = li.get_text(" ", strip=True)

        # Capture vote (anything after "-votou")
        voto_match = re.search(r"-votou\s+(.+)", text)
        if voto_match:
            voto = voto_match.group(1).strip()
            # Remove the vote part from text to parse name/party easier
            text = text.replace(voto_match.group(0), "").strip()
        else:
            voto = "Ausente"

        # Separate Name and Party/UF -> Example: "Nome do Deputado (PARTIDO-UF)"
        m = re.match(r"^(.*?)\s*\((.*?)-([A-Z]{2})\)$", text)
        if m:
            nome, partido, uf = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        else:
            # Fallback if format is different
            nome, partido, uf = text, "N/A", "N/A"

        rows.append({
            "Nome": nome,
            "Partido": partido,
            "UF": uf,
            "Voto": voto
        })

    df = pd.DataFrame(rows)
    return resultado_final, df, None


# --- Streamlit Layout ---
st.set_page_config(page_title="Chamber Voting Analyzer", layout="wide")

st.title("🏛️ Chamber of Deputies Voting Analyzer")
st.markdown("Paste a URL from the *Portal da Câmara* voting page to extract the data.")

# Input
url_input = st.text_input("Voting URL:", placeholder="https://www.camara.leg.br/presenca-comissoes/votacao-portal?...")

if st.button("Analyze Voting"):
    if url_input:
        with st.spinner("Scraping data..."):
            res_final, df, error = scrape_voting_data(url_input)

        if error:
            st.error(error)
        else:
            # Display Final Result Header
            st.success(f"**Official Result:** {res_final}")

            # --- Tab Layout ---
            tab1, tab2 = st.tabs(["🗳️ Votes by Deputy", "📊 Summary by Party"])

            with tab1:
                st.subheader("Individual Votes")
                st.dataframe(df, use_container_width=True)

                # Download Button for CSV
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="Download Full CSV",
                    data=csv,
                    file_name='votacao_camara.csv',
                    mime='text/csv',
                )

            with tab2:
                st.subheader("Votes by Party")
                if not df.empty:
                    # Create Pivot Table: Rows=Partido, Cols=Voto, Values=Count
                    pivot_df = pd.crosstab(df['Partido'], df['Voto'])
                    
                    # Add a Total column for sorting
                    pivot_df['Total'] = pivot_df.sum(axis=1)
                    pivot_df = pivot_df.sort_values(by='Total', ascending=False)
                    
                    st.dataframe(pivot_df, use_container_width=True)
                else:
                    st.warning("No data available to generate summary.")

    else:
        st.warning("Please enter a URL.")
