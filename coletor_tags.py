import requests
from bs4 import BeautifulSoup
import sys

def extrair_tags_steam():
    print("Iniciando a extração de tags da Steam...")
    url = "https://store.steampowered.com/search/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # O Steam armazena as tags no filtro de busca com data-param="tags"
        elementos_tags = soup.find_all(attrs={'data-param': 'tags'})
        
        if not elementos_tags:
            print("Aviso: Nenhuma tag foi encontrada na página. O layout da Steam pode ter mudado.")
            sys.exit(1)
            
        tags = []
        for el in elementos_tags:
            tag_nome = el.get('data-loc')
            if tag_nome:
                tags.append(tag_nome.strip())
                
        # Remove duplicatas e ordena em ordem alfabética
        tags_unicas = sorted(list(set(tags)))
        
        # Salva no arquivo de texto
        arquivo_saida = "steam_tags.txt"
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            for tag in tags_unicas:
                f.write(f"{tag}\n")
                
        print(f"Sucesso! {len(tags_unicas)} tags únicas foram extraídas e salvas em '{arquivo_saida}'.")
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao se conectar à Steam: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    extrair_tags_steam()
