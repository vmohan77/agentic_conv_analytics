import chromadb
from build_rag import *


def main():
    
    client = chromadb.PersistentClient(path="./chroma_db")
    print(f"The current schemas in ChromaDB are: {client.list_collections()} \n\n")
    collection = client.get_collection("retail_schemas")
    
    #Query RAG
    context = query_schemas("what are different product categories?", collection)
    print(f"Query result: {context}")

if __name__ == "__main__":
    main()