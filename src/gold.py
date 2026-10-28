# %%
from pathlib import Path
import duckdb

#%%
project_root = Path(__file__).resolve().parent.parent
silver_path = project_root / "data" / "silver"

#%% 
con = duckdb.connect(":memory:")

# Cada Parquet fica disponível no SQL pelo nome do arquivo.
for arquivo in silver_path.glob("*.parquet"):
    con.read_parquet(str(arquivo)).create_view(arquivo.stem)

# %%

# Jogo com preco inicial mais caro
most_expensive_query = (
    """
    SELECT
        name,
        initial_price,
        RANK () OVER (ORDER BY initial_price DESC) as rank
    FROM games
    """)

con.sql(most_expensive_query).show()
#%% [markdown]
""" Os nulls abaixo são resultado do pipeline (parsing) ruim """
# %%
# Top 10 developers com mais jogos

dev_query = (
    """
    SELECT
        d.developer_name,
        COUNT(gd.app_id) as number_of_dev_games,
        AVG(g.initial_price)::DECIMAL(10,2) as average_initial_price,
        RANK () OVER (ORDER BY number_of_dev_games DESC) as rank
    FROM developer d
    JOIN game_developers gd
    ON d.developer_id = gd.developer_id
    JOIN games g
    ON g.app_id = gd.app_id
    GROUP BY d.developer_name
    """)
con.sql(dev_query).show()

# %%
# Top 10 publisher com mais jogos

pub_query = (
    """
    SELECT
        p.publisher_name,
        COUNT(gp.app_id) as number_of_published_games,
        AVG(g.initial_price)::DECIMAL(10,2) as average_initial_price,
        RANK () OVER (ORDER BY number_of_published_games DESC) as rank
    FROM publisher p
    JOIN game_publisher gp
    ON p.publisher_id = gp.publisher_id

    JOIN games g
    ON g.app_id = gp.app_id

    GROUP BY p.publisher_name
    """)
con.sql(pub_query).show()
#%%

# (agg jogos por faixa de preco)

agg_games_range = (
    """
    WITH limit_games AS (
        SELECT
            g.name,
            g.price,
            CASE
                WHEN g.price IS NULL THEN 'Sem preço'
                WHEN g.price <= 30  THEN '0-30'
                WHEN g.price <= 60  THEN '>30-60'
                WHEN g.price <= 90  THEN '>60-90'
                WHEN g.price <= 120 THEN '>90-120'
                WHEN g.price <= 150 THEN '>120-150'
                ELSE '>150'
            END AS price_range
        FROM games g
    ),
    total_g AS (
        SELECT
            COUNT(g.name) as total
        FROM games g
    )
    SELECT
        price_range,
        COUNT(name) as quantity,
        (quantity / (SELECT total FROM total_g))::DECIMAL(10,5) as percentage_games
    FROM limit_games
    GROUP BY (price_range)
    ORDER BY CASE price_range
        WHEN '0-30'    THEN 1
        WHEN '31-60'   THEN 2
        WHEN '61-90'   THEN 3
        WHEN '91-120'  THEN 4
        WHEN '121-150' THEN 5
        WHEN '>150'   THEN 6
        ELSE 7
    END;
    """
)
con.sql(agg_games_range).show()
# %%

ccu_query = (
    """
    SELECT
        g.name,
        g.ccu,
        RANK () OVER (ORDER BY g.ccu DESC) as rank
    FROM games g
    """
)


con.sql(ccu_query).show()
# %%

# Materializa os resultados das consultas em arquivos Parquet na camada Gold.
gold_path = project_root / "data" / "gold"
gold_path.mkdir(parents=True, exist_ok=True)

gold_queries = {
    "most_expensive_games": most_expensive_query,
    "games_by_developer": dev_query,
    "games_by_publisher": pub_query,
    "games_by_price_range": agg_games_range,
    "games_by_ccu": ccu_query,
}

for table_name, query in gold_queries.items():
    output_path = gold_path / f"{table_name}.parquet"
    con.sql(query).write_parquet(str(output_path))
    print(f"Gold salva: {output_path.name}")
