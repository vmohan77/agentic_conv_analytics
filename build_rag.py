import chromadb
from sentence_transformers import SentenceTransformer

# read the destination file to be chunked

def read_file_to_be_chunked(file_dest) -> str:
    with open(file_dest, "r") as f:
        content = f.read()
    return content

# chunk the file - by structure of the file

def chunk_file(contents: str) -> List:

    chunks = []

    for content in contents.split("TABLE"):
        chunks.append(content)
    
    
    # cnt = 0 
    # for chunk in chunks:
    #     cnt = cnt + 1
    #     print(f"chunk {cnt}:{chunk} \n\n")
    #     if cnt >= 5: break
    
    return chunks

def build_index(chunks, model, collection):
    
    for i, chunk in enumerate(chunks):
        embedding = model.encode(chunk).tolist()
        collection.add(
            ids = [f"chunk_{i}"],
            documents = [chunk],
            embeddings = [embedding]
        )
    print(f"Finished embedding")

def query_schemas(user_question, collection, top_k=3):
    results = collection.query(
        query_texts=[user_question],
        n_results=top_k
    )
    return results

def main():
    
    #Read File to be chunked 
    contents = read_file_to_be_chunked("retail_schema_documentation.txt")
    print(f"Length of the file by characters {len(contents)} \n\n")
    
    #Chunk the file contents
    chunks = chunk_file(contents)
    print(f"# of chunks created {len(chunks)} \n\n")
    
    #Create Chromadb file on disc
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection("retail_schemas")

    #Initialize model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    #Build the embedding index
    build_index(chunks, model, collection)



if __name__ == "__main__":
    main()
