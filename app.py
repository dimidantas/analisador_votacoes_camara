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

    # 1. Tenta capturar o título/resultado
    resultado_box = soup.select_one(".resultadoVotacao")
    if resultado_box:
        resultado_final = resultado_box.get_text(strip=True)
    else:
        titulo_pag = soup.select_one("h1")
        resultado_final = titulo_pag.get_text(strip=True) if titulo_pag else ""

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
    df['Partido'] = df['Partido'].str.strip()
    df['Partido'] = df['Partido'].replace({
        'Republican': 'Republicanos',
        'Solidaried': 'Solidariedade'
    })

    return resultado_final, df, None

# --- Função Auxiliar para Criar Placar ---
def gerar_placar(df_filtrado, titulo):
    if df_filtrado.empty:
        return
    
    contagem = df_filtrado['Voto'].value_counts()
    opcoes = ['Sim', 'Não', 'Abstenção', 'Ausente']
    dados = {op: contagem.get(op, 0) for op in opcoes}
    
    df_placar = pd.DataFrame([dados])
    
    st.markdown(f"##### {titulo}")
    st.markdown(df_placar.to_html(index=False), unsafe_allow_html=True)


# --- Layout do Streamlit ---
st.set_page_config(page_title="Analisador de Votações", layout="wide")

st.title("🏛️ Analisador de Votações da Câmara")
st.markdown("Cole o link de uma votação do **Portal da Câmara** para extrair os dados.")

url_input = st.text_input("Link da Votação:", placeholder="https://www.camara.leg.br/presenca-comissoes/votacao-portal?...")

if st.button("Processar Votação"):
    if url_input:
        with st.spinner("Extraindo e calculando dados..."):
            res_txt, df, error = scrape_voting_data(url_input)

        if error:
            st.error(error)
        else:
            if res_txt and "Não encontrado" not in res_txt:
                st.success(f"**Info da Página:** {res_txt}")

            # --- SEÇÃO DE PLACARES ---
            st.divider()
            col_a, col_b = st.columns(2)
            
            with col_a:
                gerar_placar(df, "📊 Placar Geral")
                
                partidos_centrao = ['PP', 'UNIÃO', 'MDB', 'REPUBLICANOS', 'PSD']
                mask_centrao = df['Partido'].str.upper().isin(partidos_centrao)
                gerar_placar(df[mask_centrao], "🏛️ Placar do Centrão (PP, União, MDB, Rep, PSD)")

            with col_b:
                gerar_placar(df[df['Partido'].str.upper() == 'PL'], "🦅 Placar do PL")
                gerar_placar(df[df['Partido'].str.upper() == 'PT'], "⭐ Placar do PT")
            
            st.divider()

            # --- ABAS ---
            tab1, tab2 = st.tabs(["📊 Detalhamento por Partido", "🗳️ Lista de Deputados"])

            # --- ABA 1: RESUMO POR PARTIDO ---
            with tab1:
                st.subheader("Resumo Completo por Partido")
                if not df.empty:
                    # Cria Tabela
                    pivot_df = pd.crosstab(df['Partido'], df['Voto'])
                    target_cols = ['Sim', 'Não', 'Abstenção', 'Ausente']
                    pivot_df = pivot_df.reindex(columns=target_cols, fill_value=0)
                    pivot_df = pivot_df.reset_index()
                    pivot_df = pivot_df.sort_values(by='Sim', ascending=False)
                    
                    st.info("Selecione com o mouse e copie (Ctrl+C).")
                    st.markdown(pivot_df.to_html(index=False), unsafe_allow_html=True)

                    # Botão Download - Resumo Partido
                    st.markdown("---")
                    csv_partido = pivot_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 Baixar CSV (Resumo por Partido)",
                        data=csv_partido,
                        file_name='resumo_votos_por_partido.csv',
                        mime='text/csv',
                    )
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

                # Botão Download - Lista Deputados
                st.markdown("---")
                csv_deputados = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar CSV (Lista de Deputados)",
                    data=csv_deputados,
                    file_name='votacao_camara_deputados.csv',
                    mime='text/csv',
                )

    else:
        st.warning("Por favor, insira uma URL.")
