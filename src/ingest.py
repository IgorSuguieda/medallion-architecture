# %% [markdown]
 ## Return format for an app: ##
"""
api : https://steamspy.com/api.php 
  * appid - Steam Application ID. If it's 999999, then data for this application is hidden on developer's request, sorry.
  * name - game's name
  * developer - comma separated list of the developers of the game
  * publisher - comma separated list of the publishers of the game
  * score_rank - score rank of the game based on user reviews
  * owners - owners of this application on Steam as a range.
  * average_forever - average playtime since March 2009. In minutes.
  * average_2weeks - average playtime in the last two weeks. In minutes.
  * median_forever - median playtime since March 2009. In minutes.
  * median_2weeks - median playtime in the last two weeks. In minutes.
  * ccu - peak CCU yesterday.
  * price - current US price in cents.
  * initialprice - original US price in cents.
  * discount - current discount in percents.
  * tags - game's tags with votes in JSON array.
  * languages - list of supported languages.
  * genre - list of genres.

  Returns all games with owners data sorted by owners. Returns 1,000 entries per page.
  * page - page number for the list (starts at 0)

    #Padronizar inicialmente as 10 primeiras páginas
"""

# %%
import requests
from pathlib import Path
import json
from uuid import uuid4
from datetime import datetime, timezone
import time

def main():
    # %%
    base_url = 'https://steamspy.com/api.php'

    # %%

    project_root = Path(__file__).resolve().parent.parent

    start_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bronze = project_root / 'data' / 'bronze'
    collection_date = f"date_{start_date}"
    bronze_dir = bronze / collection_date

    metadata_run_log = 'metadata.json'
    run_log = {
        "start_collection" : start_date,
        "source" : base_url,
        "failed" : [],
        "success" : []
    }


    bronze_dir.mkdir(parents=True, exist_ok=True)


    for i in range(0,10):
        try:
            if i > 0:
                time.sleep(60)

            paginated_data = requests.get(
                url=base_url,
                params={"request" : "all",
                "page": i}
            )

            page = f"page_{i}.json"


            if paginated_data.status_code != 200:
                raise Exception('Not 200')
            
            requested_data = paginated_data.json()

            for item in requested_data.values():
                item['ingest_date'] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            
            with open(bronze_dir / page, 'w', encoding='utf-8') as json_file:
                json.dump(requested_data, json_file, indent=4, ensure_ascii=False)

        except Exception as error:
            print(f"[FALHA] : Página {i} não foi coletada\n Erro: {error}")
            run_log['failed'].append(i)
            

        else:
            run_log["success"].append(i)
            print(f"[SUCESSO] Página {i}")

    # %%
    end_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_log['end_collection'] = end_date

    with open(bronze_dir / metadata_run_log, 'w', encoding='utf-8') as json_file:
        json.dump(run_log, json_file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()