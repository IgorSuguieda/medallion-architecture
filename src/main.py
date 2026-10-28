import ingest
import silver
import gold


def main():
    print("Iniciando ingestão (Bronze)...")
    ingest.main()

    print("Iniciando camada Silver...")
    silver.main()

    print("Iniciando camada Gold...")
    gold.main()

    print("Pipeline concluído!")

if __name__ == "__main__":
    main()
