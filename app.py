import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
import re

# ==========================================
# CONFIGURAÇÃO INICIAL
# ==========================================
st.set_page_config(
    page_title="Steam Scanner - Mapeamento por URL",
    page_icon="🕹️",
    layout="wide"
)

# Inicialização do Session State
if 'df_urls' not in st.session_state:
    st.session_state.df_urls = None
if 'df_scraped' not in st.session_state:
    st.session_state.df_scraped = None

# ==========================================
# FUNÇÕES AUXILIARES E SCRAPING
# ==========================================
@st.cache_data(show_spinner=False)
def convert_df_to_csv(df):
    """Converte DataFrame para CSV utf-8 para download."""
    return df.to_csv(index=False).encode('utf-8')

def extract_appid_from_url(url):
    """Extrai o AppID de uma URL da Steam."""
    match = re.search(r'app/(\d+)', url)
    if match:
        return match.group(1)
    return None

def scrape_steam_app(appid):
    """
    Scraping da página do jogo individual.
    Usa Cookies obrigatórios para contornar o Age Gate de jogos maduros.
    """
    url = f"https://store.steampowered.com/app/{appid}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    cookies = {
        'birthtime': '283993201', 
        'lastagecheckage': '1-January-1979',
        'wants_mature_content': '1'
    }
    
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        if resp.status_code != 200:
            return "Desconhecido", "N/A", 0, 0, "Desconhecido", "Não encontrado", "Não encontrado"
            
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Título
        title_elem = soup.find('div', class_='apphub_AppName')
        title = title_elem.get_text(strip=True) if title_elem else f"AppID {appid}"
        
        # Preço
        price_elem = soup.find('div', class_='game_purchase_price')
        if not price_elem:
            price_elem = soup.find('div', class_='discount_final_price')
        price = price_elem.get_text(strip=True) if price_elem else 'Grátis / Não Informado'
        
        # Tipo
        app_type = "Desconhecido"
        breadcrumbs = soup.find('div', class_='breadcrumbs')
        if breadcrumbs:
            text = breadcrumbs.get_text(strip=True).lower()
            if 'software' in text:
                app_type = 'Software'
            elif 'dlc' in text:
                app_type = 'DLC'
            elif 'game' in text or 'jogos' in text:
                app_type = 'Game'
        else:
            if soup.find('div', class_='game_area_purchase_game'):
                app_type = 'Game'
                
        # Reviews
        pos_reviews, neg_reviews = 0, 0
        reviews_spans = soup.find_all('span', class_='nonresponsive_hidden responsive_reviewdesc')
        for span in reviews_spans:
            texto = span.get_text(strip=True)
            match = re.search(r'(\d+)%\s+of the\s+([\d,]+)\s+user reviews', texto)
            if match:
                pct = int(match.group(1))
                total = int(match.group(2).replace(',', ''))
                pos_reviews = int(total * (pct / 100))
                neg_reviews = total - pos_reviews
                if "for this game" in texto:
                    break

        # Idiomas
        languages = []
        lang_table = soup.find('table', class_='game_language_options')
        if lang_table:
            for tr in lang_table.find_all('tr')[1:]: # pula o cabeçalho
                td = tr.find('td')
                if td:
                    lang_name = td.get_text(strip=True)
                    if lang_name:
                        languages.append(lang_name)
        lang_str = ", ".join(languages) if languages else "Não encontrado"
        
        # Tags
        scraped_tags = []
        tags_elements = soup.find_all('a', class_='app_tag')
        for tag_elem in tags_elements:
            t = tag_elem.get_text(strip=True)
            if t and t != '+':
                scraped_tags.append(t)
        scraped_tags_str = ", ".join(scraped_tags) if scraped_tags else "Não encontrado"
        
        return title, price, pos_reviews, neg_reviews, app_type, lang_str, scraped_tags_str
        
    except Exception as e:
        return "Erro", "Erro", 0, 0, f"Erro: {e}", "Erro", "Erro"

# ==========================================
# ESTRUTURA DA INTERFACE - BARRA LATERAL
# ==========================================
st.sidebar.title("🔍 Mapeamento Sistemático")
st.sidebar.markdown("---")

etapas = [
    "1. Inserção de URLs",
    "2. Deep Scraping",
    "3. Consolidação de Dados"
]
etapa_atual = st.sidebar.radio("Selecione a Etapa:", etapas)
st.sidebar.markdown("---")

# ==========================================
# ROTEAMENTO DAS ETAPAS
# ==========================================

