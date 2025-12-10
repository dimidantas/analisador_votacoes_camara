import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# --- Função de Extração (Scraper) ---
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
        return None, None, f"Erro ao acessar a URL: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1. Resultado Final
    resultado_box = soup.select_one(".resultadoVotacao")
    resultado_final = resultado_box.get_text(strip=True) if resultado_box else "Resultado não encontrado na página."

    # 2. Lista de Votantes
    items = soup.select("#accordion li")
    
    if not items:
        return None, None, "Lista de votação não encontrada (verifique se o link está correto)."

    rows = []
    for li in items:
        text = li.get_text(" ", strip=True)

        # Captura o voto
        voto_match = re.search(r"-votou\s+(.+)", text)
        if voto_match:
            voto = voto_match.group(1).strip()
            text = text.replace(voto_match.group(0), "").strip()
        else:
            voto = "Ausente"

        # Captura Nome e Partido/UF
        m = re.match(r"^(.*?)\s*\((.*?)-([A-Z]{2})\)$", text)
        if m:
            nome, partido, uf = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        else:
            nome, partido, uf = text, "N/A", "N/A"

        rows.append({
            "Nome": nome,
            "Partido": partido,
            "UF": uf,
            "Voto": voto
        })

    df = pd.DataFrame(rows)
    
    # --- Limpeza de Dados ---
    df['Partido'] = df['Partido'].replace({
        'Republican': 'Republicanos',
        'Solidaried': 'Solidariedade'
    })

    return resultado_final, df, None


# --- Layout do Streamlit ---
st.set_page_config(page_title="Analisador de Votações", layout="wide")

st.title("🏛️ Analisador de Votações da Câmara")
st.markdown("Cole o link de uma votação do **Portal da Câmara** para extrair os dados.")

url_input = st.text_input("Link da Votação:", placeholder="https://www.camara.leg.br/presenca-comissoes/votacao-portal?...")

if st.button("Processar Votação"):
    if url_input:
        with st.spinner("Extraindo dados..."):
            res_final, df, error = scrape_voting_data(url_input)

        if error:
            st.error(error)
        else:
            st.success(f"**Resultado Oficial:** {res_final}")

            tab1, tab2 = st.tabs(["📊 Resumo por Partido", "🗳️ Lista de Deputados"])

            # --- ABA 1: RESUMO (MODIFICADO) ---
            with tab1:
                st.subheader("Resumo por Partido")
                if not df.empty:
                    # 1. Calcula a contagem (Crosstab)
                    pivot_df = pd.crosstab(df['Partido'], df['Voto'])
                    
                    # 2. Define a ordem exata das colunas solicitadas
                    target_cols = ['Sim', 'Não', 'Ausente', 'Abstenção']
                    
                    # 3. Garante que as colunas existam (preenche com 0 se faltar alguma)
                    pivot_df = pivot_df.reindex(columns=target_cols, fill_value=0)
                    
                    # 4. Transforma o 'Partido' (que era índice) em uma coluna normal
                    pivot_df = pivot_df.reset_index()
                    
                    # 5. Ordena por 'Sim' (opcional, mas ajuda na visualização)
                    pivot_df = pivot_df.sort_values(by='Sim', ascending=False)
                    
                    st.info("Selecione com o mouse e copie (Ctrl+C).")
                    
                    # Renderiza HTML puro sem o índice numérico (0, 1, 2...)
                    # A coluna 'Partido' aparecerá como a primeira coluna normal
                    st.markdown(pivot_df.to_html(index=False), unsafe_allow_html=True)
                else:
                    st.warning("Nenhum dado disponível.")

            # --- ABA 2: LISTA DE DEPUTADOS ---
            with tab2:
                st.subheader("Votos Individuais")
                
                modo_view = st.radio(
                    "Escolha o formato:",
                    ["Tabela Simples (Ideal para Copiar)", "Tabela Interativa (Filtrar/Ordenar)"],
                    horizontal=True
                )

                if modo_view == "Tabela Simples (Ideal para Copiar)":
                    st.caption("Esta tabela exibe todos os dados sem numeração de linha. Selecione, copie e cole.")
                    st.markdown(df.to_html(index=False), unsafe_allow_html=True)
                else:
                    st.caption("Use esta tabela para clicar nas colunas e ordenar.")
                    st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("---")
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Planilha (.csv)",
                    data=csv,
                    file_name='votacao_camara_deputados.csv',
                    mime='text/csv',
                )

    else:
        st.warning("Por favor, insira uma URL.")
