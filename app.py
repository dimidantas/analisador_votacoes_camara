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

            tab1, tab2 = st.tabs(["📊 Resumo por Partido (Fácil Cópia)", "🗳️ Votos por Deputado"])

            # --- ABA 1: RESUMO (Prioridade para cópia) ---
            with tab1:
                st.subheader("Resumo por Partido")
                if not df.empty:
                    # Tabela Dinâmica
                    pivot_df = pd.crosstab(df['Partido'], df['Voto'])
                    target_cols = ['Sim', 'Não', 'Abstenção', 'Ausente']
                    pivot_df = pivot_df.reindex(columns=target_cols, fill_value=0)
                    pivot_df = pivot_df.sort_values(by='Sim', ascending=False)
                    
                    st.info("Esta tabela é estática. Basta selecionar com o mouse e copiar (Ctrl+C).")
                    # st.table gera HTML puro, ideal para copiar
                    st.table(pivot_df)
                else:
                    st.warning("Nenhum dado disponível.")

            # --- ABA 2: LISTA DE DEPUTADOS ---
            with tab2:
                st.subheader("Lista de Deputados")
                
                # Opção 1: Visualização interativa (boa para ler)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("---")
                
                # Opção 2: Tabela estática escondida (boa para copiar)
                with st.expander("📋 Ver Tabela Estática para Copiar (Clique aqui)"):
                    st.caption("Esta tabela exibe todos os nomes de uma vez. Selecione e copie.")
                    st.table(df)

                # Download CSV
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="Baixar CSV Completo",
                    data=csv,
                    file_name='votacao_camara_deputados.csv',
                    mime='text/csv',
                )

    else:
        st.warning("Por favor, insira uma URL.")
