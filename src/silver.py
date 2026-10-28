# %%
from datetime import datetime, timezone
import pathlib
import os
import json
import pandas as pd
import re
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

#%%
df.columns
# %%
# owners é um range, quero dar um jeito de transformar isso

# print(df[df.duplicated(subset='appid')])
df = df.drop_duplicates(subset=['appid'])
df = df.rename(columns={'appid': 'app_id'})
df['price'] = df['price'].astype('float') /  100
df['initial_price'] = df['initialprice'].astype('float') / 100
df['discount'] = df['discount'].astype('float') / 100
df['ingest_date'] = df['ingest_date'].astype('datetime64[s, UTC]')

#Dar split em todas as linhas do df e retorna uma series com listas resultantes do split
# df['owners'].str.split(' ')
#sempre retorna uma series a cada operacao
df['lower_bound_owners'] = df['owners'].str.split(' ').str[0].str.replace(',', '').astype('int')
df['upper_bound_owners'] = df['owners'].str.split(' ').str[2].str.replace(',', '').astype('int')

df = df.drop(columns=['score_rank', 'owners', 'initialprice'])
print(f'Após processamento e removendo duplicados: {len(df)}')
# %%

# # Essa era uma tentativa de aplicar diretamente regex
# print(df['developer'].str.split(', ').str[1].value_counts().to_string())
# print((df['developer'].str.split('.,[ Inc.|Ltd. |LLC | LTD.]?', regex=True)).str.len())

def string_to_list(lst, reg:re):

    #possivelmente ainda existe o problema de indexacao da lista, que continua como se n tivesse removido
    for i, word in enumerate(lst):
        if(re.search(pattern=reg, string=word, flags=re.IGNORECASE)):
            lst[i-1] = f'{lst[i-1]} {word}'
            lst.pop(i)

    return lst

dev_pattern = r'inc\.?|ltd\.?|llc\.?|ltd\.?'
df["developer"] = (
    df["developer"]
    .str.split(", ")
    .apply(lambda lista: string_to_list(lista, reg=dev_pattern))
)

# %%
df["publisher"] = (
    df["publisher"]
    .str.split(", ")
    .apply(lambda lista: string_to_list(lista, reg=dev_pattern))
)

# for texto in ["Inc.", "inc.", "LTD.", "Indie Studio", "Outro Estúdio"]:
#     resultado = re.match(dev_pattern, texto, flags=re.IGNORECASE)
#     print(repr(texto), bool(resultado))

# %% 
#Crio uma tabela para games
games = df[['app_id', 'name', 'initial_price', 'price', 'discount', 'ccu']].copy()

#Explode expande as linhas: para cada tupla app_id eu terei tuplas = len(app_id) * len(publisher)
#publisher sera uma coluna com uma lista 
publisher_association = (
    df[['app_id', 'publisher']]
    .explode('publisher')
    .rename(columns={'publisher': 'publisher_name'})
)

developer_association = (
    df[['app_id', 'developer']]
    .explode('developer')
    .rename(columns={'developer': 'developer_name'})
)

developer_association
# %%

#Crio um df que sera a tabela publisher 
publisher = (
    publisher_association[['publisher_name']]
    .drop_duplicates()
    .reset_index(drop=True)
)

publisher['publisher_id'] = range(1, len(publisher) + 1)

developer = (
    developer_association[['developer_name']]
    .drop_duplicates()
    .reset_index(drop=True)
)

developer['developer_id'] = range(1, len(developer) + 1)

developer

# %%
game_developers = (
    developer_association
    .merge(
        developer,
        on='developer_name',
        how='inner',
    )
    [['app_id', 'developer_id']]
)
game_developers

#%%

game_publisher = (
    publisher_association
    .merge(
        publisher,
        on='publisher_name',
        how='inner',
    )
    [['app_id', 'publisher_id']]
)

publisher

# %%
developer_association.tail()

#%%
if not os.path.exists(silver_path):
    os.mkdir(silver_path)

# silver_data = os.path.join(silver_path, 'games.parquet')
games.to_parquet(f'{silver_path}/games.parquet', index=False)
publisher.to_parquet(f'{silver_path}/publisher.parquet', index=False)
game_publisher.to_parquet(f'{silver_path}/game_publisher.parquet', index=False)
developer.to_parquet(f'{silver_path}/developer.parquet', index=False)
game_developers.to_parquet(f'{silver_path}/game_developers.parquet', index=False)

#%%
print("Silver feita")

#%%
print(f'{silver_path}/games')