# ETAPA 1
if etapa_atual == etapas[0]:
    st.header("Etapa 1: Inserção Manual de URLs")
    
    st.markdown("Cole abaixo a lista de links da Steam Store (uma URL por linha). O aplicativo extrairá os AppIDs para a próxima etapa.")
    
    urls_input = st.text_area("URLs da Steam:", height=200, placeholder="https://store.steampowered.com/app/730/CSGO\nhttps://store.steampowered.com/app/1086940/Baldurs_Gate_3")
    
    if st.button("Processar URLs", type="primary"):
        if urls_input.strip():
            linhas = urls_input.split('\n')
            dados_urls = []
            
            for linha in linhas:
                linha = linha.strip()
                if linha:
                    appid = extract_appid_from_url(linha)
                    if appid:
                        dados_urls.append({'AppID': appid, 'URL': linha})
            
            if dados_urls:
                df = pd.DataFrame(dados_urls)
                # Removendo duplicatas, caso o usuário tenha colado o mesmo jogo 2 vezes
                df = df.drop_duplicates(subset='AppID')
                st.session_state.df_urls = df
                st.success(f"{len(df)} URLs válidas foram processadas com sucesso!")
            else:
                st.error("Nenhuma URL válida da Steam foi encontrada. Verifique o formato (ex: https://store.steampowered.com/app/ID).")
        else:
            st.warning("Por favor, cole alguma URL antes de processar.")

    if st.session_state.df_urls is not None:
        st.subheader("Lista Reconhecida")
        st.dataframe(st.session_state.df_urls, use_container_width=True)

# ETAPA 2
elif etapa_atual == etapas[1]:
    st.header("Etapa 2: Deep Scraping (Coleta de Dados)")
    
    if st.session_state.df_urls is None:
        st.warning("⚠️ Retorne à Etapa 1 e adicione as URLs primeiro.")
    else:
        st.write(f"Total de itens na fila: **{len(st.session_state.df_urls)}**")
        
        if st.button("Iniciar Scraping", type="primary"):
            df_enriched = st.session_state.df_urls.copy()
            df_enriched['Título'] = ''
            df_enriched['Preço'] = ''
            df_enriched['Type'] = ''
            df_enriched['Total_Reviews_Positivas'] = 0
            df_enriched['Total_Reviews_Negativas'] = 0
            df_enriched['Languages'] = ''
            df_enriched['Scraped_Tags'] = ''
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            total = len(df_enriched)
            
            for i, row in df_enriched.iterrows():
                appid = row['AppID']
                status_text.text(f"Realizando Scraping: AppID {appid} ({i+1}/{total})")
                
                title, price, pos, neg, app_type, langs, scraped_tags = scrape_steam_app(appid)
                
                df_enriched.at[i, 'Título'] = title
                df_enriched.at[i, 'Preço'] = price
                df_enriched.at[i, 'Total_Reviews_Positivas'] = pos
                df_enriched.at[i, 'Total_Reviews_Negativas'] = neg
                df_enriched.at[i, 'Type'] = app_type
                df_enriched.at[i, 'Languages'] = langs
                df_enriched.at[i, 'Scraped_Tags'] = scraped_tags
                
                time.sleep(random.uniform(1.0, 2.5))
                progress_bar.progress((i + 1) / total)
                
            st.session_state.df_scraped = df_enriched
            status_text.text("Scraping Concluído!")
            st.success("Coleta de dados finalizada com sucesso.")
            
    if st.session_state.df_scraped is not None:
        st.subheader("Prévia dos Dados Extraídos")
        st.dataframe(st.session_state.df_scraped[['AppID', 'Título', 'Preço', 'Type']], use_container_width=True)

# ETAPA 3
elif etapa_atual == etapas[2]:
    st.header("Etapa 3: Consolidação e Exportação de Dados")
    
    if st.session_state.df_scraped is None:
        st.warning("⚠️ Complete a Etapa 2 para visualizar e exportar os dados.")
    else:
        df_final = st.session_state.df_scraped
        
        st.markdown("### Base de Dados Completa")
        st.dataframe(df_final, use_container_width=True)
        
        csv_data = convert_df_to_csv(df_final)
        st.download_button(
            label="⬇️ Download steam_scraped_data.csv",
            data=csv_data,
            file_name="steam_scraped_data.csv",
            mime="text/csv",
        )
        
        st.info("A próxima fase analítica (ex: extração qualitativa ou lógica cruzada) pode ser planejada com base neste CSV final.")
