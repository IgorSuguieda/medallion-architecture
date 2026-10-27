# %%
from datetime import datetime, timezone
import pathlib
import os
import glob
import json
import pandas as pd
# %%

project_root = pathlib.Path(__file__).resolve().parent.parent

bronze_path = project_root / "data" / "bronze"
silver_path = project_root / "data" / "silver"

if not bronze_path.is_dir():
    raise FileNotFoundError(f"Pasta Bronze não encontrada: {bronze_path}")

coletas = []

for pasta in bronze_path.glob("date_*"):
    if not pasta.is_dir():
        continue

    texto_data = pasta.name.removeprefix("date_")

    try:
        data_coleta = datetime.fromisoformat(texto_data)
    except ValueError:
        continue  # Ignora nomes que não contêm uma data válida.

    # Seus nomes antigos tinham apenas a data; assumimos UTC nesses casos.
    if data_coleta.tzinfo is None:
        data_coleta = data_coleta.replace(tzinfo=timezone.utc)

    coletas.append((data_coleta, pasta))

if not coletas:
    raise FileNotFoundError("Nenhuma pasta de coleta válida na Bronze.")

# eh como se eu passasse uma lista de dicts, e escolhesse qual campo usar 
latest_folder = max(coletas, key=lambda coleta: coleta[0])[1]

print(f"Coleta selecionada: {latest_folder.name}")

# %%

read_metadata = latest_folder / "metadata.json"
pages = sorted(latest_folder.glob("page_*.json"))

if not read_metadata.is_file():
    raise FileNotFoundError(
        f"Metadata não encontrado em {latest_folder.name}."
    )

if not pages:
    raise FileNotFoundError(
        f"Nenhuma página de dados encontrada em {latest_folder.name}."
    )

with open(read_metadata, 'r') as metadata_file:
    #ler o arquivo json
    #verificar se tem alguem em failed
    #se tiver, lança erro e printa
    #se nao, prossegue
    aux = json.load(metadata_file)

    if(len(aux['failed'])):
        raise Exception(f'[FALHA] : Alguma página em {latest_folder.name} falhou')


#%%
list_of_json = []

for page in pages:
    with open(page, 'r') as read_page:
        games = json.load(read_page)    #lista de dicts
        list_of_json.extend(games.values()) #se nao tiver o values, guarda so as keys
        # print(list_of_json)

#%%
#Agora eu tenho uma mega lista de dicts / json
# print(list_of_json)
# %%
df = pd.json_normalize(list_of_json)
df.dtypes

print(f'Antes processamento: {len(df)}')

# %%
# owners é um range, quero dar um jeito de transformar isso

# print(df[df.duplicated(subset='appid')])
df = df.drop_duplicates(subset=['appid'])
df['price'] = df['price'].astype('float') /  100
df['initialprice'] = df['initialprice'].astype('float') / 100
df['discount'] = df['discount'].astype('float') / 100
df['ingest_date'] = df['ingest_date'].astype('datetime64[s, UTC]')

#Dar split em todas as linhas do df e retorna uma series com listas resultantes do split
# df['owners'].str.split(' ')
#sempre retorna uma series a cada operacao
df['lower_bound_owners'] = df['owners'].str.split(' ').str[0].str.replace(',', '').astype('int')
df['upper_bound_owners'] = df['owners'].str.split(' ').str[2].str.replace(',', '').astype('int')

df = df.drop(columns=['score_rank', 'owners'])
print(f'Após processamento e removendo duplicados: {len(df)}')
# %%
if not os.path.exists(silver_path):
    os.mkdir(silver_path)

silver_data = os.path.join(silver_path, 'games.parquet')
df.to_parquet(silver_data, index=False)