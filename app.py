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

        # Captura o voto (tudo depois de "-votou")
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
    # Corrigir nomes de partidos específicos
    df['Partido'] = df['Partido'].replace({
        'Republican': 'Republicanos',
        'Solidaried': 'Solidariedade'
    })

    return resultado_final, df, None


# --- Layout do Streamlit ---
st.set_page_config(page_title="Analisador de Votações", layout="wide")

st.title("🏛️ Analisador de Votações da Câmara")
st.markdown("Cole o link de uma votação do **Portal da Câmara** para extrair os dados e gerar tabelas.")

url_input = st.text_input("Link da Votação:", placeholder="https://www.camara.leg.br/presenca-comissoes/votacao-portal?...")

if st.button("Processar Votação"):
    if url_input:
        with st.spinner("Extraindo dados..."):
            res_final, df, error = scrape_voting_data(url_input)

        if error:
            st.error(error)
        else:
            st.success(f"**Resultado Oficial:** {res_final}")

            tab1, tab2 = st.tabs(["🗳️ Votos por Deputado", "📊 Resumo por Partido"])

            with tab1:
                st.subheader("Lista de Deputados")
                st.caption("Dica: Clique no canto superior esquerdo da tabela para selecionar tudo, ou arraste o mouse para selecionar células e use Ctrl+C para copiar.")
                
                # data_editor com disabled=True permite copiar células facilmente
                st.data_editor(
                    df, 
                    use_container_width=True, 
                    hide_index=True, 
                    disabled=True
                )

                # Download CSV
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="Baixar Tabela Completa (CSV)",
                    data=csv,
                    file_name='votacao_camara_deputados.csv',
                    mime='text/csv',
                )

            with tab2:
                st.subheader("Votos por Partido")
                if not df.empty:
                    # Tabela Dinâmica (Pivot)
                    pivot_df = pd.crosstab(df['Partido'], df['Voto'])
                    
                    # Forçar colunas específicas na ordem desejada
                    target_cols = ['Sim', 'Não', 'Abstenção', 'Ausente']
                    
                    # Reindex garante que as colunas existam (preenchendo com 0 se faltar)
                    pivot_df = pivot_df.reindex(columns=target_cols, fill_value=0)
                    
                    # Ordenar por quantidade de votos 'Sim' (opcional)
                    pivot_df = pivot_df.sort_values(by='Sim', ascending=False)
                    
                    st.caption("Selecione as células e use Ctrl+C para copiar.")
                    st.data_editor(
                        pivot_df, 
                        use_container_width=True, 
                        disabled=True
                    )
                else:
                    st.warning("Nenhum dado disponível para resumo.")

    else:
        st.warning("Por favor, insira uma URL.")
